from app.memory.vector_store import VectorStore

class VDBAdapter:
    def __init__(self):
        self.store = VectorStore("kb")

    def ingest_texts(self, items: list[dict]):
        # items: [{"id":..., "text":..., "metadata":{...}}]
        self.store.ingest(items)

    def query(self, query: str, top_k: int = 3):
        return self.store.query(query, top_k)
