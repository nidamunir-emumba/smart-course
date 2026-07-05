"""Seed the database with demo courses that have real, long-form lesson content.

Idempotent: re-running deletes the seed instructor's existing courses (cascading
their modules/assets/enrollments) and recreates them, so lesson content refreshes.

Run inside the API container (the repo is bind-mounted at /app):

    make seed
    # or:  docker compose exec api python scripts/seed.py
"""
import asyncio

from sqlalchemy import delete, select

from app.db.postgres import SessionLocal
from app.models.course import Course
from app.models.enums import UserRole
from app.schemas.course import AssetCreate, CourseCreate, ModuleCreate
from app.schemas.user import UserCreate
from app.services import courses as course_service
from app.services import users as user_service

SEED_INSTRUCTOR = UserCreate(
    email="instructor@smartcourse.dev",
    full_name="Dr. Maya Okonkwo",
    password="instructor-demo-pw",
    role=UserRole.INSTRUCTOR,
)


def text(title: str, body: str, order: int) -> AssetCreate:
    # Lesson bodies are dedented and stripped so indentation in this file
    # doesn't leak into the stored content.
    return AssetCreate(title=title, type="text", content=body.strip(), order_index=order)


# ── Lesson bodies ─────────────────────────────────────────────────────────────
ASYNC_WHAT = """
Concurrency is not parallelism. That single sentence, borrowed from Rob Pike, is
the mental model this whole course is built on. Parallelism is doing many things
at literally the same instant, usually across multiple CPU cores. Concurrency is
structuring a program so that many tasks can be *in progress* at once, making
progress by taking turns. Python's `asyncio` is a concurrency tool, not a
parallelism tool — it lets a single thread juggle thousands of tasks that spend
most of their time waiting.

Why does that matter? Because most real programs are not CPU-bound; they are
I/O-bound. A web scraper waits on the network. An API server waits on the
database. A chat backend waits on sockets. During every one of those waits, the
CPU sits idle. Threads are one way to fill that idle time, but each OS thread
carries a real memory cost and every context switch goes through the kernel. At a
few thousand connections that overhead dominates.

`asyncio` takes a different approach. A single event loop runs on one thread and
keeps a queue of ready-to-run tasks. When a task hits an `await` on something that
isn't ready yet — bytes from a socket, a row from Postgres — it *yields control
back to the loop* instead of blocking. The loop immediately picks the next ready
task. When the awaited result arrives, the original task is rescheduled and
resumes exactly where it left off. No kernel threads, no locks around shared
memory, just cooperative hand-offs at well-defined suspension points.

The catch, and it is the single most common beginner mistake, is the word
*cooperative*. A task only yields at an `await`. If you call a slow, blocking
function that never awaits — a synchronous `requests.get`, a tight numeric loop, a
`time.sleep` — you freeze the entire loop and every other task stalls behind it.
Async is a contract: in exchange for cheap concurrency, you promise never to block
the thread. Keep that promise and a single Python process comfortably handles tens
of thousands of concurrent connections.
"""

ASYNC_COROUTINES = """
A coroutine is a function you define with `async def`. Calling it does **not** run
it — it returns a coroutine object, a paused computation waiting to be driven.
This trips up nearly everyone at first: `result = fetch()` gives you a coroutine,
not a result. You get the value only by awaiting it: `result = await fetch()`.

`await` does two things at once. It drives the awaited coroutine to completion, and
— crucially — it marks a point where the current coroutine is willing to be
suspended so the event loop can run something else. You can only `await` inside an
`async def`; that's the language enforcing the contract that suspension points are
explicit and visible in the code.

To run several coroutines concurrently you do not just await them one after
another — that's sequential, each finishing before the next starts. Instead you
schedule them as Tasks. `asyncio.create_task(coro)` hands a coroutine to the loop
to run in the background and returns a handle you can await later. The idiomatic
pattern is `asyncio.gather(*coros)`, which schedules them all and waits for the
whole set:

    async def main():
        results = await asyncio.gather(
            fetch("/a"), fetch("/b"), fetch("/c"),
        )

If each fetch waits one second on the network, the sequential version takes three
seconds and the gathered version takes one — the three waits overlap. That overlap,
not raw speed, is the entire point of async I/O.

Modern code increasingly reaches for `asyncio.TaskGroup` (Python 3.11+) instead of
bare `gather`, because a TaskGroup gives you *structured concurrency*: if any child
task raises, the group cancels its siblings and propagates the error, so you never
leak orphaned tasks. Prefer it for anything beyond a throwaway script.
"""

