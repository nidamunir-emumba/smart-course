"""Notification service — the in-app feed (create, list, unread count, mark read).

Rows are created inline in the same transaction as the action they announce
(enroll, complete, register), so the feed never misses an event the way a
dropped email can. Email delivery stays in Celery (app/tasks/notifications.py).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.services.exceptions import NotFoundError


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    kind: str,
    title: str,
    body: str,
    link: str | None = None,
    commit: bool = True,
) -> Notification:
    """Add a feed item. Pass commit=False to join a caller-managed transaction."""
    notification = Notification(user_id=user_id, kind=kind, title=title, body=body, link=link)
    session.add(notification)
    if commit:
        await session.commit()
        await session.refresh(notification)
    return notification


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int = 20, offset: int = 0
) -> list[Notification]:
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def unread_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    )
    return int(result.scalar_one())


async def mark_read(
    session: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
) -> Notification:
    """Mark one of the user's own notifications read (idempotent)."""
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        # Not-found for foreign rows too: don't reveal other users' notification ids.
        raise NotFoundError(f"Notification not found: {notification_id}")
    if notification.read_at is None:
        notification.read_at = _now()
        await session.commit()
    return notification


async def mark_all_read(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Mark every unread notification read; returns how many changed."""
    result = await session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=_now())
    )
    await session.commit()
    return result.rowcount or 0
