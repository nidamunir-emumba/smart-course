"""Course/module/asset management + publishing.

Phase 1: `publish` flips the course to READY synchronously. Phase 2/4 replace it with the
durable Temporal ContentPublishingWorkflow (extract → chunk → embed → index → mark ready).
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.postgres import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.services import courses as course_service

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
    _: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await course_service.list_courses(session)


@router.get("/{course_id}", response_model=CourseRead)
async def get_course(
    course_id: uuid.UUID,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.get_course(session, course_id)


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
