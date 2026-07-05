"""Analytics read models — denormalized counters in MongoDB.

Mongo is the designated home for cheap-to-read dashboard views (never the
source of truth). Writes are idempotent: every event carries a key that is
inserted into `analytics_applied` first (unique _id); a duplicate key means
this event was already counted — replays and workflow retries become no-ops.
"""
import logging
import uuid

from pymongo.errors import DuplicateKeyError

from app.db.mongo import get_db

logger = logging.getLogger(__name__)


async def record_enrollment(enrollment_id: uuid.UUID | str, course_id: uuid.UUID | str) -> bool:
    """Count one enrollment in the course + platform rollups.

    Returns True if applied, False if this enrollment was already counted
    (idempotency key = enrollment id).
    """
    db = get_db()
    try:
        await db.analytics_applied.insert_one({"_id": f"enrollment:{enrollment_id}"})
    except DuplicateKeyError:
        logger.info("analytics: enrollment %s already applied, skipping", enrollment_id)
        return False

    await db.course_analytics.update_one(
        {"_id": str(course_id)}, {"$inc": {"enrollments": 1}}, upsert=True
    )
    await db.platform_analytics.update_one(
        {"_id": "platform"}, {"$inc": {"total_enrollments": 1}}, upsert=True
    )
    return True
