import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Tuple
from datetime import datetime

SETUP_SQL = """CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    k TEXT NOT NULL,
    v TEXT NOT NULL,
    ts TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mem_ns_k ON memory(namespace, k);
"""

class Memory:
    def __init__(self, db_path: Optional[str] = "./mininode_memory.sqlite3"):
        self.db_path = db_path
        with self._conn() as c:
            c.executescript(SETUP_SQL)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def set(self, namespace: str, k: str, v: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO memory(namespace, k, v, ts) VALUES (?, ?, ?, ?)",
                (namespace, k, v, datetime.utcnow().isoformat()),
            )

    def get(self, namespace: str, k: str) -> Optional[str]:
        with self._conn() as c:
            cur = c.execute(
                "SELECT v FROM memory WHERE namespace=? AND k=? ORDER BY id DESC LIMIT 1",
                (namespace, k),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def history(self, namespace: str, k: str, limit: int = 20) -> List[Tuple[str, str]]:
        with self._conn() as c:
            cur = c.execute(
                "SELECT ts, v FROM memory WHERE namespace=? AND k=? ORDER BY id DESC LIMIT ?",
                (namespace, k, limit),
            )
            return cur.fetchall()
