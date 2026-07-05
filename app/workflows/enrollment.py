"""Enrollment Workflow (Temporal) — the durable enrollment pipeline.

Steps (each an idempotent activity in app/workflows/activities.py):
  1. record_enrollment            — enrollment + progress rows, one ACID transaction
  2. update_analytics             — Mongo counters, deduped by enrollment id
  3. send_enrollment_notifications — in-app feed row (deduped) + welcome email

Guarantees this buys over the inline path:
  - Idempotency: the workflow id is derived from (student_id, course_id), so a
    duplicate submit joins the running workflow instead of double-processing;
    every activity additionally dedupes on its own key.
  - Recovery: a crash between steps resumes AT that step, on any worker.
  - Backpressure: enrollments queue on the Temporal task queue; a burst (or a
    dead worker) delays processing instead of dropping it.

The workflow body stays import-clean for Temporal's sandbox — activities are
referenced by name and executed in the worker process, where the app (DB,
Mongo, Celery) is available.
"""
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=1),
)
_TIMEOUT = timedelta(seconds=30)


def enrollment_workflow_id(student_id: str, course_id: str) -> str:
    """Deterministic id: duplicate submits dedupe onto the same run."""
    return f"enroll-{student_id}-{course_id}"


@workflow.defn
class EnrollmentWorkflow:
    @workflow.run
    async def run(self, student_id: str, course_id: str) -> str:
        enrollment_id: str = await workflow.execute_activity(
            "record_enrollment",
            args=[student_id, course_id],
            start_to_close_timeout=_TIMEOUT,
            retry_policy=_RETRY,
        )
        await workflow.execute_activity(
            "update_analytics",
            args=[enrollment_id, course_id],
            start_to_close_timeout=_TIMEOUT,
            retry_policy=_RETRY,
        )
        await workflow.execute_activity(
            "send_enrollment_notifications",
            args=[enrollment_id],
            start_to_close_timeout=_TIMEOUT,
            retry_policy=_RETRY,
        )
        return enrollment_id
