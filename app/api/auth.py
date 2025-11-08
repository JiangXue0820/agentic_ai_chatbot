from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.utils.config import settings

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """
    Basic Authentication endpoint.
    Validates username/password, returns the static API_TOKEN.
    """
    if req.username == settings.ADMIN_USERNAME and req.password == settings.ADMIN_PASSWORD:
        return {"access_token": settings.API_TOKEN, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password"
    )
