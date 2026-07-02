"""Enrollment service — enforces the enrollment rules (FR-1.3) and progress/completion.

Rules enforced on enroll:
  1. Student must exist and have the `student` role.
  2. Course must exist and be READY (published).
  3. No duplicate *active* enrollment (app check + DB partial-unique index as the race backstop).
  4. Enrollment limit (active enrollments) not exceeded.
  5. All prerequisite courses must be COMPLETED by the student.
Cancelled/completed rows are retained as history; re-enrollment creates a new active row.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.certificate import Certificate
from app.models.enrollment import Enrollment
from app.models.enums import CourseStatus, EnrollmentStatus, UserRole
from app.models.progress import Progress
from app.schemas.enrollment import EnrollmentCreate
from app.services.courses import get_course
from app.services.exceptions import (
    CourseNotPublishedError,
    DuplicateEnrollmentError,
    EnrollmentLimitReachedError,
    NotFoundError,
    PrerequisitesNotMetError,
)
from app.services.users import require_role

_ENROLLMENT_LOADERS = (
    selectinload(Enrollment.progress),
    selectinload(Enrollment.certificate),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def enroll(session: AsyncSession, data: EnrollmentCreate) -> Enrollment:
    await require_role(session, data.student_id, UserRole.STUDENT)
    course = await get_course(session, data.course_id)  # loads modules/assets + prerequisites

    if course.status != CourseStatus.READY:
        raise CourseNotPublishedError(f"Course {course.id} is not open for enrollment")

    if await _active_enrollment(session, data.student_id, data.course_id) is not None:
        raise DuplicateEnrollmentError("Student is already actively enrolled in this course")

    if course.enrollment_limit is not None:
        active = await _active_count(session, data.course_id)
        if active >= course.enrollment_limit:
            raise EnrollmentLimitReachedError("Course enrollment limit reached")

    if course.prerequisites:
        completed = await _completed_course_ids(session, data.student_id)
        missing = [str(p.id) for p in course.prerequisites if p.id not in completed]
        if missing:
            raise PrerequisitesNotMetError(f"Unmet prerequisite course(s): {missing}")

    total_assets = sum(len(m.assets) for m in course.modules)
    enrollment = Enrollment(
        student_id=data.student_id,
        course_id=data.course_id,
        status=EnrollmentStatus.ACTIVE,
        progress=Progress(total_assets=total_assets, completed_assets=0, percent_complete=0.0),
    )
    session.add(enrollment)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Lost a race against the partial-unique index (uq_active_enrollment).
        await session.rollback()
        raise DuplicateEnrollmentError("Student is already actively enrolled in this course") from exc
    return await get_enrollment(session, enrollment.id)


async def get_enrollment(session: AsyncSession, enrollment_id: uuid.UUID) -> Enrollment:
    result = await session.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id).options(*_ENROLLMENT_LOADERS)
    )
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        raise NotFoundError(f"Enrollment not found: {enrollment_id}")
    return enrollment


async def list_for_student(session: AsyncSession, student_id: uuid.UUID) -> list[Enrollment]:
    result = await session.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .options(*_ENROLLMENT_LOADERS)
        .order_by(Enrollment.created_at)
    )
    return list(result.scalars().all())


async def set_progress(
    session: AsyncSession, enrollment_id: uuid.UUID, completed_assets: int
) -> Enrollment:
    """Update completion count; auto-complete + issue a certificate at 100%."""
    enrollment = await get_enrollment(session, enrollment_id)
    progress = enrollment.progress
    if progress is None:
        progress = Progress(total_assets=0, completed_assets=0, percent_complete=0.0)
        enrollment.progress = progress

    total = progress.total_assets
    progress.completed_assets = max(0, min(completed_assets, total)) if total else completed_assets
    progress.percent_complete = (progress.completed_assets / total * 100.0) if total else 100.0
    progress.last_activity_at = _now()

    if progress.percent_complete >= 100.0 and enrollment.status == EnrollmentStatus.ACTIVE:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = _now()
        if enrollment.certificate is None:
            enrollment.certificate = Certificate(serial=_make_serial())

    await session.commit()
    return await get_enrollment(session, enrollment_id)


# ---------- internal helpers ----------
async def _active_enrollment(
    session: AsyncSession, student_id: uuid.UUID, course_id: uuid.UUID
) -> Enrollment | None:
    result = await session.execute(
        select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    return result.scalar_one_or_none()


async def _active_count(session: AsyncSession, course_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Enrollment)
        .where(Enrollment.course_id == course_id, Enrollment.status == EnrollmentStatus.ACTIVE)
    )
    return int(result.scalar_one())


async def _completed_course_ids(session: AsyncSession, student_id: uuid.UUID) -> set[uuid.UUID]:
    result = await session.execute(
        select(Enrollment.course_id).where(
            Enrollment.student_id == student_id,
            Enrollment.status == EnrollmentStatus.COMPLETED,
        )
    )
    return set(result.scalars().all())


def _make_serial() -> str:
    return f"CERT-{uuid.uuid4().hex[:12].upper()}"
