from fastapi import Header, HTTPException, status, Depends
from app.utils.config import settings

async def require_bearer(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    if token != settings.API_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    return {"user_id": "demo"}
