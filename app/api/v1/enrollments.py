"""Enrollment endpoints — synchronous in Phase 1.

Enrollment rules (duplicate/limit/prerequisite/history) live in the enrollment service.
Phase 4 moves this behind the durable Temporal EnrollmentWorkflow; the endpoint will then
start the workflow and return 202 instead of doing the work inline.
"""
import uuid

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.postgres import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.services import enrollments as enrollment_service
from app.services.exceptions import ForbiddenError
from app.schemas.enrollment import EnrollmentCreate, EnrollmentRead

router = APIRouter()


class ProgressUpdate(BaseModel):
    completed_assets: int = Field(ge=0)


def _require_self_or_staff(owner_id: uuid.UUID, user: User) -> None:
    """A student may only touch their own enrollments; instructors/admins may view any."""
    if user.role in (UserRole.INSTRUCTOR, UserRole.ADMIN) or owner_id == user.id:
        return
    raise ForbiddenError("You may only access your own enrollments")


@router.post("", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
async def enroll(
    data: EnrollmentCreate,
    user: User = Depends(require_role(UserRole.STUDENT)),
    session: AsyncSession = Depends(get_session),
):
    return await enrollment_service.enroll(session, data, student_id=user.id)


@router.get("/{enrollment_id}", response_model=EnrollmentRead)
async def get_enrollment(
    enrollment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    enrollment = await enrollment_service.get_enrollment(session, enrollment_id)
    _require_self_or_staff(enrollment.student_id, user)
    return enrollment


@router.get("/student/{student_id}", response_model=list[EnrollmentRead])
async def list_student_enrollments(
    student_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _require_self_or_staff(student_id, user)
    return await enrollment_service.list_for_student(session, student_id)


@router.post("/{enrollment_id}/progress", response_model=EnrollmentRead)
async def update_progress(
    enrollment_id: uuid.UUID,
    data: ProgressUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Set the number of completed assets; auto-completes + issues a certificate at 100%."""
    enrollment = await enrollment_service.get_enrollment(session, enrollment_id)
    # Only the owning student (or an admin) may advance progress.
    if user.role != UserRole.ADMIN and enrollment.student_id != user.id:
        raise ForbiddenError("You may only update your own progress")
    return await enrollment_service.set_progress(session, enrollment_id, data.completed_assets)
