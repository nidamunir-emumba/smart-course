"""Qdrant = vector store for RAG retrieval over course content.

Chosen over pgvector/Pinecone/Weaviate for: self-hosted via docker (no SaaS lock-in),
strong metadata filtering (filter chunks by course_id/module_id at query time), and
first-class async client. One collection `course_chunks`, payload carries course_id.
"""
from qdrant_client import AsyncQdrantClient

from app.core.config import settings

COURSE_CHUNKS_COLLECTION = "course_chunks"

_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=settings.qdrant_url)
    return _client
