# =====================================================
# app/agent/long_term_memory.py
# LongTermMemory: Cross-Session Memory Storage
# =====================================================

from typing import List, Dict
from app.memory.vector_store import VectorStore


class LongTermMemory:
    """
    Wrapper around VectorStore for storing and querying cross-session user memory.
    Each stored entry embeds user_id and session_id in metadata for filtering.
    """

    def __init__(self):
        self.vstore = VectorStore(collection="longterm_mem")

    def store_conversation(self, user_id: str, session_id: str, messages: List[Dict[str, str]]):
        """
        Store conversation messages for long-term retrieval.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            messages: List of message dictionaries with 'role' and 'content' keys
        """
        docs = []
        for i, m in enumerate(messages):
            text = m.get("content", "")
            if not text:
                continue
            docs.append({
                "id": f"{user_id}_{session_id}_{i}",
                "text": text,
                "metadata": {
                    "user_id": user_id, 
                    "session_id": session_id, 
                    "role": m.get("role", "user")
                }
            })
        if docs:
            self.vstore.ingest(docs)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search for relevant conversations based on semantic similarity.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            
        Returns:
            List of matching documents with metadata
        """
        return self.vstore.query(query, top_k=top_k)

