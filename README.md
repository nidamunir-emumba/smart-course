# SmartCourse

Intelligent, large-scale course delivery backend for EduCorp — course management,
event-driven operations, durable workflows, and an AI learning assistant.

> **Status:** Core platform implemented and tested. Auth, user/course/content
> management, enrollment, progress tracking, certification, and notifications
> (email + in-app) are fully working (72-test suite, in-memory SQLite — no
> Docker needed). The async/AI layer (Temporal workflows, Kafka events, RAG-grounded
> assistant) is scaffolded.

## What's working

- **Auth & access control** — JWT login/logout/me, bcrypt hashing, role-based gating (student / instructor / admin).
- **Course management** — full CRUD plus lifecycle (draft → publish → unpublish → archive → delete) with ownership and visibility rules; module/asset editing; lesson content gated behind enrollment (syllabus open, bodies unlock on enroll — enforced in the API).
- **Enrollment & progress** — enroll with duplicate/limit/prerequisite enforcement (auto-derived learning paths with a dedicated Paths page and friendly guidance); durable enrollment via Temporal when `ENROLLMENT_WORKFLOW_ENABLED` (workflow-id idempotency, Mongo analytics counters, step-level recovery — see the Temporal UI at :8088); per-lesson completion (check lessons off individually), derived progress, auto-completion and automatic certificate issuance; students can archive courses from the dashboard or catalog and unenroll (history retained, seat freed).
- **Notifications** — email (Celery: registration welcome, enrollment welcome, completion congratulations; console backend by default, SMTP via `EMAIL_BACKEND=smtp`) and an in-app feed (bell in the frontend header, unread counts, mark read) written transactionally with each event.
- **Data & migrations** — full relational model (users, courses, modules, assets, enrollments, progress, certificates) with Alembic migrations.
- **AI assistant (phase 1)** — ask questions about any lesson, answered in the browser, grounded in the course content (set ANTHROPIC_API_KEY; RAG retrieval upgrade is Phase 2).
- **Infrastructure** — async PostgreSQL, structured logging, OpenTelemetry tracing, Prometheus metrics; pluggable LLM provider (Anthropic / OpenAI / Groq).
- **Tests** — 72 tests covering the full synchronous domain end to end.

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
