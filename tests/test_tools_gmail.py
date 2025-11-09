from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer changeme"}

def test_gmail_summary_requires_auth_or_returns_data():
    r = client.post("/tools/gmail/summary", headers=AUTH, json={"limit": 1})
    if r.status_code == 400:
        detail = r.json().get("detail", "")
        assert "Gmail account" in detail
    else:
        assert r.status_code == 200
        data = r.json()
        assert "emails" in data
        assert data["count"] == len(data["emails"])

