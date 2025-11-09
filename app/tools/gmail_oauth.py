from __future__ import annotations

import json
import os
from typing import Optional, Tuple, List

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.utils.config import settings

_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _ensure_client_config(redirect_uri: Optional[str] = None) -> dict:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise RuntimeError("GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET not configured")

    config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": _AUTH_URI,
            "token_uri": _TOKEN_URI,
        }
    }

    if redirect_uri:
        config["web"]["redirect_uris"] = [redirect_uri]

    return config


def _scopes(scopes: Optional[List[str]] = None) -> List[str]:
    return scopes or list(settings.GMAIL_SCOPES)


def create_authorization_url(
    redirect_uri: str,
    scopes: Optional[List[str]] = None,
    state: Optional[str] = None,
) -> Tuple[str, str]:
    """Construct an authorization URL for the Gmail OAuth flow."""
    flow = Flow.from_client_config(
        _ensure_client_config(redirect_uri),
        scopes=_scopes(scopes),
        state=state,
        redirect_uri=redirect_uri,
    )
    auth_url, new_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, new_state


def exchange_code(
    redirect_uri: str,
    code: str,
    state: Optional[str] = None,
    scopes: Optional[List[str]] = None,
) -> Credentials:
    """Exchange an authorization code for access/refresh tokens."""
    flow = Flow.from_client_config(
        _ensure_client_config(redirect_uri),
        scopes=_scopes(scopes),
        state=state,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    save_credentials(creds)
    return creds


def save_credentials(creds: Credentials) -> None:
    os.makedirs(os.path.dirname(settings.GMAIL_TOKEN_PATH), exist_ok=True)
    with open(settings.GMAIL_TOKEN_PATH, "w", encoding="utf-8") as fp:
        fp.write(creds.to_json())


def load_credentials(scopes: Optional[List[str]] = None) -> Optional[Credentials]:
    if not os.path.exists(settings.GMAIL_TOKEN_PATH):
        return None
    return Credentials.from_authorized_user_file(
        settings.GMAIL_TOKEN_PATH,
        scopes=_scopes(scopes),
    )


def ensure_credentials(scopes: Optional[List[str]] = None) -> Credentials:
    creds = load_credentials(scopes)
    if not creds:
        raise RuntimeError("Gmail account not authorized. Complete OAuth flow first.")

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_credentials(creds)
        else:
            raise RuntimeError("Stored Gmail credentials are invalid. Re-authorize the account.")
    return creds


def credentials_status() -> dict:
    creds = load_credentials()
    if not creds:
        return {"authorized": False}
    valid = creds.valid
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(creds)
            valid = True
        except Exception:
            valid = False
    return {"authorized": valid}
