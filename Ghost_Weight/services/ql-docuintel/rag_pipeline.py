"""
rag_pipeline.py — ChromaDB vector store + RAG retrieval for QL-DocuIntel.

Provides:
  - Document chunking with configurable chunk size
  - Embedding generation via sentence-transformers (all-MiniLM-L6-v2)
  - ChromaDB persistent vector store
  - Similarity search: top-k chunks by cosine similarity
"""

import os
import uuid
import logging
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

VECTORSTORE_PATH = os.getenv("VECTORSTORE_PATH", "/app/data/vectorstore")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
COLLECTION_NAME = "qfl_documents"


class RAGPipeline:
    """ChromaDB-backed RAG pipeline for QL-DocuIntel."""

    def __init__(self):
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None
        self._embedder: Optional[SentenceTransformer] = None

    def _get_client(self) -> chromadb.PersistentClient:
        if self._client is None:
            os.makedirs(VECTORSTORE_PATH, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=VECTORSTORE_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
        return self._client

    def _get_collection(self):
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def _get_embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self._embedder = SentenceTransformer(EMBEDDING_MODEL)
        return self._embedder

    def chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = end - overlap
        return chunks

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of text chunks."""
        embedder = self._get_embedder()
        embeddings = embedder.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def store_document(self, document_id: str, text: str, metadata: dict = None) -> int:
        """
        Chunk, embed, and store a document in the vector store.
        Returns number of chunks stored.
        """
        collection = self._get_collection()
        chunks = self.chunk_text(text)
        if not chunks:
            return 0

        embeddings = self.embed_texts(chunks)
        ids = [f"{document_id}__chunk_{i}" for i in range(len(chunks))]
        metadatas = [{
            "document_id": document_id,
            "chunk_index": i,
            **(metadata or {})
        } for i in range(len(chunks))]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
        return len(chunks)

    def similarity_search(self, query: str, k: int = 5, document_id: str = None) -> list[dict]:
        """
        Retrieve top-k chunks most similar to query.
        Returns list of dicts with: text, document_id, chunk_index, distance.
        """
        collection = self._get_collection()
        query_embedding = self.embed_texts([query])[0]

        where_filter = {"document_id": document_id} if document_id else None

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, collection.count() or 1),
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        chunks = []
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            chunks.append({
                "text": doc,
                "document_id": meta.get("document_id", ""),
                "chunk_index": meta.get("chunk_index", i),
                "distance": dist,
                "similarity": 1.0 - dist,  # cosine distance → similarity
            })
        return chunks

    def list_documents(self) -> list[str]:
        """Return list of unique document_ids in the store."""
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        results = collection.get(include=["metadatas"])
        doc_ids = list({m.get("document_id", "") for m in results["metadatas"] if m.get("document_id")})
        return sorted(doc_ids)

    def clear(self) -> None:
        """Delete all documents from the vector store."""
        client = self._get_client()
        client.delete_collection(COLLECTION_NAME)
        self._collection = None
        logger.info("Vector store cleared")


# Module-level singleton
_pipeline: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
