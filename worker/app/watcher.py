# Polls SFTP for new files and downloads them
# Then polls ingress/ for downloaded files
# Detects *.ready
# Ensures only one claim per file.
# Hands off to processor.
# No business logic.

import time
from pathlib import Path
from app.state import StateStore
from app.processor import process_file, fail
from app.downloader import download_from_sftp
from app.config import DOWNLOAD_INTERVAL_SECONDS
from app.logger import setup_logger

logger = setup_logger()

BASE_DIR = Path(__file__).resolve().parents[2]
INGRESS_DIR = BASE_DIR / "ingress"

POLL_INTERVAL = 2 # Seconds

INGRESS_DIR.mkdir(exist_ok=True)

def watch():
    state = StateStore()
    logger.info("Watcher started")

    logger.info("Reconciling in-flight files")
    state.reconcile()

    last_download_time = 0

    while True:
        # Periodically download new files from SFTP
        current_time = time.time()
        if current_time - last_download_time >= DOWNLOAD_INTERVAL_SECONDS:
            try:
                download_from_sftp(state)
            except Exception as e:
                logger.error(f"Error downloading from SFTP: {e}")
            last_download_time = current_time

        # Process downloaded files
        for file in INGRESS_DIR.glob("*.ready"):
            filename = file.name
    
            if state.is_known(filename):
                if state.can_retry(filename):
                    logger.info(f"RETRY | {filename}")
                else:
                    continue
            else:
                logger.info(f"CLAIM | {filename}")
                state.claim(filename)
    
            result = process_file(file, state)
    
            if result.success:
                state.mark_done(filename)
            else:
                # attempts already incremented inside state
                if not state.can_retry(filename):
                    logger.error(f"POISON | {filename}")
                    fail(file)
                    state.mark_failed(filename, result.stage, result.error)
                else:
                    state.mark_retryable_failed(filename, result.stage, result.error)
    
        time.sleep(POLL_INTERVAL)
    