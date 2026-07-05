# SmartCourse

Intelligent, large-scale course delivery backend for EduCorp — course management,
event-driven operations, durable workflows, and an AI learning assistant.

> **Status:** The core platform is complete and tested (72 automated tests).
> Students sign in, enrol, work through lessons, and earn certificates;
> instructors author and publish courses. Enrolment runs as a durable,
> crash-recoverable workflow (Temporal), and an AI assistant answers
> lesson-scoped questions. Remaining Phase-2 work — the content-publishing
> pipeline, the Kafka event backbone, and RAG-based AI retrieval — is scaffolded
> on already-running infrastructure.

## What's working

Concise and outcome-focused — suitable for a status update.

- **Authentication & roles** — secure login (JWT + bcrypt) with role-based access for students, instructors, and admins.
- **Course authoring & lifecycle** — create, edit, publish, and archive courses and lessons; lesson content is gated behind enrolment (syllabus public, bodies unlock on enrol — enforced server-side).
- **Enrolment & progress** — enrolment with capacity, prerequisite, and duplicate rules; auto-generated learning paths; per-lesson completion, progress tracking, and automatic certificates at 100%; students can archive or unenrol (history retained).
- **Durable enrolment workflow** — enrolment runs on Temporal: idempotent (no double-enrolment or double-counted analytics), backpressure-tolerant, and crash-recoverable — it resumes mid-pipeline after a worker restart. (Temporal UI at :8088)
- **Notifications** — a transactional in-app feed plus best-effort email (Celery), on sign-up, enrolment, and completion.
- **AI lesson assistant** — lesson-scoped Q&A grounded in course content; provider-pluggable (Anthropic / OpenAI / Groq). RAG retrieval is the Phase-2 upgrade.
- **Observability** — structured logging, distributed request tracing (OpenTelemetry → Jaeger), and metrics (Prometheus → Grafana) for fast diagnosis.
- **Data layer** — async PostgreSQL with versioned schema migrations (Alembic).
- **Tests** — 72 automated tests covering the full synchronous domain, runnable with no external services.

## Quick start

```bash
cp .env.example .env            # set ANTHROPIC_API_KEY
make infra                      # start Postgres/Mongo/Redis/Kafka/Temporal/observability
pip install -e ".[dev]"         # local Python env (or use the api container)
make migrate                    # apply DB migrations
make api                        # http://localhost:8000/docs
```

Or run the whole thing in containers: `make up`.

## Learn the stack — inside the app

`make seed-academy` seeds a two-course learning path that teaches this project's
own stack to a frontend developer, from zero: Python, FastAPI, SQLAlchemy,
migrations, auth, Docker, Celery/RabbitMQ, and the full architecture — with
quizzes, hands-on exercises, and a capstone design assignment. Course 1
(*Backend Foundations for Frontend Developers*) is a prerequisite of course 2
(*Inside SmartCourse*), so the platform itself enforces the path. Enroll as a
student and study it in the browser.

`make seed-chess` seeds the Chess Mastery Program: a diagnostic plus the first
two modules of a coached 12-module path (positions render as real boards via
the `[fen:…]` lesson marker); later modules are generated from the student's
results.

## Testing notifications

The API only *queues* email tasks; the Celery worker executes them — run both:

```bash
make api     # terminal 1 — queues notification tasks on RabbitMQ
make celery  # terminal 2 — the worker; rendered emails print here (EMAIL_BACKEND=console)
```

Register, enroll, or complete a course and the emails appear in the worker's log;
in-app notifications appear under the bell in the frontend header. To exercise the
real SMTP path without a mail provider, run [Mailpit](https://mailpit.axllent.org)
and point the app at it:

```bash
docker run -d -p 1025:1025 -p 8025:8025 axllent/mailpit
# .env: EMAIL_BACKEND=smtp  SMTP_HOST=localhost  SMTP_PORT=1025  SMTP_USE_TLS=false
```

Sent mail shows up at http://localhost:8025.

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
