from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer changeme"}

def test_gmail_mock():
    r = client.post("/tools/gmail/summary", headers=AUTH, json={"limit": 3})
    assert r.status_code == 200
    data = r.json()
    assert "emails" in data
    assert len(data["emails"]) == 3

