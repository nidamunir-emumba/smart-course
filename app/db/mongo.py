"""MongoDB = flexible content documents and denormalized read models.

Holds parsed course content (modules -> lessons -> chunks), and materialized
analytics views that are cheap to read for dashboards. Not the source of truth
for transactional state — that is PostgreSQL.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_url)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongo_db]
