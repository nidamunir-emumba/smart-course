"""Canonical Kafka topic + event-type names. Import these; never hardcode strings.

Kafka is the domain-event backbone: producers emit facts, independent consumers
react (analytics, search indexing, notifications). Decouples flows and absorbs
spikes/backpressure. Schema Registry (Avro, schemas in app/events/schemas) enforces
compatibility so producers/consumers can evolve independently.
"""

COURSE_PUBLISHED = "smartcourse.course.published"
STUDENT_ENROLLED = "smartcourse.student.enrolled"
ASSISTANT_QUERIED = "smartcourse.assistant.queried"
COURSE_COMPLETED = "smartcourse.course.completed"
