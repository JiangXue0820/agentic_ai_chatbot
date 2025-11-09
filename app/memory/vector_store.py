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
                metadata = res["metadatas"][0][i] or {}
                out.append({
                    "chunk": res["documents"][0][i],
                    "score": 1 - res["distances"][0][i],
                    "doc_id": metadata.get("doc_id", res["ids"][0][i]),
                    "metadata": metadata,
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
                metadata = self.meta[i] if i < len(self.meta) else {}
                out.append({
                    "chunk": self.docs[i],
                    "score": float(s),
                    "doc_id": metadata.get("doc_id", str(i)),
                    "metadata": metadata,
                })
        return out

    # =====================================================
    # Document Management
    # =====================================================
    def list_documents(self) -> List[Dict]:
        """
        Return the list of documents currently stored in the vector store.

        Each item contains:
            - doc_id: Unique identifier for the document
            - filename: Original filename if available
            - uploaded_at: ISO timestamp string if available
        """
        documents: dict[str, Dict[str, str]] = {}

        if _HAVE_CHROMA:
            res = self.coll.get(include=["metadatas"])
            for meta in res.get("metadatas", []) or []:
                if not isinstance(meta, dict):
                    continue
                doc_id = meta.get("doc_id")
                if not doc_id:
                    continue
                documents.setdefault(
                    doc_id,
                    {
                        "doc_id": doc_id,
                        "filename": meta.get("filename", doc_id),
                        "uploaded_at": meta.get("uploaded_at", ""),
                    },
                )
        else:
            for meta in self.meta:
                if not isinstance(meta, dict):
                    continue
                doc_id = meta.get("doc_id")
                if not doc_id:
                    continue
                documents.setdefault(
                    doc_id,
                    {
                        "doc_id": doc_id,
                        "filename": meta.get("filename", doc_id),
                        "uploaded_at": meta.get("uploaded_at", ""),
                    },
                )

        return list(documents.values())

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete all chunks belonging to the specified document.

        Returns True if any chunks were removed, False otherwise.
        """
        if _HAVE_CHROMA:
            existing = self.coll.get(where={"doc_id": doc_id})
            if not existing.get("ids"):
                return False
            self.coll.delete(where={"doc_id": doc_id})
            return True

        if not getattr(self, "docs", None):
            return False

        kept_docs: list[str] = []
        kept_meta: list[dict] = []
        removed = False

        for text, meta in zip(self.docs, self.meta):
            if isinstance(meta, dict) and meta.get("doc_id") == doc_id:
                removed = True
                continue
            kept_docs.append(text)
            kept_meta.append(meta)

        if removed:
            self.docs = kept_docs
            self.meta = kept_meta

        return removed

    def delete_all(self):
        """Clear the entire collection."""
        if _HAVE_CHROMA:
            res = self.coll.get(include=["metadatas"])
            ids: list[str] = []
            for idx, metas in enumerate(res.get("metadatas", []) or []):
                if isinstance(metas, dict) and metas.get("doc_id"):
                    ids.append(res["ids"][idx])
                else:
                    ids.append(res["ids"][idx])
            if ids:
                self.coll.delete(ids=ids)
        else:
            self.docs = []
            self.meta = []





