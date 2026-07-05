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

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.certificate import Certificate
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.enums import CourseStatus, EnrollmentStatus, UserRole
from app.models.lesson_completion import LessonCompletion
from app.models.progress import Progress
from app.schemas.enrollment import EnrollmentCreate
from app.services.courses import get_course
from app.services.exceptions import (
    ConflictError,
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
    selectinload(Enrollment.completions),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def enroll(
    session: AsyncSession, data: EnrollmentCreate, student_id: uuid.UUID
) -> Enrollment:
    await require_role(session, student_id, UserRole.STUDENT)
    course = await get_course(session, data.course_id)  # loads modules/assets + prerequisites

    if course.status != CourseStatus.READY:
        raise CourseNotPublishedError(f"Course {course.id} is not open for enrollment")

    if await _active_enrollment(session, student_id, data.course_id) is not None:
        raise DuplicateEnrollmentError("Student is already actively enrolled in this course")

    if course.enrollment_limit is not None:
        active = await _active_count(session, data.course_id)
        if active >= course.enrollment_limit:
            raise EnrollmentLimitReachedError("Course enrollment limit reached")

    if course.prerequisites:
        completed = await _completed_course_ids(session, student_id)
        missing = [str(p.id) for p in course.prerequisites if p.id not in completed]
        if missing:
            raise PrerequisitesNotMetError(f"Unmet prerequisite course(s): {missing}")

    total_assets = sum(len(m.assets) for m in course.modules)
    enrollment = Enrollment(
        student_id=student_id,
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
        select(Enrollment)
        .where(Enrollment.id == enrollment_id)
        .options(*_ENROLLMENT_LOADERS)
        # Refresh identity-mapped rows: lesson toggles use bulk insert/delete,
        # which the already-loaded `completions` collection wouldn't reflect.
        .execution_options(populate_existing=True)
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
    """Set completion by count: marks the first N lessons (course order) complete.

    Kept for bulk actions ("complete all"); per-lesson state is the source of
    truth, so the requested count is materialized as completion rows.
    """
    enrollment = await get_enrollment(session, enrollment_id)
    course = await get_course(session, enrollment.course_id)
    asset_ids = _ordered_asset_ids(course)

    n = max(0, min(completed_assets, len(asset_ids)))
    await session.execute(
        delete(LessonCompletion).where(LessonCompletion.enrollment_id == enrollment_id)
    )
    session.add_all(
        LessonCompletion(enrollment_id=enrollment_id, asset_id=aid) for aid in asset_ids[:n]
    )
    _apply_progress(enrollment, completed=n)

    await session.commit()
    return await get_enrollment(session, enrollment_id)


async def complete_lesson(
    session: AsyncSession, enrollment_id: uuid.UUID, asset_id: uuid.UUID
) -> Enrollment:
    """Mark one lesson complete (idempotent); auto-completes the course at 100%."""
    enrollment, asset_ids = await _lesson_toggle_target(session, enrollment_id, asset_id)

    already = {c.asset_id for c in enrollment.completions}
    if asset_id not in already:
        session.add(LessonCompletion(enrollment_id=enrollment_id, asset_id=asset_id))
        _apply_progress(enrollment, completed=len(already) + 1)
        await session.commit()
    return await get_enrollment(session, enrollment_id)


async def uncomplete_lesson(
    session: AsyncSession, enrollment_id: uuid.UUID, asset_id: uuid.UUID
) -> Enrollment:
    """Unmark a completed lesson (idempotent)."""
    enrollment, _ = await _lesson_toggle_target(session, enrollment_id, asset_id)

    already = {c.asset_id for c in enrollment.completions}
    if asset_id in already:
        await session.execute(
            delete(LessonCompletion).where(
                LessonCompletion.enrollment_id == enrollment_id,
                LessonCompletion.asset_id == asset_id,
            )
        )
        _apply_progress(enrollment, completed=len(already) - 1)
        await session.commit()
    return await get_enrollment(session, enrollment_id)


# ---------- internal helpers ----------
def _ordered_asset_ids(course: Course) -> list[uuid.UUID]:
    """All lesson (asset) ids in reading order: module order, then asset order."""
    ids: list[uuid.UUID] = []
    for module in sorted(course.modules, key=lambda m: m.order_index):
        ids.extend(a.id for a in sorted(module.assets, key=lambda a: a.order_index))
    return ids


async def _lesson_toggle_target(
    session: AsyncSession, enrollment_id: uuid.UUID, asset_id: uuid.UUID
) -> tuple[Enrollment, list[uuid.UUID]]:
    """Shared validation for lesson toggles: enrollment ACTIVE, asset in course."""
    enrollment = await get_enrollment(session, enrollment_id)
    if enrollment.status != EnrollmentStatus.ACTIVE:
        raise ConflictError("Enrollment is not active")
    course = await get_course(session, enrollment.course_id)
    asset_ids = _ordered_asset_ids(course)
    if asset_id not in asset_ids:
        raise NotFoundError(f"Lesson not found in this course: {asset_id}")
    return enrollment, asset_ids


def _apply_progress(enrollment: Enrollment, *, completed: int) -> None:
    """Update counters from a completion count; auto-complete + certificate at 100%."""
    progress = enrollment.progress
    if progress is None:
        progress = Progress(total_assets=0, completed_assets=0, percent_complete=0.0)
        enrollment.progress = progress

    total = progress.total_assets
    progress.completed_assets = max(0, min(completed, total)) if total else completed
    progress.percent_complete = (progress.completed_assets / total * 100.0) if total else 100.0
    progress.last_activity_at = _now()

    if progress.percent_complete >= 100.0 and enrollment.status == EnrollmentStatus.ACTIVE:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = _now()
        if enrollment.certificate is None:
            enrollment.certificate = Certificate(serial=_make_serial())


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
