from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer changeme"}

def test_vdb_query():
    # Ingest test data
    ingest_r = client.post("/tools/vdb/ingest", headers=AUTH, json={"items":[{"id":"d1","text":"federated learning uses secure aggregation","metadata":{}}]})
    assert ingest_r.status_code == 200
    
    # Query
    r = client.post("/tools/vdb/query", headers=AUTH, json={"query":"Explain secure aggregation", "top_k": 3})
    assert r.status_code == 200
    assert "results" in r.json()

