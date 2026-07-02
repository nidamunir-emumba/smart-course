"""Enrollment Workflow (Temporal). STUB.

Steps (idempotent activities):
  1. record_enrollment   — insert enrollment row (unique constraint enforces no dup)
  2. init_progress       — create progress tracking rows
  3. update_analytics    — increment analytics counters (idempotency key = enrollment id)
  4. send_notification   — enqueue a Celery task / emit `student.enrolled` to Kafka

Idempotency: the workflow id is derived from (student_id, course_id) so a duplicate
enrollment submit reuses the same workflow run instead of double-processing.
"""
from temporalio import workflow


@workflow.defn
class EnrollmentWorkflow:
    @workflow.run
    async def run(self, student_id: str, course_id: str) -> None:
        _ = (student_id, course_id)
        raise NotImplementedError
