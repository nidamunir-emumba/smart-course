# SmartCourse

Intelligent, large-scale course delivery backend for EduCorp — course management,
event-driven operations, durable workflows, and an AI learning assistant.

> **Status:** Core platform implemented and tested. Auth, user/course/content
> management, enrollment, progress tracking, and certification are fully working
> (28-test suite, in-memory SQLite — no Docker needed). The async/AI layer
> (Temporal workflows, Kafka events, Celery tasks, RAG assistant) is scaffolded.

## What's working

- **Auth & access control** — JWT login/logout/me, bcrypt hashing, role-based gating (student / instructor / admin).
- **Course management** — full CRUD plus lifecycle (draft → publish → unpublish → archive → delete) with ownership and visibility rules; module/asset editing.
- **Enrollment & progress** — enroll with duplicate/limit/prerequisite enforcement; progress tracking with auto-completion and automatic certificate issuance.
- **Data & migrations** — full relational model (users, courses, modules, assets, enrollments, progress, certificates) with Alembic migrations.
- **Infrastructure** — async PostgreSQL, structured logging, OpenTelemetry tracing, Prometheus metrics; pluggable LLM provider (Anthropic / OpenAI / Groq).
- **Tests** — 28 tests covering the full synchronous domain end to end.

## Quick start

```bash
cp .env.example .env            # set ANTHROPIC_API_KEY
make infra                      # start Postgres/Mongo/Redis/Kafka/Temporal/observability
pip install -e ".[dev]"         # local Python env (or use the api container)
make migrate                    # apply DB migrations
make api                        # http://localhost:8000/docs
```

Or run the whole thing in containers: `make up`.

## Consoles

| Service       | URL                     | Notes                        |
|---------------|-------------------------|------------------------------|
| API docs      | http://localhost:8000/docs | Swagger UI                |
| Temporal UI   | http://localhost:8088   | workflow executions          |
| RabbitMQ      | http://localhost:15672  | guest / guest                |
| Grafana       | http://localhost:3000   | dashboards (anon enabled)    |
| Prometheus    | http://localhost:9090   | metrics                      |
| Jaeger        | http://localhost:16686  | traces                       |
| Qdrant        | http://localhost:6333/dashboard | vector store         |

## Docs

- [docs/PRD.md](./docs/PRD.md) — product requirements: use-cases, FRs/NFRs, milestones, diagrams, traceability matrix.
- [CLAUDE.md](./CLAUDE.md) — architecture and where each responsibility lives.
