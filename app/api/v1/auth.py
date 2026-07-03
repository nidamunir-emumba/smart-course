"""Authentication endpoints — sign in / sign out / current user.

Stateless JWT bearer tokens: `login` returns a signed token the client sends as
`Authorization: Bearer <token>`. `logout` is a client-side token discard (a Redis
denylist can be added later for server-side revocation).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.postgres import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserRead
from app.services import users as user_service

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    user = await user_service.authenticate(session, data.email, data.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return Token(access_token=create_access_token(str(user.id)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: User = Depends(get_current_user)) -> None:
    # Stateless JWT: the client discards its token. Nothing to do server-side (yet).
    return None


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
