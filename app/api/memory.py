from fastapi import APIRouter, Depends
from app.security.auth import require_bearer
from app.schemas.models import MemoryWrite
from app.memory.sqlite_store import SQLiteStore

router = APIRouter()
store = SQLiteStore()

@router.post("/write")
async def write(m: MemoryWrite, user=Depends(require_bearer)):
    store.write(user_id=user["user_id"], namespace=m.namespace, mtype=m.type, content=m.content, ttl=m.ttl)
    return {"ok": True}

@router.get("/read")
async def read(namespace: str, limit: int = 10, user=Depends(require_bearer)):
    return {"items": store.read(user_id=user["user_id"], namespace=namespace, limit=limit)}
