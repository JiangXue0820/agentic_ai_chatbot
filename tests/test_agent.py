from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

AUTH = {"Authorization": "Bearer changeme"}

def test_invoke_echo():
    r = client.post("/agent/invoke", json={"input":"hello"}, headers=AUTH)
    assert r.status_code == 200
    assert "answer" in r.json()

