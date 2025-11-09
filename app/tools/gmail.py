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
        raw_count = kwargs.get("count", kwargs.get("limit", 5))
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            count = 5
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
    
    def list_recent(self, limit: int = 5, query: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Return summaries for the most recent Gmail messages.

        Accepts both 'limit' (primary) and 'count' (alias) so planner/tool calls remain compatible.
        """
        count_override = kwargs.pop("count", None)
        if count_override is not None:
            try:
                limit = int(count_override)
            except (TypeError, ValueError):
                limit = 5

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 5

        if limit > 50:
            limit = 50
        creds = ensure_credentials()

        try:
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            results: List[Dict[str, Any]] = []
            page_token: Optional[str] = None

            while len(results) < limit:
                list_kwargs = {
                    "userId": "me",
                    "maxResults": limit,
                    "labelIds": ["INBOX"],
                }
                if query:
                    list_kwargs["q"] = query
                if page_token:
                    list_kwargs["pageToken"] = page_token

                response = service.users().messages().list(**list_kwargs).execute()
                messages = response.get("messages", [])
                if not messages:
                    break

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
                    if len(results) >= limit:
                        break

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            if len(results) > limit:
                results = results[:limit]
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
