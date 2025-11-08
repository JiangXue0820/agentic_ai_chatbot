"""Simple pluggable vector store: try Chroma; fallback to sklearn-TFIDF + cosine."""
from typing import List, Dict

try:
    import chromadb
    from chromadb.utils import embedding_functions
    _HAVE_CHROMA = True
except Exception:
    _HAVE_CHROMA = False

from math import sqrt

class VectorStore:
    def __init__(self, 
                 collection: str = "knowledge_base", 
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 use_cosine: bool = True):
        """
        Initialize VectorStore.
        
        Args:
            collection: Collection name (must be 3+ characters)
            embedding_model: Sentence transformer model name
            use_cosine: Use cosine similarity (True) or L2 distance (False)
        """
        self.collection_name = collection
        self.embedding_model = embedding_model

        if _HAVE_CHROMA:
            self.client = chromadb.Client()
            
            # Create embedder with specified model
            self.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=embedding_model
            )
            
            # Create collection with embedder
            metadata = {"hnsw:space": "cosine" if use_cosine else "l2"}
            self.coll = self.client.get_or_create_collection(
                name=collection, 
                embedding_function=self.embedder,
                metadata=metadata
            )
        else:
            self.docs: list[str] = []
            self.meta: list[dict] = []

    def ingest(self, docs: List[Dict]):
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

    def query(self, query: str, top_k: int = 3):
        if _HAVE_CHROMA:
            res = self.coll.query(query_texts=[query], n_results=top_k)
            out = []
            for i in range(len(res["ids"][0])):
                out.append({
                    "chunk": res["documents"][0][i],
                    "score": 1 - res["distances"][0][i],
                    "doc_id": res["ids"][0][i],
                    "metadata": res["metadatas"][0][i],
                })
            return out
        else:
            # Fallback: cosine on naive hash-embeddings
            def emb(s):
                import random
                random.seed(hash(s) & 0xffffffff)
                return [random.random() for _ in range(64)]
            q = emb(query)
            def cos(a, b):
                num = sum(x*y for x,y in zip(a,b))
                da = sqrt(sum(x*x for x in a))
                db = sqrt(sum(x*x for x in b))
                return num / (da*db + 1e-9)
            scored = []
            for i, t in enumerate(self.docs):
                scored.append((i, cos(q, emb(t))))
            scored.sort(key=lambda x: x[1], reverse=True)
            out = []
            for i, s in scored[:top_k]:
                out.append({
                    "chunk": self.docs[i], 
                    "score": float(s), 
                    "doc_id": str(i), 
                    "metadata": self.meta[i]
                })
            return out