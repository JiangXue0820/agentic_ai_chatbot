# =====================================================
# app/agent/memory.py
# ShortTermMemory / SessionMemory Management
# =====================================================

from typing import List, Dict, Any
from app.memory.sqlite_store import SQLiteStore


class ShortTermMemory:
    """
    In-memory buffer for recent conversation turns.
    """

    def __init__(self, limit: int = 5):
        self.buffer: List[Dict[str, str]] = []
        self.limit = limit

    def add(self, role: str, content: str):
        self.buffer.append({"role": role, "content": content})
        if len(self.buffer) > self.limit:
            self.buffer.pop(0)

    def get_context(self) -> List[Dict[str, str]]:
        return self.buffer

    def clear(self):
        self.buffer.clear()


class SessionMemory:
    """
    Persistent memory for session context and execution trace.
    """

    def __init__(self, store: SQLiteStore):
        self.store = store

    def write(self, user_id: str, session_id: str, key: str, value: Any, ttl: int | None = None):
        """
        Write session data to persistent storage.
        
        Args:
            user_id: User identifier
            session_id: Session identifier (used as namespace)
            key: Key/type of data being stored
            value: Value to store (will be converted to string)
            ttl: Time-to-live in seconds (None = no expiration)
        """
        self.store.write(user_id, session_id, key, str(value), ttl)

    def read(self, user_id: str, session_id: str, key: str):
        """
        Read session data from persistent storage.
        
        Args:
            user_id: User identifier
            session_id: Session identifier (used as namespace)
            key: Key/type of data to retrieve
            
        Returns:
            List of matching records (most recent first)
        """
        results = self.store.read(user_id, session_id)
        # Filter by key/type
        for record in results:
            if record.get("type") == key:
                return record.get("content")
        return None
