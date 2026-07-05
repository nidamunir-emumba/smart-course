"""Course service — CRUD for courses/modules/assets plus a placeholder publish.

NOTE: `publish_course` here just flips the status to READY. Phase 2/4 replace it with
the real content-processing pipeline (extract → chunk → embed → index) run under Temporal.
"""
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Asset, Course, Module
from app.models.enums import CourseStatus, UserRole
from app.models.user import User
from app.schemas.course import (
    AssetCreate,
    AssetUpdate,
    CourseCreate,
    CourseUpdate,
    ModuleCreate,
    ModuleUpdate,
)
from app.services.exceptions import ConflictError, ForbiddenError, NotFoundError
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


async def learning_path(session: AsyncSession, course_id: uuid.UUID) -> list[Course]:
    """The automatically derived learning path ending at `course_id`.

    Walks prerequisites transitively (a prerequisite's prerequisites included),
    depth-first, and returns courses in the order a student should take them —
    target course last. Shared prerequisites appear once; cycles are guarded by
    the visited set.
    """
    ordered: list[Course] = []
    visited: set[uuid.UUID] = set()

    async def visit(cid: uuid.UUID) -> None:
        if cid in visited:
            return
        visited.add(cid)
        course = await get_course(session, cid)
        # Stable order: older prerequisites first (foundations before advanced).
        for prereq in sorted(course.prerequisites, key=lambda c: c.created_at):
            await visit(prereq.id)
        ordered.append(course)

    await visit(course_id)
    return ordered


async def list_courses(
    session: AsyncSession, *, viewer: User, limit: int = 50, offset: int = 0
) -> list[Course]:
    """List courses visible to `viewer`:

    - student: only READY courses,
    - instructor: READY courses plus their own (any status),
    - admin: everything.
    """
    stmt = select(Course).options(*_COURSE_LOADERS).order_by(Course.created_at)
    if viewer.role == UserRole.STUDENT:
        stmt = stmt.where(Course.status == CourseStatus.READY)
    elif viewer.role == UserRole.INSTRUCTOR:
        stmt = stmt.where(
            or_(Course.status == CourseStatus.READY, Course.instructor_id == viewer.id)
        )
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


def is_visible_to(course: Course, viewer: User) -> bool:
    """Same visibility rule as `list_courses`, for single-course reads."""
    if viewer.role == UserRole.ADMIN:
        return True
    if course.status == CourseStatus.READY:
        return True
    return course.instructor_id == viewer.id and viewer.role == UserRole.INSTRUCTOR


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
    """Placeholder publish (Phase 1): DRAFT -> READY. Real pipeline arrives in Phase 2/4."""
    course = await get_course(session, course_id)
    _require_owner(course, actor)
    if course.status != CourseStatus.DRAFT:
        raise ConflictError(f"Only draft courses can be published (is {course.status.value})")
    course.status = CourseStatus.READY
    await session.commit()
    return await get_course(session, course_id)


async def unpublish_course(
    session: AsyncSession, course_id: uuid.UUID, actor: User
) -> Course:
    """READY -> DRAFT, hiding the course from students again (existing enrollments retained)."""
    course = await get_course(session, course_id)
    _require_owner(course, actor)
    if course.status != CourseStatus.READY:
        raise ConflictError(f"Only ready courses can be unpublished (is {course.status.value})")
    course.status = CourseStatus.DRAFT
    await session.commit()
    return await get_course(session, course_id)


async def archive_course(
    session: AsyncSession, course_id: uuid.UUID, actor: User
) -> Course:
    """DRAFT/READY -> ARCHIVED. Terminal: no new enrollments; history is preserved."""
    course = await get_course(session, course_id)
    _require_owner(course, actor)
    if course.status == CourseStatus.ARCHIVED:
        raise ConflictError("Course is already archived")
    course.status = CourseStatus.ARCHIVED
    await session.commit()
    return await get_course(session, course_id)


