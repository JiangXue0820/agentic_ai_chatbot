import json
from fastapi import APIRouter, Depends

from app.security.auth import require_bearer
from app.tools.vdb import KnowledgeBaseStore
from app.agent.memory import LongTermMemoryStore
from app.memory.sqlite_store import SQLiteStore
from app.api.agent import agent as running_agent

router = APIRouter()


@router.post("/reset")
async def reset_all_data(user=Depends(require_bearer)):
    kb_store = KnowledgeBaseStore()
    kb_store.clear_all()

    longterm_store = LongTermMemoryStore()
    longterm_store.clear_all()

    SQLiteStore().clear_all()

    # Clear in-memory caches held by the running agent instance
    running_agent.short_mem.clear()
    running_agent.mem.clear_all()
    running_agent.longterm_mem.clear_all()
    vdb_adapter = running_agent.tools.tools.get("vdb")
    if vdb_adapter and hasattr(vdb_adapter, "store"):
        vdb_adapter.store.clear_all()
    running_agent.session_mem = running_agent.session_mem.__class__(running_agent.mem)

    return {"status": "ok", "detail": "All knowledge, long-term, and session data cleared."}


@router.get("/bootstrap")
async def bootstrap_state(user=Depends(require_bearer)):
    store = SQLiteStore()
    sessions_raw = store.list_session_contexts(user["user_id"])
    sessions = []

    for idx, entry in enumerate(sessions_raw, start=1):
        content = entry.get("content")
        payload = {}
        if isinstance(content, str):
            try:
                payload = json.loads(content)
            except Exception:
                payload = {}
        elif isinstance(content, dict):
            payload = content

        messages = payload.get("conversation_history") or []
        sanitized_messages = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            text = message.get("content")
            if not role or text is None:
                continue
            sanitized = {"role": role, "content": text}
            if "masked_input" in message:
                sanitized["masked_input"] = message["masked_input"]
            sanitized_messages.append(sanitized)

        title = payload.get("title")
        if not title and sanitized_messages:
            first_user = next((m["content"] for m in sanitized_messages if m["role"] == "user"), "")
            snippet = (first_user or "").strip()
            if snippet:
                title = snippet[:20] + ("…" if len(snippet) > 20 else "")

        if not title:
            title = f"Chat {idx}"

        sessions.append(
            {
                "id": entry.get("session_id"),
                "title": title,
                "updated_at": entry.get("created_at"),
                "messages": sanitized_messages,
            }
        )

    documents = KnowledgeBaseStore().list_documents()

    return {"sessions": sessions, "documents": documents}
