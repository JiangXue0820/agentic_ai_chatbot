"""
Vector Database (VDB) Tool Adapter
Provides semantic search and knowledge retrieval using ChromaDB.
"""
import logging
from typing import List, Dict, Any

from app.memory.vector_store import VectorStore
from app.utils.config import KNOWLEDGE_PATH
from app.utils.file_parser import extract_text
from app.utils.text_splitter import chunk_text

logger = logging.getLogger(__name__)


# =====================================================
# 🔹 Knowledge Base Wrapper
# =====================================================
class KnowledgeBaseStore:
    """
    High-level wrapper for document knowledge storage and retrieval.

    Uses Chroma or local fallback depending on environment.
    """

    def __init__(self):
        self.vstore = VectorStore(
            path=KNOWLEDGE_PATH,
            collection="knowledge_base"
        )

    def ingest_docs(self, docs: List[Dict]):
        """Ingest a batch of documents into the knowledge base."""
        self.vstore.ingest(docs)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search the knowledge base for relevant information."""
        return self.vstore.query(query, top_k)


class VDBAdapter:
    """
    Vector database knowledge retrieval tool.
    
    Provides semantic search over ingested documents using embeddings.
    Powered by ChromaDB with sentence-transformers for embeddings.
    
    Attributes:
        description: Human-readable description of the tool
        parameters: JSON schema defining the tool's parameters
        store: KnowledgeBaseStore instance for document storage and retrieval
    """
    
    # Tool metadata for ToolRegistry
    description = "Search knowledge base using semantic similarity to find relevant information"
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query or question to find relevant knowledge",
                "required": True
            },
            "top_k": {
                "type": "integer",
                "description": "Number of most relevant results to return (default: 3)",
                "default": 3,
                "minimum": 1,
                "maximum": 10
            },
            "k": {
                "type": "integer",
                "description": "Alias for 'top_k' parameter",
                "default": 3
            }
        },
        "required": ["query"]
    }
    
    def __init__(self):
        """
        Initialize VDB adapter with a KnowledgeBaseStore instance.
        
        The store uses ChromaDB collection named "knowledge_base".
        """
        self.store = KnowledgeBaseStore()
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Unified entry point for the tool (required by ToolRegistry).
        
        Args:
            **kwargs: Flexible keyword arguments that must include:
                - query (str): Search query string
                - top_k (int, optional): Number of results (default: 3)
                - k (int, optional): Alternative name for top_k
        
        Returns:
            Dict containing:
                - query (str): Original query
                - results (List[Dict]): List of matching documents with:
                    - chunk (str): Document text
                    - score (float): Similarity score (0-1)
                    - doc_id (str): Document identifier
                    - metadata (Dict): Additional document metadata
                - count (int): Number of results returned
        
        Raises:
            ValueError: If query parameter is missing
        
        Example:
            >>> adapter.run(query="What is federated learning?", top_k=3)
            {
                "query": "What is federated learning?",
                "results": [
                    {
                        "chunk": "Federated learning is...",
                        "score": 0.89,
                        "doc_id": "doc_123",
                        "metadata": {...}
                    }
                ],
                "count": 3
            }
        """
        query = kwargs.get("query")
        if not query:
            raise ValueError("Parameter 'query' is required for vector database search")
        
        # Support both 'top_k' and 'k' parameter names
        top_k = kwargs.get("top_k") or kwargs.get("k", 3)
        
        results = self.query(query=query, top_k=top_k)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    
    def ingest_texts(self, items: List[Dict]) -> None:
        """
        Ingest documents into the vector store.
        
        Args:
            items: List of document dictionaries with structure:
                - id (str): Unique document identifier
                - text (str): Document text content
                - metadata (Dict, optional): Additional metadata
        
        Example:
            >>> adapter.ingest_texts([
            ...     {
            ...         "id": "doc1",
            ...         "text": "Federated learning enables...",
            ...         "metadata": {"source": "paper", "year": 2023}
            ...     }
            ... ])
        """
        self.store.ingest_docs(items)

    def ingest_file(self, filename: str, file_bytes: bytes) -> Dict[str, Any]:
        """
        Parse a document, split into chunks, and ingest into the vector store.
        """
        pages = extract_text(file_bytes, filename)

        items: List[Dict[str, Any]] = []
        empty_pages = 0

        for page_data in pages:
            page_number = page_data.get("page")
            page_text = (page_data.get("text") or "").strip()

            if not page_text:
                empty_pages += 1
                continue

            chunks = chunk_text(page_text)
            for idx, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                items.append(
                    {
                        "id": f"{filename}_p{page_number}_c{idx}",
                        "text": chunk,
                        "metadata": {
                            "filename": filename,
                            "page": page_number,
                            "chunk_index": idx,
                        },
                    }
                )

        if not items:
            raise ValueError("No extractable text found in document.")

        self.ingest_texts(items)
        logger.info(
            "Ingested %s chunks from %s (empty pages skipped: %s)",
            len(items),
            filename,
            empty_pages,
        )

        return {"chunks": len(items), "empty_pages": empty_pages, "filename": filename}
    
    def query(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar documents.
        
        Args:
            query: Search query text
            top_k: Number of top results to return (default: 3)
        
        Returns:
            List of dictionaries containing:
                - chunk (str): Matched document text
                - score (float): Similarity score (higher is better)
                - doc_id (str): Document identifier
                - metadata (Dict): Document metadata
        
        Example:
            >>> results = adapter.query("privacy in ML", top_k=2)
            >>> for result in results:
            ...     print(f"Score: {result['score']}, Text: {result['chunk'][:50]}")
        """
        return self.store.search(query, top_k)
