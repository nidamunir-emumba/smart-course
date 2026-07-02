"""Content Publishing Workflow (Temporal). STUB.

Steps (each an idempotent activity, retried independently by Temporal):
  1. extract_content   — parse assets into modules/lessons
  2. chunk_content     — split into retrievable chunks, store in MongoDB
  3. embed_chunks      — compute embeddings
  4. index_chunks      — upsert vectors into Qdrant (course_chunks collection)
  5. mark_ready        — flip course status -> READY in PostgreSQL
  6. emit event        — publish `course.published` to Kafka

A partial failure retries only the failed activity; the course is never marked
ready unless all steps complete.
"""
from datetime import timedelta

from temporalio import workflow


@workflow.defn
class ContentPublishingWorkflow:
    @workflow.run
    async def run(self, course_id: str) -> None:
        retry = timedelta(seconds=5)  # placeholder; real code uses RetryPolicy in activity opts
        _ = (course_id, retry)
        # await workflow.execute_activity(extract_content, course_id, ...)
        # ... chunk -> embed -> index -> mark_ready -> emit ...
        raise NotImplementedError
