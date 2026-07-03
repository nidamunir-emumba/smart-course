"""Central typed configuration. All services import `settings` from here."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    log_level: str = "INFO"

    # Data stores
    database_url: str = "postgresql+asyncpg://smartcourse:smartcourse@localhost:5432/smartcourse"
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "smartcourse"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    # Messaging / streaming
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672//"
    kafka_bootstrap_servers: str = "localhost:29092"
    schema_registry_url: str = "http://localhost:8081"

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "smartcourse"

    # Auth (JWT)
    # Dev default only (>=32 bytes for HS256). Override via JWT_SECRET_KEY in prod.
    jwt_secret_key: str = "dev-secret-change-me-in-production-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # AI / LLM
    llm_provider: str = "anthropic"  # anthropic | openai | groq
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    openai_api_key: str = ""
    groq_api_key: str = ""

    # Observability
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "smartcourse-api"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
