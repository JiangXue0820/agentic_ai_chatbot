import json, sys
from app.tools.vdb import VDBAdapter

if __name__ == "__main__":
    v = VDBAdapter()
    items = [
        {"id":"ppfl_1","text":"Privacy-preserving federated learning uses secure aggregation to protect client updates.","metadata":{"source":"demo"}},
        {"id":"ppfl_2","text":"Differential privacy can be applied to gradients in FL to bound leakage.","metadata":{"source":"demo"}},
        {"id":"ppfl_3","text":"Homomorphic encryption enables computation on encrypted data in FL settings.","metadata":{"source":"demo"}},
    ]
    v.ingest_texts(items)
    print(json.dumps({"ingested": len(items)}))

