import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


DB_FILE = Path(__file__).resolve().parents[2] / "state.db"


class StateReader:
    def _get_conn(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

    def all_files(self, limit: Optional[int] = None, offset: int = 0, 
                  state: Optional[str] = None, vendor: Optional[str] = None):
        """Get all files with optional filtering and pagination."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM files WHERE 1=1"
            params = []
            
            if state:
                query += " AND state = ?"
                params.append(state)
            
            if vendor:
                query += " AND filename LIKE ?"
                params.append(f"{vendor}_%")
            
            query += " ORDER BY started_at DESC"
            
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cur = conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_file(self, filename: str) -> Optional[Dict]:
        """Get a specific file by filename."""
        conn = self._get_conn()
        try:
            cur = conn.execute("SELECT * FROM files WHERE filename = ?", (filename,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_stats(self) -> Dict:
        """Get aggregate statistics about file processing."""
        conn = self._get_conn()
        try:
            stats = {}
            
            # Count by state
            cur = conn.execute("""
                SELECT state, COUNT(*) as count 
                FROM files 
                GROUP BY state
            """)
            stats['by_state'] = {row['state']: row['count'] for row in cur.fetchall()}
            
            # Total counts
            cur = conn.execute("SELECT COUNT(*) as total FROM files")
            stats['total'] = cur.fetchone()['total']
            
            # Success rate
            cur = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN state = 'DONE' THEN 1 ELSE 0 END) as done,
                    SUM(CASE WHEN state = 'FAILED' THEN 1 ELSE 0 END) as failed
                FROM files
            """)
            row = cur.fetchone()
            stats['success_rate'] = (row['done'] / row['total'] * 100) if row['total'] > 0 else 0
            
            # Average processing time
            cur = conn.execute("""
                SELECT AVG(duration_ms) as avg_duration 
                FROM files 
                WHERE duration_ms IS NOT NULL
            """)
            row = cur.fetchone()
            stats['avg_duration_ms'] = row['avg_duration'] if row['avg_duration'] else 0
            
            # Recent activity (last 24 hours)
            cur = conn.execute("""
                SELECT COUNT(*) as count 
                FROM files 
                WHERE started_at > datetime('now', '-1 day')
            """)
            stats['last_24h'] = cur.fetchone()['count']
            
            return stats
        finally:
            conn.close()

    def search_files(self, query: str, limit: int = 50) -> List[Dict]:
        """Search files by filename."""
        conn = self._get_conn()
        try:
            cur = conn.execute("""
                SELECT * FROM files 
                WHERE filename LIKE ? 
                ORDER BY started_at DESC 
                LIMIT ?
            """, (f"%{query}%", limit))
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()