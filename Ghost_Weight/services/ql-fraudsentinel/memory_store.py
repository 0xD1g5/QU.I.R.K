"""
memory_store.py — Persistent memory store for QL-FraudSentinel.

Backed by ChromaDB. Provides semantic retrieval of agent memories.

INTENTIONAL VULNERABILITY:
  Retrieved memories are injected directly into the scoring LLM context
  without validation or anomaly detection.

  An adversary who can write to the memory store (via POST /memory or via
  the agent channel from QL-DocuIntel) can plant adversarial embeddings that
  surface during legitimate fraud scoring queries, influencing LLM decisions.

  This is the attack surface for:
    Phase 5: Long-Term Memory Poisoning (AML-T0040)
"""

import os
import uuid
import logging
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MEMORY_PATH = os.getenv("MEMORY_PATH", "/app/data/memory")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
COLLECTION_NAME = "fraudsentinel_memory"


class MemoryStore:
    """ChromaDB-backed persistent memory store for the fraud scoring agent."""

    def __init__(self):
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None
        self._embedder: Optional[SentenceTransformer] = None

    def _get_client(self) -> chromadb.PersistentClient:
        if self._client is None:
            os.makedirs(MEMORY_PATH, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=MEMORY_PATH,
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
            self._embedder = SentenceTransformer(EMBEDDING_MODEL)
        return self._embedder

    def store(self, key: str, content: str, metadata: dict = None) -> str:
        """
        Add or update a memory entry.
        Returns the memory_id.
        """
        collection = self._get_collection()
        embedder = self._get_embedder()
        embedding = embedder.encode([content])[0].tolist()
        memory_id = key or str(uuid.uuid4())

        collection.upsert(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "key": memory_id,
                **(metadata or {})
            }]
        )
        logger.info(f"Memory stored: {memory_id}")
        return memory_id

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        """
        Semantic retrieval of top-k relevant memories.

        INTENTIONAL: Returns raw memory content — caller injects directly
        into LLM scoring context without filtering.
        """
        collection = self._get_collection()
        if collection.count() == 0:
            return []

        embedder = self._get_embedder()
        query_embedding = embedder.encode([query])[0].tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        memories = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            memories.append({
                "key": meta.get("key", ""),
                "content": doc,    # ← raw content, injected into scoring context
                "similarity": round(1.0 - dist, 4),
                "metadata": meta
            })
        return memories

    def list(self) -> list[dict]:
        """
        Return all memory entries (for Red Team visualization).
        """
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        results = collection.get(include=["documents", "metadatas"])
        entries = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            entries.append({
                "key": meta.get("key", ""),
                "content_preview": doc[:200],
                "metadata": meta
            })
        return sorted(entries, key=lambda x: x["key"])

    def delete(self, key: str) -> bool:
        """Delete a memory entry by key."""
        try:
            collection = self._get_collection()
            collection.delete(ids=[key])
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all memories."""
        client = self._get_client()
        client.delete_collection(COLLECTION_NAME)
        self._collection = None
        logger.info("Memory store cleared")


# Module-level singleton
_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
