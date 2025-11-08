"""Gmail adapter  structure in place; replace stub with OAuth flow in real runs."""
from typing import List, Dict

class GmailAdapter:
    def list_recent(self, limit: int = 5) -> List[Dict]:
        # TODO: implement Google OAuth + Gmail API calls
        # For MVP demo without credentials, return mock data.
        out = []
        for i in range(limit):
            out.append({
                "id": f"demo-{i}",
                "from": "alice@example.com",
                "subject": f"Sample subject {i}",
                "date": "2025-11-05T10:00:00Z",
                "snippet": "This is a placeholder email snippet"
            })
        return out
