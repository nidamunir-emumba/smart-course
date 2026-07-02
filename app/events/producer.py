"""Avro producer against Kafka + Schema Registry. STUB.

Usage: `publish(COURSE_PUBLISHED, {...})`. Values are Avro-serialized with schemas
registered in Schema Registry; keys are entity ids so per-entity ordering holds.
"""
from app.core.config import settings


def publish(topic: str, value: dict, key: str | None = None) -> None:
    _ = (topic, value, key, settings.kafka_bootstrap_servers, settings.schema_registry_url)
    # confluent_kafka.SerializingProducer with AvroSerializer(schema_registry_client)
    raise NotImplementedError
