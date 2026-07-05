"""User & role management (student / instructor / admin)."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_session
from app.schemas.user import UserCreate, UserRead
from app.services import notifications as notification_service
from app.services import users as user_service
from app.tasks import dispatch
from app.tasks.notifications import send_registration_welcome

router = APIRouter()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(data: UserCreate, session: AsyncSession = Depends(get_session)):
    user = await user_service.create_user(session, data)
    await notification_service.create(
        session,
        user.id,
        kind="welcome",
        title="Welcome to SmartCourse",
        body=(
            "Create your first course from My Courses."
            if user.role.value == "instructor"
            else "Browse the catalog and enroll in your first course."
        ),
        link="/instructor" if user.role.value == "instructor" else "/",
    )
    dispatch.fire(send_registration_welcome, user.email, user.full_name, user.role.value)
    return user


@router.get("", response_model=list[UserRead])
async def list_users(session: AsyncSession = Depends(get_session)):
    return await user_service.list_users(session)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await user_service.get_user(session, user_id)
