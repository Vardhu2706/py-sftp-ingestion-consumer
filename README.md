# SFTP Ingestion Consumer

A Python-based consumer service that downloads encrypted files from an SFTP server, decrypts them, and processes them using AI for structured data extraction. Designed for vendor data ingestion pipelines where files are securely encrypted and delivered via SFTP for automated processing.

## Overview

The SFTP Ingestion Consumer is a robust file processing system that:

1. **Downloads files** from SFTP server (e.g., AWS Transfer Family) for multiple vendors
2. **Decrypts files** using PGP/GPG with the consumer's private key
3. **Extracts structured data** using AI (OpenAI) from decrypted documents
4. **Persists results** as JSON files for downstream processing
5. **Manages state** to ensure idempotency and handle retries
6. **Cleans up** by deleting processed files from SFTP after successful processing

## Features

- 📥 **SFTP Download**: Secure file download with SSH key authentication (Ed25519 and RSA support)
- 🔓 **PGP/GPG Decryption**: Decrypts files using consumer's private key
- 🤖 **AI-Powered Extraction**: Uses OpenAI to extract structured data from documents
- 📊 **State Management**: SQLite-based state tracking for idempotency and crash recovery
- 🔄 **Retry Logic**: Automatic retries with exponential backoff (up to 3 attempts)
- 🗑️ **SFTP Cleanup**: Automatically deletes processed files from SFTP after successful processing
- 📝 **Structured Logging**: Comprehensive logging for monitoring and debugging
- ⚙️ **Configurable**: Environment-based configuration for easy deployment
- 🔄 **Asynchronous Processing**: Redis Queue (RQ) for parallel AI job processing
- 📡 **Monitoring API**: Comprehensive Flask REST API with filtering, pagination, search, and statistics
- 🛡️ **Error Handling**: Graceful error handling with poison message detection
- 🔒 **Security**: Secure key management and encrypted file handling

## Architecture

```
┌─────────────────┐
│  SFTP Server    │
│  (AWS S3)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  SFTP Download  │────▶│   Decrypt   │────▶│   Parse    │
│  (Multi-Vendor) │     │  (GPG/PGP)  │     │  (Extract) │
└─────────────────┘     └──────────────┘     └─────────────┘
                                                      │
                                                      ▼
                                            ┌─────────────────┐
                                            │  AI Processing  │
                                            │  (OpenAI/RQ)    │
                                            └────────┬────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │  Persist &      │
                                            │  Archive        │
                                            └─────────────────┘
```

## Components

The consumer consists of three main components:

### 1. Main Worker (`worker/main.py`)
- Polls SFTP server for new `.ready` files
- Downloads files to local `ingress/` directory
- Validates, decrypts, and queues files for AI processing
- Archives successful files and deletes from SFTP
- Manages file state and retries

### 2. AI Worker (`worker/ai_worker.py`)
- Processes AI interpretation jobs from Redis queue
- Extracts structured data using OpenAI
- Persists results as JSON files in `output/` directory
- Handles job retries and failures

### 3. API Server (`api/main.py`) - Optional
- Provides comprehensive REST API for monitoring and management
- **Health Check** (`/health`): System health status (database, Redis)
- **File States** (`/state`): View all files with pagination and filtering (by state, vendor)
- **File Details** (`/state/<filename>`): Get detailed information about a specific file
- **Statistics** (`/stats`): Aggregate statistics (success rate, processing times, counts by state)
- **Search** (`/search`): Search files by filename
- **Queue Status** (`/queue`): Monitor Redis queue job counts (queued, started, finished, failed)

See [API Documentation](api/API_DOCUMENTATION.md) for detailed endpoint documentation.

## Workflow

1. **SFTP Polling**: Main worker polls SFTP every N seconds (configurable) for new `.ready` files
2. **Download**: Files are downloaded from vendor-specific directories (`{vendor}/incoming/`)
3. **Claim**: File is claimed in state database to prevent duplicate processing
4. **Validation**: File is validated (exists, non-empty, correct extension)
5. **Decryption**: File is decrypted using GPG with consumer's private key
6. **Parsing**: Decrypted content is extracted (currently reads raw bytes)
7. **AI Queue**: File content is queued for AI processing via Redis
8. **AI Processing**: AI worker extracts structured data (document type, entities, dates, amounts, confidence)
9. **Persistence**: AI results are saved as JSON files in `output/` directory
10. **Archive**: Original encrypted file is moved to `archive/` directory
11. **SFTP Cleanup**: File is deleted from SFTP server (only after successful processing)

## File Processing States

Files progress through these states tracked in SQLite database:

- **CLAIMED**: File has been claimed for processing
- **PROCESSING**: File is being processed (stages: VALIDATE, DECRYPT, PARSE, AI_INTERPRET, ARCHIVE)
- **DONE**: File successfully processed and archived
- **RETRYABLE_FAILED**: Processing failed but can be retried (up to 3 attempts with backoff)
- **FAILED**: Processing failed permanently (moved to `failed/` directory)

## File Naming Convention

Files follow this naming pattern (from producer):
```
{vendor}_{template_name}_{timestamp}_{uuid}.{ext}.gpg.ready
```

Example:
```
vendor_a_sample_invoice_20260124081522_ffce2720.pdf.gpg.ready
```

- **`.gpg`**: Indicates the file is PGP-encrypted
- **`.ready`**: Indicates the file is ready for consumer processing

## API Usage

The Flask API provides comprehensive monitoring and management capabilities. Start the API server:

```bash
python api/main.py
```

The API runs on `http://localhost:5000` by default.

### Quick Examples

```bash
# Health check
curl http://localhost:5000/health

# Get all files (paginated)
curl "http://localhost:5000/state?limit=20&offset=0"

# Filter by state
curl "http://localhost:5000/state?state=DONE"

# Filter by vendor
curl "http://localhost:5000/state?vendor=vendor_a"

# Get statistics
curl http://localhost:5000/stats

# Search files
curl "http://localhost:5000/search?q=invoice"

# Get specific file details
curl http://localhost:5000/state/vendor_a_sample_invoice_20240101.gpg

# Check queue status
curl http://localhost:5000/queue
```

See [Ingestion Producer](https://github.com/Vardhu2706/py-sftp-ingestion-producer) for how files are encrypted and sent to the SFTP server.
