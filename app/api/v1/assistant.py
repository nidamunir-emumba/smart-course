"""AI learning assistant endpoints. STUB.

- POST /qa           : contextual Q&A over course content (RAG via app.ai.graph)
- POST /enhance      : instructor content generation (summaries/objectives/quizzes),
                       streamed back via StreamingResponse for long outputs.
"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/qa")
async def ask_question():
    """Retrieve relevant chunks from Qdrant, run the LangGraph RAG graph, answer."""
    raise NotImplementedError


@router.post("/enhance")
async def enhance_content():
    """Generate summaries/quizzes for instructors; supports streamed delivery."""
    raise NotImplementedError
