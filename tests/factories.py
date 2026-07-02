"""Small async helpers to build domain objects in tests via the service layer."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AssetType, UserRole
from app.schemas.course import AssetCreate, CourseCreate, ModuleCreate
from app.schemas.user import UserCreate
from app.services import courses as course_service
from app.services import users as user_service


async def make_user(session: AsyncSession, role: UserRole, name: str = "Test"):
    email = f"{role.value}-{uuid.uuid4().hex[:8]}@example.com"
    return await user_service.create_user(
        session, UserCreate(email=email, full_name=name, role=role)
    )


async def make_course(
    session: AsyncSession,
    instructor_id: uuid.UUID,
    *,
    n_assets: int = 2,
    enrollment_limit: int | None = None,
    prerequisite_ids: list[uuid.UUID] | None = None,
    publish: bool = True,
):
    assets = [
        AssetCreate(title=f"Asset {i}", type=AssetType.TEXT, content="…", order_index=i)
        for i in range(n_assets)
    ]
    course = await course_service.create_course(
        session,
        CourseCreate(
            title="Intro Course",
            instructor_id=instructor_id,
            enrollment_limit=enrollment_limit,
            prerequisite_ids=prerequisite_ids or [],
            modules=[ModuleCreate(title="Module 1", order_index=0, assets=assets)],
        ),
    )
    if publish:
        course = await course_service.publish_course(session, course.id)
    return course
