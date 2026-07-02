"""Celery app (broker = RabbitMQ, result backend = Redis).

Celery handles discrete fire-and-forget tasks that don't need workflow orchestration:
sending an individual notification email, a one-off re-index, thumbnailing, etc.
Multi-step processes that must be durable/recoverable belong in Temporal, not here.
"""
from celery import Celery

from app.core.config import settings

celery = Celery(
    "smartcourse",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=["app.tasks.notifications"],
)

celery.conf.update(
    task_acks_late=True,           # redeliver on worker crash
    task_reject_on_worker_lost=True,
    task_default_queue="smartcourse",
)
