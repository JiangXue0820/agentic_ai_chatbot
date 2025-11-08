from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer changeme"}

def test_weather_endpoint():
    r = client.post("/tools/weather/current", headers=AUTH, json={"city":"Singapore"})
    assert r.status_code == 200
    assert "temperature" in r.json()

