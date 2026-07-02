"""User service — registration and lookup."""
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate
from app.services.exceptions import ConflictError, NotFoundError


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    user = User(email=data.email, full_name=data.full_name, role=data.role)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(f"Email already registered: {data.email}") from exc
    await session.refresh(user)
    return user


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User not found: {user_id}")
    return user


async def require_role(session: AsyncSession, user_id: uuid.UUID, role: str) -> User:
    """Fetch a user and assert their role (used by course/enrollment services)."""
    user = await get_user(session, user_id)
    if user.role != role:
        raise NotFoundError(f"User {user_id} is not a {role}")
    return user


async def list_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())
