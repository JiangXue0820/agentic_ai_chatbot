# =====================================================
# app/agent/memory.py
# ShortTermMemory / SessionMemory Management
# =====================================================

from typing import List, Dict, Any
import uuid
from app.memory.sqlite_store import SQLiteStore
from app.memory.vector_store import VectorStore
from app.utils.config import LONGTERM_PATH


class ShortTermMemory:
    """
    Purely in-RAM buffer for recent conversation turns.
    """

    def __init__(self, limit: int = 5):
        self.buffer: List[Dict[str, str]] = []
        self.limit = limit

    def add(self, role: str, content: str):
        self.buffer.append({"role": role, "content": content})
        if len(self.buffer) > self.limit:
            self.buffer.pop(0)

    def get_context(self) -> List[Dict[str, str]]:
        return list(self.buffer)

    def clear(self):
        self.buffer.clear()


class SessionMemory:
    """
    Persistent context via SQLite.
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
        if value is None:
            self.store.delete(user_id, session_id, key)
            return
        self.store.write(user_id, session_id, key, str(value), ttl)

    def read(self, user_id: str, session_id: str, key: str):
        """
        Read session data from persistent storage.
        
        Args:
            user_id: User identifier
            session_id: Session identifier (used as namespace)
            key: Key/type of data to retrieve
            
        Returns:
            Content of the first matching record or None
        """
        results = self.store.read(user_id, session_id)
        if isinstance(results, list):
            for record in results:
                if record.get("type") == key:
                    return record.get("content")
        return None

    def to_longterm_snapshot(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Extract the latest conversation context for long-term storage."""
        context = self.read(user_id, session_id, "context")
        if not context:
            return []
        import json
        try:
            parsed = json.loads(context) if isinstance(context, str) else context
            return parsed.get("conversation_history", [])
        except Exception:
            return []

    def clear(self, user_id: str, session_id: str):
        """Clear all records under this session_id."""
        import sqlite3
        conn = sqlite3.connect(self.store.path)
        conn.execute("DELETE FROM memories WHERE user_id=? AND namespace=?", (user_id, session_id))
        conn.commit()
        conn.close()

# =====================================================
# 🔹 Long-Term Memory Wrapper
# =====================================================

class LongTermMemoryStore:
    """
    High-level wrapper for storing and querying long-term conversational memory.

    Intended for:
        - Cross-session user context
        - Personalized long-term memory
    """

    def __init__(self):
        self.vstore = VectorStore(
            path=LONGTERM_PATH,
            collection="longterm_mem"
        )

    def store_conversation(self, user_id: str, session_id: str, messages: List[Dict], start_index: int = 0):
        """
        Convert and store conversation messages into long-term memory.

        Args:
            user_id: Unique user identifier
            session_id: Session identifier
            messages: List of dicts with "role" and "content"
        """
        docs = []
        for offset, m in enumerate(messages):
            text = m.get("content", "")
            if not text:
                continue
            docs.append({
                "id": f"{user_id}_{session_id}_{start_index + offset}_{uuid.uuid4().hex}",
                "text": text,
                "metadata": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "role": m.get("role", "user"),
                    "turn_index": start_index + offset,
                }
            })
        if docs:
            self.vstore.ingest(docs)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Query the long-term memory for semantically related content.

        Args:
            query: Natural language query
            top_k: Maximum number of results to return

        Returns:
            A list of relevant memory chunks.
        """
        return self.vstore.query(query, top_k)
