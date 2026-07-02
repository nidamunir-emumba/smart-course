"""RAG retrieval over course content in Qdrant. STUB.

Embeds the question, queries the `course_chunks` collection filtered by course_id,
returns the top-k chunks to ground the assistant's answer.
"""
from app.db.qdrant import COURSE_CHUNKS_COLLECTION, get_qdrant


async def retrieve_context(course_id: str, question: str, k: int = 5) -> list[str]:
    _ = (course_id, question, k, COURSE_CHUNKS_COLLECTION, get_qdrant)
    raise NotImplementedError