ASYNC_LOOP = """
The event loop is the engine, and understanding its cycle removes almost all of
async's apparent mystery. Conceptually the loop runs forever doing four things:
pop the next ready task, run it until it awaits or finishes, register any I/O it is
now waiting on, and then ask the operating system which I/O has completed so the
corresponding tasks can be marked ready again.

That last step is where the efficiency comes from. The loop uses a single OS-level
readiness call — `epoll` on Linux, `kqueue` on macOS, IOCP on Windows — to ask
about *thousands* of sockets in one syscall: "which of these are ready to read or
write?" This is why one thread can supervise an enormous number of connections. It
never polls each socket individually; it hands the whole set to the kernel and gets
back only the ones that changed.

You almost never touch the loop directly. `asyncio.run(main())` creates a loop,
runs your top-level coroutine until it completes, and then shuts the loop down
cleanly. It is the single blessed entry point and should appear roughly once in a
program, at the very top. Reaching for lower-level calls like
`get_event_loop().run_until_complete()` in application code is a code smell left
over from older tutorials.

Two rules keep you out of trouble. First, never block the loop: offload CPU-heavy
or unavoidably-synchronous work with `await asyncio.to_thread(func, *args)`, which
runs it on a worker thread and lets the loop keep going. Second, always have a
timeout on anything touching the network: wrap awaits in `asyncio.timeout(5)` so a
hung peer can't pin a task forever. Master those two habits and you have mastered
the practical 90 percent of asyncio.
"""

RAG_WHAT = """
Retrieval-Augmented Generation, or RAG, is the dominant pattern for making a
language model answer questions about *your* data — documents, a codebase, a
knowledge base — without retraining it. The insight is simple: instead of hoping
the answer is baked into the model's weights, you fetch the relevant passages at
question time and hand them to the model as context, then ask it to answer using
only what you provided.

This solves two problems that plague naive chatbots. The first is staleness: a
model's knowledge is frozen at its training cutoff, but a retrieval step reads
whatever is in your store *right now*. The second is hallucination: when you ground
the model in specific, quoted source text and instruct it to answer only from that
text, it has far less room to invent. You can even return citations, so a human can
verify every claim against the passage it came from.

A RAG system has two phases. Offline, you *ingest*: split your documents into
chunks, convert each chunk into an embedding vector, and store those vectors in a
database that supports fast similarity search. Online, you *retrieve and generate*:
embed the user's question with the same model, find the handful of chunks whose
vectors sit closest to it, stuff those chunks into a prompt, and let the LLM
compose an answer.

Everything that separates a toy RAG demo from a production system lives in the
details of those steps — how you chunk, which embedding model you choose, how many
results you retrieve, how you filter by metadata, and how you write the final
prompt. The rest of this course walks through each of those decisions with the
trade-offs that actually move answer quality.
"""

RAG_EMBED = """
An embedding is a list of numbers — typically a few hundred to a few thousand of
them — that represents the *meaning* of a piece of text as a point in
high-dimensional space. The defining property is that texts with similar meaning
land near each other, even when they share no words. "How do I reset my password?"
and "I forgot my login credentials" are far apart by keyword overlap but very close
as embeddings. That semantic closeness is exactly what keyword search misses and
what makes retrieval feel intelligent.

Closeness is measured with cosine similarity: the cosine of the angle between two
vectors, ranging from -1 (opposite) to 1 (identical direction). Retrieval ranks
every stored chunk by cosine similarity to the query embedding and returns the top
few. Because comparing a query against millions of vectors one by one would be too
slow, vector databases build an approximate-nearest-neighbor index (HNSW is the
common choice) that trades a sliver of accuracy for enormous speed.

Two practical rules govern embeddings. First, you must use the *same* model to
embed your documents and your queries — vectors from different models live in
incompatible spaces and their distances are meaningless. Second, chunk size is a
genuine trade-off you have to tune. Chunks that are too large dilute the signal:
one relevant sentence gets averaged together with paragraphs of unrelated text, and
the embedding drifts. Chunks that are too small lose the surrounding context needed
to be understood at all.

A reliable starting point is chunks of roughly 200 to 500 tokens with a small
overlap — say 50 tokens — between neighbors, so a sentence stranded at a boundary
still appears whole in one chunk. Split on natural structure (headings,
paragraphs) rather than a blind character count whenever the document's format
lets you, because coherent chunks embed far better than arbitrary slices.
"""

