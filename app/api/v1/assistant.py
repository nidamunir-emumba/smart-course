"""AI learning assistant endpoints.

- POST /qa      : contextual Q&A, grounded in the course/lesson being read
                  (Phase 1: context straight from Postgres; Phase 2 upgrades
                  the grounding to RAG retrieval over Qdrant via app.ai.graph).
- POST /enhance : instructor content generation (summaries/objectives/quizzes),
                  streamed back via StreamingResponse. STUB — Phase 2.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import qa
from app.api.deps import get_current_user
from app.db.postgres import get_session
from app.models.user import User
from app.schemas.assistant import AskRequest, AskResponse
from app.services import courses as course_service
from app.services.exceptions import NotFoundError

router = APIRouter()


@router.post("/qa", response_model=AskResponse)
async def ask_question(
    data: AskRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Answer a student's question, grounded in the course (and lesson) they're reading."""
    course = await course_service.get_course(session, data.course_id)
    if not course_service.is_visible_to(course, user):
        raise NotFoundError(f"Course not found: {data.course_id}")

    asset = None
    if data.asset_id is not None:
        asset = next(
            (a for m in course.modules for a in m.assets if a.id == data.asset_id), None
        )
        if asset is None:
            raise NotFoundError(f"Lesson not found in this course: {data.asset_id}")

    answer = await qa.answer_question(course, asset, data.question)
    return AskResponse(answer=answer)


@router.post("/enhance")
async def enhance_content():
    """Generate summaries/quizzes for instructors; supports streamed delivery."""
    raise NotImplementedError
