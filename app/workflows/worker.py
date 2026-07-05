"""Temporal worker process. Run: `python -m app.workflows.worker`.

Registers durable workflows + their activities and polls the task queue. Temporal
gives us automatic retries, durable timers, and crash-safe replay so multi-step
processes survive worker restarts (Requirements: publishing/enrollment must recover
from partial failures without corrupting state).
"""
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config import settings
from app.core.logging import setup_logging
from app.workflows.activities import ENROLLMENT_ACTIVITIES
from app.workflows.enrollment import EnrollmentWorkflow
from app.workflows.publishing import ContentPublishingWorkflow


async def main() -> None:
    setup_logging()
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ContentPublishingWorkflow, EnrollmentWorkflow],
        activities=ENROLLMENT_ACTIVITIES,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
