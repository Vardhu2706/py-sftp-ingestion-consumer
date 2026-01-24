import json
from pathlib import Path
from app.logger import setup_logger

logger = setup_logger()

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def persist(data: dict, filename: str):
    """
    Persist AI output as JSON
    One file per output
    """

    out_file = OUTPUT_DIR / f"{filename}.json"

    with out_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info(f"PERSISTED | {out_file.name}")