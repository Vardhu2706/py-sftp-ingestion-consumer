# Downloads .ready files from SFTP
# Polls vendor directories
# Downloads to ingress/ directory
# Avoids duplicate downloads by checking state

import paramiko
from pathlib import Path
from app.config import (
    SFTP_HOST, SFTP_PORT, SFTP_USERNAME,
    SFTP_PRIVATE_KEY_PATH, SFTP_REMOTE_DIR, SFTP_VENDORS
)
from app.state import StateStore
from app.logger import setup_logger

logger = setup_logger()

BASE_DIR = Path(__file__).resolve().parents[2]
INGRESS_DIR = BASE_DIR / "ingress"

INGRESS_DIR.mkdir(exist_ok=True)


def load_private_key(private_key_path: str):
    try:
        return paramiko.Ed25519Key.from_private_key_file(private_key_path)
    except paramiko.SSHException:
        pass

    try:
        return paramiko.RSAKey.from_private_key_file(private_key_path)
    except paramiko.SSHException:
        pass

    raise RuntimeError("Unsupported or invalid private key format")


def download_from_sftp(state: StateStore):
    """
    Downloads .ready files from SFTP server to local ingress/ directory.
    Skips files that are already known (downloaded or processing).
    """
    try:
        pkey = load_private_key(SFTP_PRIVATE_KEY_PATH)
        
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USERNAME, pkey=pkey)
        
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        downloaded_count = 0
        
        logger.info(f"Connecting to SFTP: {SFTP_HOST}:{SFTP_PORT} as {SFTP_USERNAME}")
        logger.info(f"Remote directory: {SFTP_REMOTE_DIR}")
        logger.info(f"Checking vendors: {', '.join([v.strip() for v in SFTP_VENDORS])}")
        
        # Check each vendor's incoming directory
        for vendor in SFTP_VENDORS:
            vendor = vendor.strip()
            vendor_dir = f"{SFTP_REMOTE_DIR}/{vendor}/incoming"
            
            logger.info(f"Checking vendor directory: {vendor_dir}")
            
            try:
                # List all .ready files in the vendor directory
                files = sftp.listdir(vendor_dir)
                logger.info(f"Found {len(files)} files in {vendor_dir}")
                ready_files = [f for f in files if f.endswith(".ready")]
                logger.info(f"Found {len(ready_files)} .ready files in {vendor_dir}")
                
                for remote_filename in ready_files:
                    # Skip if already known (downloaded or processing)
                    if state.is_known(remote_filename):
                        continue
                    
                    # Check if already downloaded locally
                    local_path = INGRESS_DIR / remote_filename
                    if local_path.exists():
                        # File exists locally but not in state - skip download
                        # Watcher will handle claiming it
                        continue
                    
                    # Download the file
                    try:
                        remote_path = f"{vendor_dir}/{remote_filename}"
                        sftp.get(remote_path, str(local_path))
                        
                        logger.info(f"DOWNLOADED | {remote_filename} from {vendor}")
                        downloaded_count += 1
                        
                        # Don't claim here - let the watcher claim it when processing
                        
                    except Exception as e:
                        logger.error(f"Failed to download {remote_filename}: {e}")
                        # Remove partial download if it exists
                        if local_path.exists():
                            local_path.unlink()
                
            except FileNotFoundError:
                # Vendor directory doesn't exist yet, skip
                logger.warning(f"Vendor directory not found: {vendor_dir}")
                continue
            except Exception as e:
                logger.error(f"Error accessing vendor directory {vendor_dir}: {e}", exc_info=True)
                continue
        
        sftp.close()
        transport.close()
        
        if downloaded_count > 0:
            logger.info(f"Downloaded {downloaded_count} file(s) from SFTP")
            
    except Exception as e:
        logger.error(f"SFTP download error: {e}", exc_info=True)
        # Don't raise - allow watcher to continue processing already-downloaded files


def delete_from_sftp(filename: str):
    """
    Deletes a file from SFTP server after successful processing.
    Extracts vendor from filename (format: vendor_{vendor}_...) and deletes from that vendor's incoming directory.
    """
    try:
        # Extract vendor from filename (e.g., "vendor_a_sample_invoice_..." -> "vendor_a")
        parts = filename.split('_')
        if len(parts) < 2 or not parts[0] == 'vendor':
            logger.warning(f"Cannot determine vendor from filename: {filename}, skipping SFTP delete")
            return
        
        vendor = f"{parts[0]}_{parts[1]}"  # e.g., "vendor_a", "vendor_b", "vendor_c"
        vendor_dir = f"{SFTP_REMOTE_DIR}/{vendor}/incoming"
        remote_path = f"{vendor_dir}/{filename}"
        
        pkey = load_private_key(SFTP_PRIVATE_KEY_PATH)
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USERNAME, pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        try:
            sftp.remove(remote_path)
            logger.info(f"DELETED FROM SFTP | {filename} from {vendor_dir}")
        except FileNotFoundError:
            logger.warning(f"File not found on SFTP (may have been deleted already): {remote_path}")
        except Exception as e:
            logger.error(f"Failed to delete {filename} from SFTP: {e}")
        finally:
            sftp.close()
            transport.close()
            
    except Exception as e:
        # Don't raise - deletion failure shouldn't break processing
        logger.error(f"Error deleting {filename} from SFTP: {e}", exc_info=True)


def download_loop(state: StateStore, interval: int):
    """
    Continuously polls SFTP and downloads new files.
    """
    from time import sleep
    
    logger.info("SFTP downloader started")
    logger.info(f"Polling SFTP every {interval} seconds")
    logger.info(f"Vendors to check: {', '.join(SFTP_VENDORS)}")
    
    while True:
        try:
            download_from_sftp(state)
        except Exception as e:
            logger.error(f"Unexpected error in download loop: {e}")
        
        sleep(interval)
