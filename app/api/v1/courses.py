"""Course/module/asset management + publishing.

Phase 1: `publish` flips the course to READY synchronously. Phase 2/4 replace it with the
durable Temporal ContentPublishingWorkflow (extract → chunk → embed → index → mark ready).
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.postgres import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.services import courses as course_service
from app.services.exceptions import NotFoundError

router = APIRouter()


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseCreate,
    user: User = Depends(require_role(UserRole.INSTRUCTOR)),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.create_course(session, data, instructor_id=user.id)


@router.get("", response_model=list[CourseRead])
async def list_courses(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Students see only published courses; instructors also see their own drafts."""
    return await course_service.list_courses(session, viewer=user, limit=limit, offset=offset)


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    course = await course_service.get_course(session, course_id)
    if not course_service.is_visible_to(course, user):
        # Don't leak the existence of unpublished courses to non-owners.
        raise NotFoundError(f"Course not found: {course_id}")
    return course


@router.patch("/{course_id}", response_model=CourseRead)
async def update_course(
    course_id: uuid.UUID,
    data: CourseUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.update_course(session, course_id, data, actor=user)


@router.post("/{course_id}/publish", response_model=CourseRead)
async def publish_course(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.publish_course(session, course_id, actor=user)


@router.post("/{course_id}/unpublish", response_model=CourseRead)
async def unpublish_course(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.unpublish_course(session, course_id, actor=user)


@router.post("/{course_id}/archive", response_model=CourseRead)
async def archive_course(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.archive_course(session, course_id, actor=user)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await course_service.delete_course(session, course_id, actor=user)
