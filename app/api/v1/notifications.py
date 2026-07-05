"""Notification feed endpoints — always scoped to the authenticated user."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_session
from app.models.user import User
from app.schemas.notification import NotificationRead, UnreadCount
from app.services import notifications as notification_service

router = APIRouter()


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await notification_service.list_for_user(session, user.id, limit=limit, offset=offset)


@router.get("/unread-count", response_model=UnreadCount)
async def get_unread_count(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return UnreadCount(unread=await notification_service.unread_count(session, user.id))


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await notification_service.mark_read(session, notification_id, user.id)


@router.post("/read-all", response_model=UnreadCount)
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await notification_service.mark_all_read(session, user.id)
    return UnreadCount(unread=0)
