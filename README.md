# SmartCourse

Intelligent, large-scale course delivery backend for EduCorp — course management,
event-driven operations, durable workflows, and an AI learning assistant.

> **Status (plain English):** The core platform is built and tested (72 automated
> checks). Students sign in, browse and enrol in courses, learn lesson by lesson,
> and earn certificates; instructors build and publish courses. Enrolling runs as
> a crash-proof background job, and an AI assistant answers questions about any
> lesson. Still to come: the course-publishing pipeline, the event backbone, and
> smarter AI search (all scaffolded).

## What's working

Plain-English points, good for a status update. Tech names are in light parentheses.

- **Sign in with roles** — secure login for students, instructors, and admins; each role can do only what it should. (JWT + bcrypt)
- **Build & run courses** — instructors create, edit, publish, and archive courses and lessons. Lesson content stays locked until a student enrols.
- **Learn & track progress** — students enrol (with capacity limits, prerequisites, and no double-enrolling), follow auto-suggested learning paths, tick off lessons, and earn a certificate at 100%; they can archive or leave a course.
- **Reliable enrolment** — enrolling runs as a background workflow that can't double-enrol, keeps a live count, and finishes itself even if a worker crashes mid-way. (Temporal; watch it at :8088)
- **Notifications** — email and in-app alerts on sign-up, enrolment, and completion. (Celery for email)
- **Ask-the-lesson AI** — students ask a question about a lesson and get an answer based on that lesson. (needs an AI key)
- **Health monitoring** — the app records what it's doing so slowdowns and errors are easy to find: a diary (logs), per-request timings (traces → Jaeger), and live graphs (metrics → Grafana).
- **Solid foundations** — fast database with automatic upgrades (PostgreSQL + Alembic), and a swappable AI provider (Anthropic / OpenAI / Groq).
- **Tested** — 72 automated checks covering the whole core, run with no extra setup.

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
