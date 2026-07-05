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
from app.models.enums import EnrollmentStatus, UserRole
from app.models.user import User
from app.schemas.enrollment import EnrollmentCreate, EnrollmentRead
from app.services import courses as course_service
from app.services import enrollments as enrollment_service
from app.services import notifications as notification_service
from app.services import users as user_service
from app.services.exceptions import ForbiddenError
from app.tasks import dispatch
from app.tasks.notifications import send_completion_congrats, send_course_welcome

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
    enrollment = await enrollment_service.enroll(session, data, student_id=user.id)
    course = await course_service.get_course(session, data.course_id)
    await notification_service.create(
        session,
        user.id,
        kind="enrollment",
        title=f"You're enrolled: {course.title}",
        body=(
            "Work through the modules at your own pace — finishing every "
            "lesson earns your certificate."
        ),
        link=f"/courses/{course.id}",
    )
    dispatch.fire(send_course_welcome, user.email, user.full_name, course.title)
    return enrollment


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


async def _authorize_progress_change(
    session: AsyncSession, enrollment_id: uuid.UUID, user: User
) -> bool:
    """Authorize + capture pre-update status. Returns whether it was ACTIVE.

    Captured as a scalar before the update: the service mutates this same
    mapped instance (identity map), so comparing objects after would lie.
    """
    enrollment = await enrollment_service.get_enrollment(session, enrollment_id)
    # Only the owning student (or an admin) may advance progress.
    if user.role != UserRole.ADMIN and enrollment.student_id != user.id:
        raise ForbiddenError("You may only update your own progress")
    return enrollment.status == EnrollmentStatus.ACTIVE


async def _fire_completion_side_effects(
    session: AsyncSession, updated, was_active: bool
) -> None:
    """Congratulate exactly once — on the ACTIVE → COMPLETED transition."""
    if not (was_active and updated.status == EnrollmentStatus.COMPLETED and updated.certificate):
        return
    student = await user_service.get_user(session, updated.student_id)
    course = await course_service.get_course(session, updated.course_id)
    await notification_service.create(
        session,
        student.id,
        kind="completion",
        title=f"Course complete: {course.title}",
        body=f"Congratulations — your certificate is issued ({updated.certificate.serial}).",
        link=f"/certificate/{updated.id}",
    )
    dispatch.fire(
        send_completion_congrats,
        student.email,
        student.full_name,
        course.title,
        updated.certificate.serial,
    )


@router.post("/{enrollment_id}/progress", response_model=EnrollmentRead)
async def update_progress(
    enrollment_id: uuid.UUID,
    data: ProgressUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Set the number of completed assets; auto-completes + issues a certificate at 100%."""
    was_active = await _authorize_progress_change(session, enrollment_id, user)
    updated = await enrollment_service.set_progress(session, enrollment_id, data.completed_assets)
    await _fire_completion_side_effects(session, updated, was_active)
    return updated


async def _owned_enrollment(
    session: AsyncSession, enrollment_id: uuid.UUID, user: User
):
    """Fetch + assert the caller owns this enrollment (or is an admin)."""
    enrollment = await enrollment_service.get_enrollment(session, enrollment_id)
    if user.role != UserRole.ADMIN and enrollment.student_id != user.id:
        raise ForbiddenError("You may only manage your own enrollments")
    return enrollment


@router.post("/{enrollment_id}/unenroll", response_model=EnrollmentRead)
async def unenroll(
    enrollment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cancel an active enrollment; history is kept and the seat is freed."""
    await _owned_enrollment(session, enrollment_id, user)
    return await enrollment_service.unenroll(session, enrollment_id)


@router.post("/{enrollment_id}/archive", response_model=EnrollmentRead)
async def archive_enrollment(
    enrollment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Hide this enrollment from the student's default dashboard view."""
    await _owned_enrollment(session, enrollment_id, user)
    return await enrollment_service.set_archived(session, enrollment_id, True)


@router.post("/{enrollment_id}/unarchive", response_model=EnrollmentRead)
async def unarchive_enrollment(
    enrollment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Bring an archived enrollment back to the student's dashboard."""
    await _owned_enrollment(session, enrollment_id, user)
    return await enrollment_service.set_archived(session, enrollment_id, False)


@router.post("/{enrollment_id}/lessons/{asset_id}/complete", response_model=EnrollmentRead)
async def complete_lesson(
    enrollment_id: uuid.UUID,
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Mark one lesson complete; auto-completes the course + certificate at 100%."""
    was_active = await _authorize_progress_change(session, enrollment_id, user)
    updated = await enrollment_service.complete_lesson(session, enrollment_id, asset_id)
    await _fire_completion_side_effects(session, updated, was_active)
    return updated


@router.delete("/{enrollment_id}/lessons/{asset_id}/complete", response_model=EnrollmentRead)
async def uncomplete_lesson(
    enrollment_id: uuid.UUID,
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Unmark a completed lesson."""
    await _authorize_progress_change(session, enrollment_id, user)
    return await enrollment_service.uncomplete_lesson(session, enrollment_id, asset_id)
