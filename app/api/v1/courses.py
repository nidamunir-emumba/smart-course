"""Course/module/asset management + publishing.

Phase 1: `publish` flips the course to READY synchronously. Phase 2/4 replace it with the
durable Temporal ContentPublishingWorkflow (extract → chunk → embed → index → mark ready).
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.postgres import get_session
from app.models.enums import EnrollmentStatus, UserRole
from app.models.user import User
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate, LearningPathStep
from app.services import courses as course_service
from app.services import enrollments as enrollment_service
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


@router.get("/{course_id}/path", response_model=list[LearningPathStep])
async def get_learning_path(
    course_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """The automatically derived learning path for a course (target last).

    Prerequisites are resolved transitively — a prerequisite's own
    prerequisites are included, in the order a student should take them.
    Student callers get their completion/progress annotated on each step.
    """
    target = await course_service.get_course(session, course_id)
    if not course_service.is_visible_to(target, user):
        raise NotFoundError(f"Course not found: {course_id}")

    path = await course_service.learning_path(session, course_id)

    # For students, annotate each step with their best enrollment:
    # completed beats active beats cancelled (history rows).
    best: dict[uuid.UUID, tuple[EnrollmentStatus, float | None]] = {}
    if user.role == UserRole.STUDENT:
        rank = {
            EnrollmentStatus.COMPLETED: 2,
            EnrollmentStatus.ACTIVE: 1,
            EnrollmentStatus.CANCELLED: 0,
        }
        for e in await enrollment_service.list_for_student(session, user.id):
            current = best.get(e.course_id)
            if current is None or rank[e.status] > rank[current[0]]:
                best[e.course_id] = (
                    e.status,
                    e.progress.percent_complete if e.progress else None,
                )

    steps = []
    for course in path:
        status_, percent = best.get(course.id, (None, None))
        steps.append(
            LearningPathStep(
                course_id=course.id,
                title=course.title,
                description=course.description,
                course_status=course.status,
                is_target=course.id == course_id,
                met=status_ == EnrollmentStatus.COMPLETED,
                enrollment_status=status_,
                percent_complete=percent,
            )
        )
    return steps


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
