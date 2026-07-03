"""Enrollment / progress / certificate response schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import EnrollmentStatus


class EnrollmentCreate(BaseModel):
    # student_id is derived from the authenticated user, not the request body.
    course_id: uuid.UUID


class ProgressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_assets: int
    completed_assets: int
    percent_complete: float
    last_activity_at: datetime | None


class CertificateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    serial: str
    issued_at: datetime


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    status: EnrollmentStatus
    completed_at: datetime | None
    created_at: datetime
    progress: ProgressRead | None = None
    certificate: CertificateRead | None = None
