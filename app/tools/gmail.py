"""
Gmail Tool Adapter
Provides email access functionality via Gmail API.
"""
from __future__ import annotations

import datetime as dt
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.tools.gmail_oauth import ensure_credentials
from app.utils.config import settings


class GmailAdapter:
    """Gmail email retrieval tool backed by the Gmail REST API."""
    
    description = "Access Gmail inbox to read and summarize recent emails"
    
    parameters = {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of recent emails to retrieve (default: 5, max: 50)",
                "default": 5,
                "minimum": 1,
                "maximum": 50,
            },
            "limit": {
                "type": "integer",
                "description": "Alias for 'count' parameter",
                "default": 5,
            },
            "filter": {
                "type": "string",
                "description": "Optional Gmail search query (e.g., 'is:unread from:someone@example.com')",
                "required": False,
            },
        },
        "required": [],
    }
    
    def run(self, **kwargs) -> Dict[str, Any]:
        count = kwargs.get("count") or kwargs.get("limit", 5)
        query = kwargs.get("filter")
        emails = self.list_recent(limit=count, query=query)
        summary = f"Retrieved {len(emails)} recent email(s)"
        if query:
            summary += f" matching query '{query}'"
        return {
            "summary": summary,
            "count": len(emails),
            "emails": emails,
            "query": query,
        }
    
    def list_recent(self, limit: int = 5, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return summaries for the most recent Gmail messages."""
        if limit > 50:
            limit = 50
        creds = ensure_credentials()

        try:
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            list_kwargs = {"userId": "me", "maxResults": limit, "labelIds": ["INBOX"]}
            if query:
                list_kwargs["q"] = query
            response = service.users().messages().list(**list_kwargs).execute()
            messages = response.get("messages", [])
            if not messages:
                return []

            results: List[Dict[str, Any]] = []
            for item in messages:
                msg = service.users().messages().get(
                    userId="me",
                    id=item["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()
                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                subject = self._decode_header(headers.get("subject"))
                sender = headers.get("from", "")
                _, email_addr = parseaddr(sender)
                date_header = headers.get("date")
                timestamp = self._parse_date(date_header)

                results.append(
                    {
                        "id": msg.get("id"),
                        "threadId": msg.get("threadId"),
                        "from": sender,
                        "from_address": email_addr,
                        "subject": subject,
                        "date": timestamp,
                        "snippet": msg.get("snippet", ""),
                        "labelIds": msg.get("labelIds", []),
                    }
                )
            return results
        except HttpError as exc:
            raise RuntimeError(f"Gmail API error: {exc}") from exc

    @staticmethod
    def _decode_header(value: Optional[str]) -> str:
        if not value:
            return ""
        decoded_parts = []
        for fragment, encoding in decode_header(value):
            if isinstance(fragment, bytes):
                decoded_parts.append(fragment.decode(encoding or "utf-8", errors="replace"))
            else:
                decoded_parts.append(fragment)
        return " ".join(decoded_parts).strip()

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            dt_obj = parsedate_to_datetime(value)
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=dt.timezone.utc)
            return dt_obj.isoformat()
        except Exception:
            return value
