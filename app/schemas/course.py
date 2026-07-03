"""Course / module / asset request & response schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AssetType, CourseStatus


# ---------- Asset ----------
class AssetCreate(BaseModel):
    title: str
    type: AssetType
    content: str | None = None
    url: str | None = None
    order_index: int = 0


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    type: AssetType
    content: str | None
    url: str | None
    order_index: int


# ---------- Module ----------
class ModuleCreate(BaseModel):
    title: str
    order_index: int = 0
    assets: list[AssetCreate] = Field(default_factory=list)


class ModuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    order_index: int
    assets: list[AssetRead] = Field(default_factory=list)


# ---------- Course ----------
class CourseCreate(BaseModel):
    # instructor_id is derived from the authenticated user, not the request body.
    title: str
    description: str | None = None
    enrollment_limit: int | None = None
    prerequisite_ids: list[uuid.UUID] = Field(default_factory=list)
    modules: list[ModuleCreate] = Field(default_factory=list)


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    enrollment_limit: int | None = None
    prerequisite_ids: list[uuid.UUID] | None = None


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    instructor_id: uuid.UUID
    status: CourseStatus
    enrollment_limit: int | None
    created_at: datetime
    updated_at: datetime
    modules: list[ModuleRead] = Field(default_factory=list)