RAG_PROMPT = """
Retrieval gets the right text in front of the model; the prompt decides what the
model does with it. A strong RAG prompt has three parts: an instruction that sets
the rules, the retrieved context clearly delimited, and the user's question. The
instruction is where you earn trustworthiness. Spell out that the model must answer
using only the provided context, and that if the answer is not present it should
say so rather than guess.

A serviceable template looks like this:

    You are a support assistant. Answer the question using ONLY the context
    below. If the context does not contain the answer, say "I don't know based
    on the available documents." Cite the source of each fact in brackets.

    Context:
    {retrieved_chunks}

    Question: {user_question}

Two failure modes dominate in practice. The first is the model ignoring the context
and answering from its own prior knowledge — usually because the instruction was
too weak or the context was buried. Put the rule up front and the context in an
obvious block. The second is the model answering from *stale* context because your
ingestion never re-ran after the source changed; retrieval quality is capped by how
fresh and well-chunked your store is, so treat ingestion as a first-class,
repeatable pipeline rather than a one-off script.

Finally, resist the urge to cram fifty chunks into the prompt "just in case." More
context is not more accuracy — irrelevant passages actively distract the model and
push the real answer toward the middle of a long prompt, where models attend to it
least. Retrieve a focused handful, order the strongest matches first, and let the
instruction do the rest.
"""

APIS_HTTP = """
Every web API conversation is a request and a response, and almost all of them ride
on HTTP. A request names a method (the verb), a path (the noun), some headers
(metadata), and often a body (the payload). The response carries a status code, its
own headers, and usually a body. Internalize that shape and the rest of API design
is vocabulary.

The methods carry meaning you are expected to honor. GET reads and must never
change server state — it should be safe to repeat and safe to cache. POST creates
or triggers an action. PUT replaces a resource wholesale; PATCH updates part of it.
DELETE removes it. Honoring these conventions is not pedantry: proxies, browsers,
and client libraries make caching and retry decisions based on them, so a GET with
side effects will eventually corrupt data when something replays it.

Status codes are the response's headline and they cluster into ranges. 2xx means
success — 200 OK for a normal read, 201 Created when a POST made something new, 204
No Content when there's nothing to return. 4xx means the caller made a mistake: 400
for a malformed request, 401 when you are not authenticated, 403 when you are
authenticated but not allowed, 404 when the resource doesn't exist, 409 for a
conflict with the current state. 5xx means the server broke, and the distinction
matters because a well-behaved client retries 5xx and idempotent requests but never
blindly retries a 4xx — the request itself is wrong and retrying only wastes both
sides' time.

The single most useful habit you can build is designing your error responses as
deliberately as your success responses. A 400 or 409 should carry a body that says,
in plain language, what was wrong and how to fix it. The APIs developers love are
the ones whose error messages let them solve the problem without opening a support
ticket.
"""

APIS_REST = """
REST is a set of conventions for organizing an HTTP API around *resources* —
nouns — rather than actions. Instead of endpoints like `/createUser` and
`/getUserById`, you expose a `users` collection and act on it with the HTTP verbs:
`POST /users` to create, `GET /users` to list, `GET /users/{id}` to read, `PATCH
/users/{id}` to update, `DELETE /users/{id}` to remove. The verb carries the
action so the URL can stay a stable name for the thing.

Good resource design keeps URLs hierarchical and predictable. A student's
enrollments live at `GET /students/{id}/enrollments`; a course's modules at
`GET /courses/{id}/modules`. The nesting mirrors the data model, so a developer who
has seen one part of your API can guess the rest. Consistency here is worth more
than cleverness — an API that is boringly predictable is an API people integrate
quickly.

Collections need three features before they are production-ready. Pagination, so
`GET /courses` returns a bounded page (via `limit` and `offset`, or a cursor)
instead of ten thousand rows. Filtering, so callers can ask for
`GET /courses?status=ready` rather than downloading everything and sifting locally.
And stable ordering, so pages don't shuffle between requests. Skip these and the
first large customer will take your endpoint down simply by using it.

Two cross-cutting concerns finish the picture. Versioning — prefixing routes with
`/api/v1` — lets you evolve without breaking existing clients the day you ship a
change. And authentication, typically a bearer token in the `Authorization` header,
identifies the caller so the server can decide what they're allowed to see and do.
Layer those on a clean, resource-oriented core and you have an API that can grow for
years without a rewrite.
"""


