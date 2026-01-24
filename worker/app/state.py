# Tracks processed files.
# Ensures idempotency.
# Survives restarts

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock

BASE_DIR = Path(__file__).resolve().parents[2]
DB_FILE = BASE_DIR / "state.db"

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [0, 5, 15]

class StateStore:
    def __init__(self):
        self._lock = Lock()
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                filename TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                stage TEXT,
                attempts INTEGER NOT NULL,
                error TEXT,
                started_at TEXT NOT NULL,
                last_update TEXT NOT NULL,
                finished_at TEXT,
                duration_ms INTEGER,
                next_retry_at TEXT
            )
            """)

    # Queries

    def is_known(self, filename: str) -> bool:
        return self._fetch_one(filename) is not None

    def can_retry(self, filename: str):
        row = self._fetch_one(filename)
        if not row or row["attempts"] >= MAX_ATTEMPTS:
            return False
        return datetime.utcnow() >= datetime.fromisoformat(row["next_retry_at"])

    # Transitions

    def claim(self, filename: str):
        now = self._now()
        with self._lock, self.conn:
            self.conn.execute("""
                INSERT INTO files (
                    filename, state, stage, attempts,
                    started_at, last_update, next_retry_at
                ) VALUES (?, 'CLAIMED', 'CLAIM', 1, ?, ?, ?)
            """, (filename, now, now, now))

    def mark_processing(self, filename: str, stage: str):
        with self._lock, self.conn:
            self.conn.execute("""
                UPDATE files
                SET state='PROCESSING', stage=?, last_update=?
                WHERE filename=?
            """, (stage, self._now(), filename))

    def mark_done(self, filename: str):
        now = self._now()
        with self._lock, self.conn:
            self.conn.execute("""
                UPDATE files
                SET state='DONE', stage='ARCHIVE',
                    finished_at=?, duration_ms=?
                WHERE filename=?
            """, (now, self._duration_ms(filename), filename))

    def mark_retryable_failed(self, filename: str, stage: str, error: str):
        row = self._fetch_one(filename)
        attempts = row["attempts"] + 1
        backoff = BACKOFF_SECONDS[min(attempts - 1, len(BACKOFF_SECONDS) - 1)]
        next_retry = (datetime.utcnow() + timedelta(seconds=backoff)).isoformat()

        with self._lock, self.conn:
            self.conn.execute("""
                UPDATE files
                SET state='RETRYABLE_FAILED',
                    stage=?, error=?, attempts=?,
                    next_retry_at=?, last_update=?
                WHERE filename=?
            """, (
                stage, error, attempts,
                next_retry, self._now(), filename
            ))

    def mark_failed(self, filename: str, stage: str, error: str):
        now = self._now()
        with self._lock, self.conn:
            self.conn.execute("""
                UPDATE files
                SET state='FAILED', stage=?, error=?,
                    finished_at=?, duration_ms=?
                WHERE filename=?
            """, (
                stage, error, now,
                self._duration_ms(filename), filename
            ))

    # Helpers

    def _fetch_one(self, filename):
        cur = self.conn.execute(
            "SELECT * FROM files WHERE filename=?", (filename,)
        )
        return cur.fetchone()


    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    def _duration_ms(self, filename: str) -> int:
        row = self._fetch_one(filename)
        start = datetime.fromisoformat(row["started_at"])
        return int((datetime.utcnow() - start).total_seconds() * 1000)

    def reconcile(self):
        from pathlib import Path

        ingress = BASE_DIR / "ingress"
        archive = BASE_DIR / "archive"
        failed = BASE_DIR / "failed"

        rows = self.conn.execute("""
            SELECT filename, state FROM files
            WHERE state='PROCESSING'
        """).fetchall()

        for row in rows:
            filename = row["filename"]

            if (archive / filename).exists():
                self.mark_done(filename)
            elif (failed / filename).exists():
                self.mark_failed(filename, "RECONCILE", "Found in failed on restart")
            elif not (ingress / filename).exists():
                self.mark_failed(filename, "RECONCILE", "File missing after crash")
