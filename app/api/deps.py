"""Shared API dependencies: authentication and role-based authorization.

`get_current_user` validates the Bearer JWT and loads the acting user; `require_role`
builds a dependency that additionally asserts the user's role. Endpoints derive the
acting identity from the token — never from the request body.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.postgres import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.services import users as user_service
from app.services.exceptions import NotFoundError

_bearer = HTTPBearer(description="Paste the access_token from POST /api/v1/auth/login")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    try:
        user = await user_service.get_user(session, uuid.UUID(payload["sub"]))
    except (NotFoundError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists") from None
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Inactive user")
    return user


def require_role(*roles: UserRole):
    """Dependency factory: require the current user to hold one of `roles`."""

    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            allowed = ", ".join(r.value for r in roles)
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Requires role: {allowed}"
            )
        return user

    return _dep
