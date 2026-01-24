import sqlite3
from pathlib import Path


DB_FILE = Path(__file__).resolve().parents[2] / "state.db"


class StateReader:
    def all_files(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row

        try:
            cur = conn.execute("SELECT * FROM files")
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()