# =====================================================
# app/memory/vector_store.py
# VectorStore backend + KnowledgeBaseStore + LongTermMemoryStore
# =====================================================

from typing import List, Dict
from math import sqrt

try:
    import chromadb
    from chromadb.utils import embedding_functions
    _HAVE_CHROMA = True
except Exception:
    _HAVE_CHROMA = False


# =====================================================
# 🔹 Base VectorStore (Core Implementation)
# =====================================================
class VectorStore:
    """
    A simple pluggable vector storage backend.

    Supports:
        - Chroma (persistent vector DB)
        - Fallback: in-memory cosine similarity with random embeddings

    Args:
        path: Base path for persistent storage
        collection: Logical collection name
        use_cosine: Whether to use cosine similarity (default: True)
    """

    def __init__(self, path: str, collection: str, use_cosine: bool = True):
        self.collection_name = collection

        if _HAVE_CHROMA:
            self.client = chromadb.PersistentClient(path=path)
            self.embedder = embedding_functions.DefaultEmbeddingFunction()
            metadata = {"hnsw:space": "cosine" if use_cosine else "l2"}
            self.coll = self.client.get_or_create_collection(
                name=collection,
                embedding_function=self.embedder,
                metadata=metadata
            )
        else:
            self.docs: list[str] = []
            self.meta: list[dict] = []

    # =====================================================
    # Ingestion
    # =====================================================
    def ingest(self, docs: List[Dict]):
        """
        Add a batch of documents to the vector store.

        Each document should contain:
            - "text": str
            - "id" (optional): unique identifier
            - "metadata" (optional): dict with extra fields
        """
        if _HAVE_CHROMA:
            texts = [d["text"] for d in docs]
            ids = [d.get("id") or str(i) for i, d in enumerate(docs)]
            self.coll.add(
                ids=ids,
                documents=texts,
                metadatas=[d.get("metadata", {}) for d in docs]
            )
        else:
            for d in docs:
                self.docs.append(d["text"])
                self.meta.append(d.get("metadata", {}))

    # =====================================================
    # Querying
    # =====================================================
    def query(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Perform semantic search against the stored vectors.

        Args:
            query: Text query
            top_k: Number of results to return (default: 3)

        Returns:
            A list of dicts containing:
                - "chunk": Retrieved text
                - "score": Similarity score (0–1)
                - "doc_id": Document ID
                - "metadata": Associated metadata
        """
        out = []
        if _HAVE_CHROMA:
            res = self.coll.query(query_texts=[query], n_results=top_k)
            for i in range(len(res["ids"][0])):
                out.append({
                    "chunk": res["documents"][0][i],
                    "score": 1 - res["distances"][0][i],
                    "doc_id": res["ids"][0][i],
                    "metadata": res["metadatas"][0][i],
                })
        else:
            # Fallback: cosine similarity using pseudo-random embeddings
            def emb(s):
                import random
                random.seed(hash(s) & 0xffffffff)
                return [random.random() for _ in range(64)]

            def cos(a, b):
                num = sum(x * y for x, y in zip(a, b))
                da = sqrt(sum(x * x for x in a))
                db = sqrt(sum(x * x for x in b))
                return num / (da * db + 1e-9)

            q = emb(query)
            scored = [(i, cos(q, emb(t))) for i, t in enumerate(self.docs)]
            scored.sort(key=lambda x: x[1], reverse=True)

            for i, s in scored[:top_k]:
                out.append({
                    "chunk": self.docs[i],
                    "score": float(s),
                    "doc_id": str(i),
                    "metadata": self.meta[i]
                })
        return out





