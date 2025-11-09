import sqlite3
import time
from typing import Any, List, Dict
from app.utils.config import SESSION_MEM_PATH

class SQLiteStore:
    def __init__(self, path: str | None = None):
        # Default path from config
        self.path = path or SESSION_MEM_PATH
        
        # Ensure directory exists
        from pathlib import Path
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init()

    def _init(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, user_id TEXT, namespace TEXT, type TEXT, content TEXT, ttl INTEGER, created_at INTEGER)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS kb_chunks (id INTEGER PRIMARY KEY, doc_id TEXT, chunk_text TEXT, metadata TEXT)"
            )

    def write(self, user_id: str, namespace: str, mtype: str, content: str, ttl: int | None):
        now = int(time.time())
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO memories(user_id, namespace, type, content, ttl, created_at) VALUES(?,?,?,?,?,?)",
                (user_id, namespace, mtype, content, ttl or 0, now),
            )

    def read(self, user_id: str, namespace: str, limit: int = 10) -> list[dict]:
        now = int(time.time())
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT content, type, ttl, created_at FROM memories WHERE user_id=? AND namespace=? ORDER BY created_at DESC LIMIT ?",
                (user_id, namespace, limit),
            ).fetchall()
        def alive(r):
            ttl = r[2]
            created = r[3]
            return ttl == 0 or (created + ttl) > now
        return [
            {"content": r[0], "type": r[1], "ttl": r[2], "created_at": r[3]}
            for r in rows if alive(r)
        ]

    def delete(self, user_id: str, namespace: str, mtype: str):
        """Delete stored memories matching the given key."""
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "DELETE FROM memories WHERE user_id=? AND namespace=? AND type=?",
                (user_id, namespace, mtype),
            )
            conn.commit()

    def clear_all(self):
        """Remove every record from all tables."""
        with sqlite3.connect(self.path) as conn:
            conn.execute("DELETE FROM memories")
            conn.commit()

    def list_session_contexts(self, user_id: str) -> List[Dict[str, Any]]:
        """Return the latest stored context per session for a user."""
        now = int(time.time())
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                """
                SELECT namespace, content, ttl, created_at
                FROM memories
                WHERE user_id=? AND type='context'
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()

        sessions: Dict[str, Dict[str, Any]] = {}
        for namespace, content, ttl, created_at in rows:
            if namespace in sessions:
                continue
            if ttl and ttl > 0 and (created_at + ttl) <= now:
                continue
            sessions[namespace] = {
                "session_id": namespace,
                "content": content,
                "created_at": created_at,
            }
        return list(sessions.values())
