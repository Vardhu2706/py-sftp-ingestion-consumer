# Handles one file.
# Pure function-style
# Returns success/failure + reason
# No filesystem scanning.

from pathlib import Path
from app.models import ProcessResult
from app.logger import setup_logger
from app.config import GPG_HOME
from app.downloader import delete_from_sftp
import gnupg
import uuid
from rq import Retry
from app.queue import ai_queue
from app.job import ai_interpret_job
from app.ai.interpreter import AIInterpreter

logger = setup_logger()

BASE_DIR = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = BASE_DIR / "archive"
FAILED_DIR  = BASE_DIR / "failed"

TMP_DIR = BASE_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)

# Use GPG_HOME from config
gpg_home_path = Path(GPG_HOME).resolve() if not Path(GPG_HOME).is_absolute() else Path(GPG_HOME)
gpg = gnupg.GPG(gnupghome=str(gpg_home_path))

ARCHIVE_DIR.mkdir(exist_ok=True)
FAILED_DIR.mkdir(exist_ok=True)

ai_interpreter = AIInterpreter()



class DecryptRetryableError(Exception):
    pass

class FatalProcessingError(Exception):
    pass



# Pipeline Stages


def validate(file: Path):
    if not file.exists():
        raise ValueError("File does not exist")

    if file.stat().st_size == 0:
        raise ValueError("Empty File")

    if not file.name.endswith(".ready"):
        raise ValueError("Invalid extension")


def decrypt(file: Path) -> Path:
    output_file = TMP_DIR / f"{file.stem}.{uuid.uuid4().hex}.decrypted"

    with file.open("rb") as f:
        result = gpg.decrypt_file(f, output=str(output_file))

    # Guard 1: GPG result object
    if result is None:
        raise DecryptRetryableError("GPG returned None result")

    # Guard 2: GPG status
    if not result.ok:
        raise DecryptRetryableError(f"GPG decrypt failed: {result.status}")

    # Guard 3: Output existence
    if not output_file.exists():
        raise DecryptRetryableError("GPG decrypt produced no output file")

    # Guard 4: Output sanity
    if output_file.stat().st_size == 0:
        raise DecryptRetryableError("Decrypted output is empty")

    return output_file


def parse(file: Path):
    """
    Sub parser.
    Later: parse CSV / JSON / etc.
    """
    if file is None:
        raise RuntimeError("Parse called with None file")

    return file.read_bytes()

def persist(data):
    """
    Stub persistance.
    Later: DB writes, idempotent logic.
    """
    return True

def archive(file: Path):
    target = ARCHIVE_DIR / file.name
    file.rename(target)

def fail(file: Path):
    target = FAILED_DIR / file.name
    file.rename(target)


# Orchestrator


def process_file(file: Path, state) -> ProcessResult:
    logger.info(f"PROCESSING | {file.name}")

    try:
        state.mark_processing(file.name, "VALIDATE")
        validate(file)

        state.mark_processing(file.name, "DECRYPT")
        decrypted = decrypt(file)

        try:
            state.mark_processing(file.name, "PARSE")
            
            raw_text = parse(decrypted)
            state.mark_processing(file.name, "AI_INTERPRET")

            payload = {
                "filename": file.name,
                "text": raw_text
            }

            ai_queue.enqueue(
                ai_interpret_job,
                payload,
                retry=Retry(max=3)
            )

        finally:
            # ALWAYS clean decrypted file immediately after use
            if decrypted.exists():
                decrypted.unlink()

        state.mark_processing(file.name, "ARCHIVE")
        archive(file)
        
        # Delete from SFTP after successful processing
        try:
            delete_from_sftp(file.name)
        except Exception as e:
            # Don't fail processing if SFTP delete fails - file is already archived
            logger.warning(f"Failed to delete {file.name} from SFTP (file already archived): {e}")

        logger.info(f"DONE | {file.name}")
        return ProcessResult(success=True)

    except DecryptRetryableError as err:
        logger.warning(f"RETRYABLE DECRYPT FAILURE | {file.name} | {err}")
        return ProcessResult(success=False, error=str(err), stage="DECRYPT")

    except ValueError as err:
        logger.error(f"FATAL VALIDATION FAILURE | {file.name} | {err}")
        fail(file)
        return ProcessResult(success=False, error=str(err), stage="VALIDATE")

    except RuntimeError as err:
        logger.warning(f"RETRYABLE AI FAILURE | {file.name} | {err}")
        return ProcessResult(
            success=False,
            error=str(err),
            stage="AI_INTERPRET"
        )

    except Exception as err:
        logger.error(f"FATAL PROCESSING FAILURE | {file.name} | {err}")
        fail(file)
        return ProcessResult(success=False, error=str(err), stage="UNKNOWN")

def _infer_stage(error: Exception) -> str:
    # Simple hueristic for now
    return "PROCESSING"