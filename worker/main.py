from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root BEFORE importing any modules that use config
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

from app.watcher import watch
from app.logger import setup_logger

logger = setup_logger()

if __name__ == "__main__":
    logger.info("Starting consumer-worker")
    watch()