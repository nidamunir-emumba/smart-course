"""Fire-and-forget dispatch of Celery tasks from request handlers.

Notifications are a side effect, never part of the request contract: if the
broker is unreachable (local dev without RabbitMQ, tests, an outage) the
request must still succeed. Failures are logged and dropped — anything that
needs delivery guarantees belongs in Temporal, not here.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


def fire(task: Any, *args: Any) -> None:
    """Queue `task.delay(*args)`, swallowing (but logging) broker errors."""
    try:
        task.delay(*args)
    except Exception:
        logger.warning(
            "notification dropped: could not queue %s (broker unavailable?)",
            getattr(task, "name", repr(task)),
            exc_info=True,
        )
