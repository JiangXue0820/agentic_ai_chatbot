from typing import Dict, Any

from app.agent.memory import LongTermMemoryStore


class ConversationMemoryAdapter:
    """
    Adapter that retrieves conversation history from long-term memory.
    
    Use this tool ONLY when the user explicitly asks to recall previous conversations.
    Do NOT use for other intents like email summarization or weather queries.
    
    Parameters (passed directly to 'input', not nested):
    - user_id (str, required): User identifier
    - session_id (str, required): Session identifier
    - query (str, optional): Optional text to focus the recall
    - top_k (int, optional): Maximum number of recalled snippets (default: 5, max: 10)
    
    Example usage in planning:
    {
      "action": "memory",
      "input": {"user_id": "user123", "session_id": "session456", "query": "previous discussion about transformers"}
    }
    """
    
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
        results = self.longterm_mem.search(
            query,
            top_k=top_k,
            user_id=user_id,
            session_id=session_id,
        )
        return {
            "scope": "longterm",
            "query": query,
            "results": results,
            "user_id": user_id,
            "session_id": session_id,
        }
