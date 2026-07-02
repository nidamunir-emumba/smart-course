"""Enrollment endpoints — synchronous in Phase 1.

Enrollment rules (duplicate/limit/prerequisite/history) live in the enrollment service.
Phase 4 moves this behind the durable Temporal EnrollmentWorkflow; the endpoint will then
start the workflow and return 202 instead of doing the work inline.
"""
import uuid

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_session
from app.schemas.enrollment import EnrollmentCreate, EnrollmentRead
from app.services import enrollments as enrollment_service

router = APIRouter()


class ProgressUpdate(BaseModel):
    completed_assets: int = Field(ge=0)


@router.post("", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
async def enroll(data: EnrollmentCreate, session: AsyncSession = Depends(get_session)):
    return await enrollment_service.enroll(session, data)


@router.get("/{enrollment_id}", response_model=EnrollmentRead)
async def get_enrollment(enrollment_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await enrollment_service.get_enrollment(session, enrollment_id)


@router.get("/student/{student_id}", response_model=list[EnrollmentRead])
async def list_student_enrollments(
    student_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    return await enrollment_service.list_for_student(session, student_id)


@router.post("/{enrollment_id}/progress", response_model=EnrollmentRead)
async def update_progress(
    enrollment_id: uuid.UUID,
    data: ProgressUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Set the number of completed assets; auto-completes + issues a certificate at 100%."""
    return await enrollment_service.set_progress(session, enrollment_id, data.completed_assets)
