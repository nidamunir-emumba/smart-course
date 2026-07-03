"""Course service — CRUD for courses/modules/assets plus a placeholder publish.

NOTE: `publish_course` here just flips the status to READY. Phase 2/4 replace it with
the real content-processing pipeline (extract → chunk → embed → index) run under Temporal.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Asset, Course, Module
from app.models.enums import CourseStatus, UserRole
from app.models.user import User
from app.schemas.course import CourseCreate, CourseUpdate
from app.services.exceptions import ForbiddenError, NotFoundError
from app.services.users import require_role

_COURSE_LOADERS = (
    selectinload(Course.modules).selectinload(Module.assets),
    selectinload(Course.prerequisites),
)


def _require_owner(course: Course, actor: User) -> None:
    """Only the owning instructor (or an admin) may modify a course."""
    if actor.role == UserRole.ADMIN or course.instructor_id == actor.id:
        return
    raise ForbiddenError("You do not own this course")


async def create_course(
    session: AsyncSession, data: CourseCreate, instructor_id: uuid.UUID
) -> Course:
    await require_role(session, instructor_id, UserRole.INSTRUCTOR)

    course = Course(
        title=data.title,
        description=data.description,
        instructor_id=instructor_id,
        enrollment_limit=data.enrollment_limit,
        status=CourseStatus.DRAFT,
    )
    for m in data.modules:
        module = Module(title=m.title, order_index=m.order_index)
        module.assets = [
            Asset(
                title=a.title,
                type=a.type,
                content=a.content,
                url=a.url,
                order_index=a.order_index,
            )
            for a in m.assets
        ]
        course.modules.append(module)

    if data.prerequisite_ids:
        course.prerequisites = await _load_courses(session, data.prerequisite_ids)

    session.add(course)
    await session.commit()
    return await get_course(session, course.id)


async def get_course(session: AsyncSession, course_id: uuid.UUID) -> Course:
    result = await session.execute(
        select(Course).where(Course.id == course_id).options(*_COURSE_LOADERS)
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise NotFoundError(f"Course not found: {course_id}")
    return course


async def list_courses(session: AsyncSession) -> list[Course]:
    result = await session.execute(
        select(Course).options(*_COURSE_LOADERS).order_by(Course.created_at)
    )
    return list(result.scalars().unique().all())


async def update_course(
    session: AsyncSession, course_id: uuid.UUID, data: CourseUpdate, actor: User
) -> Course:
    course = await get_course(session, course_id)
    _require_owner(course, actor)
    if data.title is not None:
        course.title = data.title
    if data.description is not None:
        course.description = data.description
    if data.enrollment_limit is not None:
        course.enrollment_limit = data.enrollment_limit
    if data.prerequisite_ids is not None:
        course.prerequisites = await _load_courses(session, data.prerequisite_ids)
    await session.commit()
    return await get_course(session, course_id)


async def publish_course(
    session: AsyncSession, course_id: uuid.UUID, actor: User
) -> Course:
    """Placeholder publish (Phase 1): mark READY. Real pipeline arrives in Phase 2/4."""
    course = await get_course(session, course_id)
    _require_owner(course, actor)
    course.status = CourseStatus.READY
    await session.commit()
    return await get_course(session, course_id)


async def _load_courses(session: AsyncSession, ids: list[uuid.UUID]) -> list[Course]:
    result = await session.execute(select(Course).where(Course.id.in_(ids)))
    found = list(result.scalars().all())
    missing = set(ids) - {c.id for c in found}
    if missing:
        raise NotFoundError(f"Prerequisite course(s) not found: {sorted(map(str, missing))}")
    return found