COURSES = [
    CourseCreate(
        title="Async Python from the Ground Up",
        description=(
            "Build an accurate mental model of concurrency, coroutines, and the "
            "asyncio event loop — then use it to write programs that handle "
            "thousands of connections on a single thread."
        ),
        modules=[
            ModuleCreate(
                title="Foundations of Concurrency",
                order_index=0,
                assets=[
                    text("What async really solves", ASYNC_WHAT, 0),
                    text("Coroutines, tasks, and gather", ASYNC_COROUTINES, 1),
                    AssetCreate(
                        title="Watch: the event loop visualized",
                        type="video",
                        url="https://example.com/videos/asyncio-event-loop",
                        order_index=2,
                    ),
                ],
            ),
            ModuleCreate(
                title="The Event Loop in Depth",
                order_index=1,
                assets=[
                    text("How the loop schedules work", ASYNC_LOOP, 0),
                    AssetCreate(
                        title="Reference: asyncio docs",
                        type="link",
                        url="https://docs.python.org/3/library/asyncio.html",
                        order_index=1,
                    ),
                ],
            ),
        ],
    ),
    CourseCreate(
        title="Retrieval-Augmented Generation in Practice",
        description=(
            "Ground a language model in your own documents. Chunking, embeddings, "
            "vector search, and the prompt patterns that keep answers accurate and "
            "citable."
        ),
        modules=[
            ModuleCreate(
                title="Why RAG",
                order_index=0,
                assets=[text("The RAG pattern, end to end", RAG_WHAT, 0)],
            ),
            ModuleCreate(
                title="Embeddings and Retrieval",
                order_index=1,
                assets=[
                    text("Embeddings and similarity search", RAG_EMBED, 0),
                    text("Writing the generation prompt", RAG_PROMPT, 1),
                    AssetCreate(
                        title="Watch: chunking strategies compared",
                        type="video",
                        url="https://example.com/videos/rag-chunking",
                        order_index=2,
                    ),
                ],
            ),
        ],
    ),
    CourseCreate(
        title="Designing Web APIs That Last",
        description=(
            "HTTP, REST conventions, status codes, pagination, and versioning — the "
            "durable fundamentals behind APIs that developers actually enjoy using."
        ),
        modules=[
            ModuleCreate(
                title="HTTP Fundamentals",
                order_index=0,
                assets=[text("Requests, methods, and status codes", APIS_HTTP, 0)],
            ),
            ModuleCreate(
                title="RESTful Resource Design",
                order_index=1,
                assets=[
                    text("Resources, nesting, and collections", APIS_REST, 0),
                    AssetCreate(
                        title="Reference: HTTP status code registry",
                        type="link",
                        url="https://developer.mozilla.org/docs/Web/HTTP/Status",
                        order_index=1,
                    ),
                ],
            ),
        ],
    ),
]


async def main() -> None:
    async with SessionLocal() as session:
        # Idempotent instructor.
        instructor = await user_service.get_user_by_email(session, SEED_INSTRUCTOR.email)
        if instructor is None:
            instructor = await user_service.create_user(session, SEED_INSTRUCTOR)
            print(f"created instructor {instructor.email}")
        else:
            print(f"reusing instructor {instructor.email}")

        # Wipe this instructor's existing courses so content refreshes on re-run
        # (FK ondelete=CASCADE removes their modules, assets, and enrollments).
        existing = (
            await session.execute(select(Course.id).where(Course.instructor_id == instructor.id))
        ).scalars().all()
        if existing:
            await session.execute(delete(Course).where(Course.instructor_id == instructor.id))
            await session.commit()
            print(f"removed {len(existing)} existing seed course(s)")

        for spec in COURSES:
            course = await course_service.create_course(session, spec, instructor_id=instructor.id)
            course = await course_service.publish_course(session, course.id, instructor)
            lessons = sum(len(m.assets) for m in course.modules)
            chars = sum(len(a.content or "") for m in course.modules for a in m.assets)
            print(
                f"published '{course.title}': {len(course.modules)} modules, "
                f"{lessons} lessons, {chars} chars of content"
            )

    print("\nSeed complete. Instructor login:")
    print(f"  email:    {SEED_INSTRUCTOR.email}")
    print(f"  password: {SEED_INSTRUCTOR.password}")


if __name__ == "__main__":
    asyncio.run(main())
