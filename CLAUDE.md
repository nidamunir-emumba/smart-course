# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SmartCourse is the backend for an intelligent course delivery platform: course/user
management, event-driven operations, durable multi-step workflows, and an AI learning
assistant (RAG Q&A + instructor content generation).

**Current state: infra + scaffold.** The topology, config, and connection layers are
complete and wired. Business logic is deliberately stubbed with `raise NotImplementedError`.
When implementing a stub, follow the responsibility boundaries below — the hard
architectural decisions (which store, which async mechanism) are already encoded in where
each stub lives.

## Commands

Everything is exposed through the `Makefile` (`make help` lists targets):

- `make infra` — start data stores + messaging + observability (no app code). Start here.
- `make up` / `make down` — full stack incl. app services, build from `./Dockerfile`.
- `make api` — run FastAPI locally with reload (needs `make infra` first).
- `make worker` — Temporal worker · `make celery` — Celery worker · `make consumer` — Kafka consumers.
- `make migrate` — `alembic upgrade head` · `make revision m="msg"` — autogenerate a migration.
- `make test` — pytest · `make lint` — `ruff check` + `mypy` · `make fmt` — ruff fix + format.
- Single test: `pytest tests/test_health.py::test_health` (asyncio mode is auto; no marker needed).

Local dev needs infra containers running but the Python process on the host — so `.env`
uses host ports (Kafka `29092`, others default). Inside containers, `docker-compose.yml`
injects the in-network hostnames (Kafka `9092`, `postgres`, etc.) via the `x-app-env` anchor.

## Architecture: which tool owns what

The stack has three overlapping async mechanisms (Temporal, Kafka, Celery). Choosing the
wrong one is the most common mistake here — they are **not** interchangeable:

- **Temporal (`app/workflows/`)** — durable, multi-step processes that must not corrupt on
  partial failure. The two business-critical workflows live here:
  - `ContentPublishingWorkflow`: extract → chunk → embed → index (Qdrant) → mark READY → emit.
    A course is only marked ready if every step succeeds; failed steps retry in isolation.
  - `EnrollmentWorkflow`: record → init progress → update analytics → notify. Workflow id is
    derived from `(student_id, course_id)` for **idempotency** (duplicate submits dedupe).
  - Run by the `temporal-worker` service. Add activities and register them in `worker.py`.

- **Kafka + Schema Registry (`app/events/`)** — the domain-event backbone. Producers emit
  facts (`course.published`, `student.enrolled`, `assistant.queried`); independent consumer
  groups project them into read models (analytics, search indexing, notifications). Use it
  to **decouple** reactions from the main flow and absorb spikes. Topic/event names are
  constants in `topics.py` — never hardcode. Consumers must be idempotent (dedupe on event
  id via Redis); failures go to a dead-letter topic (feeds the "Failed Events" metric).
  Avro schemas in `app/events/schemas/` are registered with Schema Registry for compat.

- **Celery + RabbitMQ (`app/tasks/`)** — discrete fire-and-forget tasks with no orchestration
  need: send one email, one re-index, one thumbnail. If a task has multiple dependent steps
  or needs recovery guarantees, it belongs in Temporal instead.

Rule of thumb: **orchestrated & durable → Temporal; broadcast a fact → Kafka; one-shot side
effect → Celery.**

## Data stores: which store owns what

- **PostgreSQL (`app/db/postgres.py`, `app/models/`)** — source of truth. All transactional,
  strong-consistency state: users/roles, courses, modules, enrollments, progress, completions,
  certificates. SQLAlchemy 2.0 **async**. Schema changes go through Alembic (`make revision`);
  `migrations/env.py` imports `app.models` and pulls the URL from `app.core.config`, so new
  models must be importable from `app.models` for autogenerate to see them.
- **MongoDB (`app/db/mongo.py`)** — flexible content documents (parsed modules→lessons→chunks)
  and denormalized analytics read models for cheap dashboard queries. Never the source of
  truth for transactional state.
- **Qdrant (`app/db/qdrant.py`)** — vector store for RAG. Single `course_chunks` collection;
  payload carries `course_id` so retrieval filters by course. Chosen over pgvector/Pinecone
  for self-hosting + strong metadata filtering + async client.
- **Redis (`app/db/redis.py`)** — cache, rate limiting, idempotency/dedupe keys, Celery result
  backend.

## AI layer (`app/ai/`)

- `llm.py` — **provider abstraction**. Everything AI depends on `get_chat_model()`, never on a
  provider SDK directly. Default is Anthropic Claude; switch via `LLM_PROVIDER` env
  (`anthropic|openai|groq`). If you add OpenAI/Groq, add the matching `langchain-*` dep.
- `graph.py` — LangGraph agent shared by both assistant capabilities (contextual Q&A and
  instructor content generation). Long generations stream token-by-token to the API for
  incremental delivery.
- `retrieval.py` — RAG retrieval against Qdrant, filtered by `course_id`.

## Observability (`app/core/observability.py`, `docker/`)

`setup_observability(app)` (called in the app factory) instruments FastAPI + SQLAlchemy with
OpenTelemetry, exports traces via OTLP to the collector → Jaeger, and exposes `/metrics` for
Prometheus. The collector config (`docker/otel/`) fans traces to Jaeger and re-exposes metrics
for Prometheus to scrape; Grafana is auto-provisioned with both datasources. When adding new
flows, propagate spans so publishing/enrollment/assistant/background paths stay diagnosable —
this is an explicit product requirement, not optional polish.

## Conventions

- Config is centralized: import `from app.core.config import settings`. Do not read env vars
  ad hoc elsewhere.
- Keep the responsibility boundaries above intact. If a change seems to need, say, writing
  transactional state to Mongo or doing multi-step work in Celery, that's a signal it's in the
  wrong layer.
- Endpoints that trigger workflows (`courses.publish`, `enrollments`) should *start* the
  Temporal workflow and return immediately, not do the work inline.
- Default to the latest Claude models for any LLM work (`claude-sonnet-5`, `claude-opus-4-8`).
