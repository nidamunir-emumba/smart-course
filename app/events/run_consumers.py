"""Kafka consumer runner. Run: `python -m app.events.run_consumers`.

Starts consumer groups that project domain events into read models:
  - analytics consumer  -> update MongoDB analytics views / Postgres counters
  - indexing consumer   -> ensure published content is searchable
  - notification consumer -> enqueue Celery notification tasks

Consumers are idempotent (dedupe on event id via Redis) so redelivery is safe.
Failed events are routed to a dead-letter topic for the 'Failed Events' metric.
"""
from app.core.logging import setup_logging


def main() -> None:
    setup_logging()
    # Build confluent_kafka.DeserializingConsumer(s), subscribe, poll loop.
    raise NotImplementedError


if __name__ == "__main__":
    main()
