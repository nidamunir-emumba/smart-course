"""AI assistant request/response schemas."""
import uuid

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    course_id: uuid.UUID
    # When set, the question is grounded in this specific lesson.
    asset_id: uuid.UUID | None = None
    question: str = Field(min_length=3, max_length=2000)


class AskResponse(BaseModel):
    answer: str
