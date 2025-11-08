from typing import Dict, Any

from app.agent.memory import SessionMemory, LongTermMemoryStore


class ConversationMemoryAdapter:
    """Adapter that retrieves conversation history from long-term memory."""

    description = "Retrieve conversation history from stored long-term memory"

    parameters = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "User identifier",
            },
            "session_id": {
                "type": "string",
                "description": "Session identifier",
            },
            "query": {
                "type": "string",
                "description": "Optional text to focus the recall",
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
                "description": "Maximum number of recalled snippets",
            },
        },
        "required": ["user_id", "session_id"],
    }

    def __init__(self, longterm_mem: LongTermMemoryStore):
        self.longterm_mem = longterm_mem

    def run(
        self,
        user_id: str,
        session_id: str,
        query: str = "",
        top_k: int = 5,
    ) -> Dict[str, Any]:
        results = self.longterm_mem.search(query, top_k=top_k)
        return {
            "scope": "longterm",
            "query": query,
            "results": results,
            "user_id": user_id,
            "session_id": session_id,
        }
