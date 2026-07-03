"""Module & asset editing for a course (instructor-owned, draft courses only).

Mounted under the /courses prefix. Every operation returns the full updated course so
the client always sees the current module/asset structure. Ownership and the draft-only
rule are enforced in the course service.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.postgres import get_session
from app.models.user import User
from app.schemas.course import (
    AssetCreate,
    AssetUpdate,
    CourseRead,
    ModuleCreate,
    ModuleUpdate,
)
from app.services import courses as course_service

router = APIRouter()


# ---------- modules ----------
@router.post(
    "/{course_id}/modules", response_model=CourseRead, status_code=status.HTTP_201_CREATED
)
async def add_module(
    course_id: uuid.UUID,
    data: ModuleCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.add_module(session, course_id, data, actor=user)


@router.patch("/{course_id}/modules/{module_id}", response_model=CourseRead)
async def update_module(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    data: ModuleUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.update_module(session, course_id, module_id, data, actor=user)


@router.delete("/{course_id}/modules/{module_id}", response_model=CourseRead)
async def delete_module(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.delete_module(session, course_id, module_id, actor=user)


# ---------- assets ----------
@router.post(
    "/{course_id}/modules/{module_id}/assets",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_asset(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    data: AssetCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.add_asset(session, course_id, module_id, data, actor=user)


@router.patch(
    "/{course_id}/modules/{module_id}/assets/{asset_id}", response_model=CourseRead
)
async def update_asset(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    asset_id: uuid.UUID,
    data: AssetUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.update_asset(
        session, course_id, module_id, asset_id, data, actor=user
    )


@router.delete(
    "/{course_id}/modules/{module_id}/assets/{asset_id}", response_model=CourseRead
)
async def delete_asset(
    course_id: uuid.UUID,
    module_id: uuid.UUID,
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await course_service.delete_asset(
        session, course_id, module_id, asset_id, actor=user
    )
