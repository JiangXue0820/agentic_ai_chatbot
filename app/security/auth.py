from fastapi import Header, HTTPException, status
from app.utils.config import settings

async def require_bearer(authorization: str = Header(None)):
    """
    Simple static bearer token validation.
    Uses the configured API_TOKEN from .env.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token"
        )

    token = authorization.split(" ", 1)[1].strip()

    if not settings.API_TOKEN or settings.API_TOKEN == "changeme":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured: API_TOKEN not set"
        )

    if token != settings.API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token"
        )

    # Always same user for now
    return {"user_id": "admin", "auth_method": "static"}
