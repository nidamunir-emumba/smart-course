"""Contextual course Q&A — Phase 1 of the learning assistant.

Grounding strategy: the context is built directly from the course content in
Postgres — the lesson the student is reading plus the course outline. No
retrieval step needed while questions are lesson-scoped. Phase 2 swaps the
context builder for RAG retrieval over Qdrant (app/ai/retrieval.py) so
whole-course and cross-lesson questions ground on the most relevant chunks.

Depends only on get_chat_model() per the provider-abstraction rule.
"""
import logging

from app.ai.llm import get_chat_model
from app.models.course import Asset, Course
from app.services.exceptions import AssistantUnavailableError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the SmartCourse learning assistant. The student asking is a beginner —
often a frontend developer learning backend concepts — so explain plainly,
use analogies to familiar frontend ideas where they help, and keep answers
focused and reasonably short.

Answer using ONLY the course context provided. If the context does not contain
the answer, say so and suggest which part of the course likely covers it.
Do not invent facts that are not in the context."""


def _build_context(course: Course, asset: Asset | None) -> str:
    """Course outline + (when lesson-scoped) the full lesson body."""
    lines = [f"Course: {course.title}"]
    if course.description:
        lines.append(f"About: {course.description}")

    lines.append("Outline:")
    for module in sorted(course.modules, key=lambda m: m.order_index):
        lines.append(f"  Module: {module.title}")
        for a in sorted(module.assets, key=lambda a: a.order_index):
            lines.append(f"    - {a.title}")

    if asset is not None and asset.content:
        lines.append(f'\nThe student is currently reading the lesson "{asset.title}":')
        lines.append(asset.content)

    return "\n".join(lines)


async def answer_question(course: Course, asset: Asset | None, question: str) -> str:
    context = _build_context(course, asset)
    try:
        model = get_chat_model()
        response = await model.ainvoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", f"Course context:\n{context}\n\nStudent's question: {question}"),
            ]
        )
    except Exception as exc:
        logger.warning("assistant LLM call failed: %s", exc)
        raise AssistantUnavailableError(
            "The assistant can't answer right now. If you run this locally, "
            "check that ANTHROPIC_API_KEY is set in .env."
        ) from exc

    content = response.content
    if isinstance(content, list):  # some providers return content blocks
        content = "".join(part if isinstance(part, str) else part.get("text", "") for part in content)
    return content
