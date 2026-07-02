"""LangGraph agent for the learning assistant. STUB.

Two capabilities share this graph:
  A. Contextual Q&A     — retrieve -> grade relevance -> generate grounded answer
  B. Content enhancement — generate summaries/objectives/quizzes for instructors

Graph nodes (sketch):
  retrieve -> (relevant?) -> generate -> END
                   └-> clarify (handle ambiguous/incomplete questions) -> END

Long generations stream token-by-token to the API layer for incremental delivery.
"""
from typing import TypedDict

from app.ai.llm import get_chat_model
from app.ai.retrieval import retrieve_context


class AssistantState(TypedDict, total=False):
    course_id: str
    question: str
    context: list[str]
    answer: str


def build_graph():
    """Compile and return the LangGraph app. TODO: define nodes/edges."""
    _ = (get_chat_model, retrieve_context, AssistantState)
    raise NotImplementedError
