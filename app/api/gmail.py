from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.tools.gmail_oauth import (
    create_authorization_url,
    exchange_code,
    credentials_status,
)

router = APIRouter()


class OAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


class OAuthCallbackResponse(BaseModel):
    message: str
    token_expiry: str | None = None


class OAuthStatusResponse(BaseModel):
    authorized: bool


@router.get("/oauth/start", response_model=OAuthStartResponse)
def oauth_start(
    redirect_uri: str = Query(..., description="OAuth redirect URI configured in Google console"),
    state: str | None = Query(None, description="Optional opaque state for CSRF protection"),
):
    try:
        auth_url, new_state = create_authorization_url(redirect_uri=redirect_uri, state=state)
        return OAuthStartResponse(authorization_url=auth_url, state=new_state)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/oauth/callback", response_model=OAuthCallbackResponse)
def oauth_callback(
    code: str = Query(..., description="Authorization code returned by Google"),
    redirect_uri: str = Query(..., description="Same redirect URI used to start the OAuth flow"),
    state: str | None = Query(None, description="State value returned by Google"),
):
    try:
        creds = exchange_code(redirect_uri=redirect_uri, code=code, state=state)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    expiry = creds.expiry.isoformat() if creds.expiry else None
    return OAuthCallbackResponse(message="Gmail authorization completed.", token_expiry=expiry)


@router.get("/oauth/status", response_model=OAuthStatusResponse)
def oauth_status():
    return OAuthStatusResponse(**credentials_status())
