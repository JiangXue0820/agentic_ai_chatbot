"""
Gmail Tool Adapter
Provides email access functionality via Gmail API.

Note: Currently returns mock data for MVP demonstration.
      In production, implement Google OAuth + Gmail API calls.
"""
from typing import List, Dict, Any


class GmailAdapter:
    """
    Gmail email retrieval tool.
    
    Provides access to user's Gmail inbox for reading and summarizing emails.
    
    Attributes:
        description: Human-readable description of the tool
        parameters: JSON schema defining the tool's parameters
    
    TODO: Implement Google OAuth flow and real Gmail API integration
    """
    
    # Tool metadata for ToolRegistry
    description = "Access Gmail inbox to read and summarize recent emails"
    
    parameters = {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of recent emails to retrieve (default: 5, max: 50)",
                "default": 5,
                "minimum": 1,
                "maximum": 50
            },
            "limit": {
                "type": "integer",
                "description": "Alias for 'count' parameter",
                "default": 5
            },
            "filter": {
                "type": "string",
                "description": "Optional filter (e.g., 'unread', 'from:sender@example.com')",
                "required": False
            }
        },
        "required": []
    }
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Unified entry point for the tool (required by ToolRegistry).
        
        Args:
            **kwargs: Flexible keyword arguments that can include:
                - count (int): Number of emails to retrieve
                - limit (int): Alternative name for count
                - filter (str): Optional filter criteria
        
        Returns:
            Dict containing:
                - summary (str): Brief summary of emails
                - count (int): Number of emails retrieved
                - emails (List[Dict]): List of email objects
        
        Example:
            >>> adapter.run(count=5)
            {
                "summary": "You have 5 recent emails",
                "count": 5,
                "emails": [...]
            }
        """
        # Support both 'count' and 'limit' parameter names
        count = kwargs.get("count") or kwargs.get("limit", 5)
        email_filter = kwargs.get("filter")
        
        emails = self.list_recent(limit=count)
        
        return {
            "summary": f"Retrieved {len(emails)} recent email(s)",
            "count": len(emails),
            "emails": emails,
            "filter": email_filter
        }
    
    def list_recent(self, limit: int = 5) -> List[Dict]:
        """
        List recent emails from Gmail inbox.
        
        Args:
            limit: Maximum number of emails to retrieve (default: 5)
        
        Returns:
            List of email dictionaries containing:
                - id: Email message ID
                - from: Sender email address
                - subject: Email subject line
                - date: Timestamp in ISO format
                - snippet: Brief preview of email content
        
        Note:
            This is a mock implementation for MVP demonstration.
            In production, replace with Google OAuth + Gmail API calls.
        
        TODO:
            1. Implement Google OAuth 2.0 authentication
            2. Use Gmail API to fetch real email data
            3. Handle pagination for large inboxes
            4. Implement error handling for API failures
            5. Add support for labels, filters, and search
        """
        # Mock data for MVP demo without credentials
        out = []
        for i in range(limit):
            out.append({
                "id": f"demo-{i}",
                "from": "alice@example.com" if i % 2 == 0 else "bob@example.com",
                "subject": f"Sample Email Subject {i + 1}",
                "date": "2025-11-05T10:00:00Z",
                "snippet": f"This is a placeholder email snippet {i + 1}. In production, this would contain actual email content preview."
            })
        return out