async def delete_course(session: AsyncSession, course_id: uuid.UUID, actor: User) -> None:
    """Hard-delete a course. Only allowed while DRAFT (no enrollments can exist yet)."""
    course = await get_course(session, course_id)
    _require_owner(course, actor)
    if course.status != CourseStatus.DRAFT:
        raise ConflictError(
            f"Only draft courses can be deleted (is {course.status.value}); archive instead"
        )
    await session.delete(course)
    await session.commit()


# ---------- module & asset editing (draft courses only) ----------
def _require_editable(course: Course) -> None:
    if course.status != CourseStatus.DRAFT:
        raise ConflictError(
            f"Course content is editable only while draft (is {course.status.value}); "
            "unpublish it first"
        )


def _find_module(course: Course, module_id: uuid.UUID) -> Module:
    for module in course.modules:
        if module.id == module_id:
            return module
    raise NotFoundError(f"Module {module_id} not found in course {course.id}")


def _find_asset(module: Module, asset_id: uuid.UUID) -> Asset:
    for asset in module.assets:
        if asset.id == asset_id:
            return asset
    raise NotFoundError(f"Asset {asset_id} not found in module {module.id}")


async def _owned_editable_course(
    session: AsyncSession, course_id: uuid.UUID, actor: User
) -> Course:
    course = await get_course(session, course_id)
    _require_owner(course, actor)
    _require_editable(course)
    return course


async def add_module(
    session: AsyncSession, course_id: uuid.UUID, data: ModuleCreate, actor: User
) -> Course:
    course = await _owned_editable_course(session, course_id, actor)
    module = Module(course_id=course.id, title=data.title, order_index=data.order_index)
    module.assets = [
        Asset(title=a.title, type=a.type, content=a.content, url=a.url, order_index=a.order_index)
        for a in data.assets
    ]
    course.modules.append(module)
    await session.commit()
    return await get_course(session, course_id)


async def update_module(
    session: AsyncSession,
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    data: ModuleUpdate,
    actor: User,
) -> Course:
    course = await _owned_editable_course(session, course_id, actor)
    module = _find_module(course, module_id)
    if data.title is not None:
        module.title = data.title
    if data.order_index is not None:
        module.order_index = data.order_index
    await session.commit()
    return await get_course(session, course_id)


async def delete_module(
    session: AsyncSession, course_id: uuid.UUID, module_id: uuid.UUID, actor: User
) -> Course:
    course = await _owned_editable_course(session, course_id, actor)
    # Removing from the collection triggers delete-orphan and keeps the in-memory state correct.
    course.modules.remove(_find_module(course, module_id))
    await session.commit()
    return await get_course(session, course_id)


async def add_asset(
    session: AsyncSession,
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    data: AssetCreate,
    actor: User,
) -> Course:
    course = await _owned_editable_course(session, course_id, actor)
    module = _find_module(course, module_id)
    module.assets.append(
        Asset(
            title=data.title,
            type=data.type,
            content=data.content,
            url=data.url,
            order_index=data.order_index,
        )
    )
    await session.commit()
    return await get_course(session, course_id)


async def update_asset(
    session: AsyncSession,
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    asset_id: uuid.UUID,
    data: AssetUpdate,
    actor: User,
) -> Course:
    course = await _owned_editable_course(session, course_id, actor)
    asset = _find_asset(_find_module(course, module_id), asset_id)
    for field in ("title", "type", "content", "url", "order_index"):
        value = getattr(data, field)
        if value is not None:
            setattr(asset, field, value)
    await session.commit()
    return await get_course(session, course_id)


async def delete_asset(
    session: AsyncSession,
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    asset_id: uuid.UUID,
    actor: User,
) -> Course:
    course = await _owned_editable_course(session, course_id, actor)
    module = _find_module(course, module_id)
    module.assets.remove(_find_asset(module, asset_id))
    await session.commit()
    return await get_course(session, course_id)


async def _load_courses(session: AsyncSession, ids: list[uuid.UUID]) -> list[Course]:
    result = await session.execute(select(Course).where(Course.id.in_(ids)))
    found = list(result.scalars().all())
    missing = set(ids) - {c.id for c in found}
    if missing:
        raise NotFoundError(f"Prerequisite course(s) not found: {sorted(map(str, missing))}")
    return found
