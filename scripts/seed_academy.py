"""Seed the SmartCourse Academy: a two-course learning path that teaches this
very project's stack and architecture to a frontend developer, from zero.

Course 1 (Backend Foundations) is a prerequisite of Course 2 (Inside
SmartCourse), so the platform's own prerequisite rule enforces the learning
path. Quizzes and assignments are text lessons (the platform's lesson type);
answers sit below a divider so you can self-check.

Idempotent: re-running wipes the academy instructor's courses and recreates
them. Run inside the API container:

    make seed-academy
    # or:  docker compose exec api python -m scripts.seed_academy
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

ACADEMY_INSTRUCTOR = UserCreate(
    email="academy@smartcourse.dev",
    full_name="SmartCourse Academy",
    password="academy-demo-pw",
    role=UserRole.INSTRUCTOR,
)


def text(title: str, body: str, order: int) -> AssetCreate:
    return AssetCreate(title=title, type="text", content=body.strip(), order_index=order)


# ══════════════════════════════════════════════════════════════════════════════
# COURSE 1 · BACKEND FOUNDATIONS FOR FRONTEND DEVELOPERS
# ══════════════════════════════════════════════════════════════════════════════

C1_WHAT_IS_BACKEND = """
You already know half of this system. Every time your React code calls fetch(), something on the other end answers. This course is about that something.

Here is the deal we'll make: every new backend idea gets introduced through something you already use daily on the frontend. A backend framework is "Express, but Python." An ORM is "Prisma, but Python." Dependency injection is "React context, but for request handling." The analogies aren't perfect — we'll break them where they mislead — but they give your brain a shelf to put things on.

So, what is a backend? Strip away the jargon and it's a program that runs forever on a computer you don't see, doing three jobs:

1. Listening — it waits on a network port (this project listens on port 8000) for HTTP requests, exactly the ones your fetch() sends.
2. Deciding — it checks who you are (authentication), whether you're allowed to do the thing (authorization), and whether the request even makes sense (validation).
3. Remembering — it reads and writes a database, because unlike your React state, this data must survive page refreshes, server restarts, and years of time.

The frontend/backend split exists because the browser is enemy territory. Anyone can open DevTools, edit your JavaScript, and send any request they like. The frontend is a guest in the user's machine; the backend is the bouncer at the door of your data. That's why every rule that matters — "students can't create courses", "you can't enroll twice" — is enforced again on the server, even if the UI already prevents it. Frontend validation is a courtesy. Backend validation is the law.

The app you are reading this lesson in right now is exactly such a system: a React frontend (which you'd feel at home in) talking to a Python backend called FastAPI, which talks to a database called PostgreSQL. By the end of this path, none of those words will be mysterious.
"""

C1_LIFE_OF_REQUEST = """
Let's trace what happened when you clicked this lesson open. Somewhere in the React code, a component asked for this course. That kicked off the journey drawn below — the request travels down the left side, the response climbs back up the right:

[diagram:request-lifecycle]

Before anything else, one clarification that saves endless confusion: FastAPI and SQLAlchemy are NOT separate stations the request travels between, and Python is not a place — it is the language everything on the backend is written in. FastAPI and SQLAlchemy are two Python libraries inside ONE running program, the same way React and axios are two JavaScript libraries inside one browser tab. Between "FastAPI" and "SQLAlchemy" in the chain above there is no network and no hand-off between systems — just ordinary function calls, in the same process, in nanoseconds. The whole middle of the diagram is one Python process wearing layers.

Your own frontend works exactly like this. A click runs a React onClick handler, which calls axios, and when the response lands, React re-renders. You would never say the click "went from JavaScript to React to axios" — it is one JavaScript program, and React appears at the start AND the end only because it is the outermost layer: it kicks off the work and it presents the result. FastAPI plays that same outermost role on the backend: it unwraps the HTTP request on the way in, and wraps your function's return value into a JSON response on the way out. That is why it appears twice in the diagram — same library, entry and exit of the same onion.

So count the actual trips: browser → API process (network hop one), API process → PostgreSQL and back (network hop two), then the response home. Everything else is in-process. And "turns Python into SQL" means exactly what Prisma does in JS-land: SQLAlchemy takes the Python expression select(Course).where(Course.id == …) and generates the SQL string that actually crosses the wire to the database.

Two more things are worth pausing on.

First: the layers. The endpoint (HTTP stuff) is separate from the service (business rules), which is separate from the models (database shape). This is the backend's version of separating components from hooks from API clients. When we read this project's code later, you'll see folders that map one-to-one onto these layers: app/api, app/services, app/models.

Second: statelessness. The backend does not remember you between requests. There is no "session" object living in server memory that says "Nida is logged in." Instead, every single request carries proof of identity — a signed token in the Authorization header. Any server process that sees the request can verify the token and serve you. This is what lets backends scale horizontally: ten identical copies of the API behind a load balancer, none of which need to have met you before.

Keep this diagram in your head. Every lesson that follows zooms into one box of it.
"""

C1_QUIZ_REQUEST_PATH = """
Answer these from memory, then scroll to the bottom to check. No grades — the goal is to notice what didn't stick.

Q1. Your React form validates that an email is well-formed before submitting. Why must the backend validate it again?

Q2. Put these in the order a request touches them: PostgreSQL · React · FastAPI · SQLAlchemy.

Q3. The backend keeps no memory of who is logged in between requests. What carries the proof of identity instead, and where does it live in the request?

Q4. True or false: if the UI hides the "Create course" button from students, the backend doesn't need to check the user's role on that endpoint.

— — — — — — — — — — — — — — — — — — — —

A1. Because the browser can't be trusted: anyone can bypass your JavaScript and send a raw request (curl, Postman, DevTools). Frontend validation improves UX; backend validation protects data.

A2. React → FastAPI → SQLAlchemy → PostgreSQL. (The response returns through the same chain, reversed.)

A3. A signed token (in this project, a JWT), sent on every request in the Authorization header. The server verifies the signature instead of remembering a session.

A4. False. The button is cosmetic; the endpoint must check the role itself. In this project that check is one line: Depends(require_role(UserRole.INSTRUCTOR)) — you'll meet it in the FastAPI module.
"""

C1_PY_SYNTAX = """
Python and JavaScript are more alike than either community admits. Here's your phrasebook — JS on the left of each pair, Python on the right.

Variables: const user = {...}  →  user = {...}. No const/let/var — you just assign. Python has no hoisting and no undefined; using a name before assigning raises an error immediately.

Functions: function add(a, b) { return a + b }  →  def add(a, b): return a + b. Indentation replaces curly braces — the whitespace IS the block structure. Four spaces is the law of the land. Arrow functions have a sibling: (a) => a * 2 is lambda a: a * 2, used for the same short-callback jobs.

Strings: template literals `Hello ${name}` become f-strings f"Hello {name}". Same idea, different sigil.

Arrays and objects: [1, 2, 3] is a list, {"key": "value"} is a dict. Where you reach for map/filter, Python reaches for comprehensions: users.map(u => u.email) becomes [u.email for u in users], and .filter(u => u.active) folds into the same expression: [u.email for u in users if u.active]. Comprehensions feel odd for a week, then you never want to go back.

Loops: for (const item of items) is for item in items. Python's for is always "of", never the C-style counter.

Modules: import { thing } from './lib' is from lib import thing. No default exports — everything is named.

null: Python has one nothing-value, None (capital N). Equality: === is just ==, and for None you use is None. Truthiness works like JS: empty lists, empty strings, 0 and None are all falsy.

Two habits to unlearn: no semicolons (allowed but never written), and snake_case instead of camelCase — full_name, not fullName. You'll see this in every file of this repo: the API sends completed_asset_ids, not completedAssetIds, and the frontend types mirror that.

Read any file in this project's app/ folder now and you'll be surprised how much simply reads as pseudocode.
"""

C1_PY_TYPES = """
JavaScript has TypeScript bolted on top; Python grew the same feature from inside. They're called type hints, and this project uses them everywhere:

    def get_user(user_id: uuid.UUID) -> User: …

Read the arrow as TypeScript's colon-after-parens: this function takes a UUID and returns a User. The twist: Python doesn't enforce hints when the code runs — they're documentation plus tooling, checked by a separate program called mypy (this repo runs it via make lint), exactly like tsc checks TypeScript.

Where TS says string | null, Python says str | None. Where TS has interfaces, Python has classes — and this project leans on a library called Pydantic that will feel instantly familiar: it's zod, but Python.

    class UserCreate(BaseModel):
        email: str
        full_name: str
        password: str

That is a schema. When a request body arrives, FastAPI validates the JSON against it — wrong type, missing field, malformed email → the caller gets a 422 with a precise error, and your handler never even runs with bad data. It's z.object({...}).parse(), promoted to a first-class citizen of the framework. This repo's app/schemas folder is full of these: UserCreate, CourseCreate, EnrollmentRead. The Read/Create suffix convention tells you which direction the data flows.

One more shape to recognize: dataclass-style model definitions for database tables (you'll meet them properly in the database module):

    class User(Base):
        id: Mapped[uuid.UUID]
        email: Mapped[str]

Different library (SQLAlchemy), same instinct — describe the shape once, in one place, and let machinery derive behavior from it. If you internalize one thing from this lesson: Python backends are typed codebases now. Your TypeScript instincts transfer almost entirely.
"""

C1_PY_ASYNC = """
Here is the concept where your frontend experience gives you a real head start: async/await. You already know why it exists — you'd never freeze the browser UI waiting for a fetch. Python arrived at the same keywords for the same reason, with one difference of emphasis: on the backend, the thing you must never freeze is the server itself.

Picture the API process as a single cashier. A request comes in that needs a database read. The database takes, say, 5 milliseconds — an eternity in CPU time. A naive server would stand there, staring at the database, while other customers queue up. An async server says "await" — which really means: "this will take a while; serve someone else and wake me when it's ready."

    async def get_course(course_id):
        course = await session.get(Course, course_id)   # ← yields here
        return course

Same mental model as JS: await marks a point where the function pauses and something else runs. Python's engine for this is called the event loop (the library is asyncio) — a direct cousin of the browser's event loop you already debug around.

The differences that matter:

1. In Python you choose async. Plenty of Python code is synchronous. A function is only pausable if defined with async def, and you can only await inside one. This project chose async end to end — FastAPI endpoints, SQLAlchemy sessions, even the Postgres driver (asyncpg) — so one process can juggle many simultaneous requests.

2. Blocking is a sin with bigger consequences. In the browser, blocking freezes one user's tab. In a server, blocking the event loop freezes every request in flight. That's why, later in this path, you'll see the project push slow work (like sending email) out of the request entirely — to a separate worker process. Hold that thought; it's the whole reason Celery exists.

3. No .then() culture. Python skipped the promise-chaining era. It's async/await or nothing, which honestly makes it cleaner than a lot of JS you've read.
"""

C1_PY_TRYIT = """
Time to touch it. This project ships Python 3.10+; you have a working interpreter in the repo's virtualenv. Open a terminal in the project root.

Exercise 1 — the REPL (Python's browser console):
Run: .venv/bin/python
You'll get a >>> prompt. Try your phrasebook:
    name = "SmartCourse"
    f"Hello {name}"
    lessons = ["intro", "http", "auth"]
    [title.upper() for title in lessons]
    {"email": "you@example.com"}["email"]
Exit with exit() or Ctrl-D.

Exercise 2 — read real code, three files, five minutes each. Don't try to understand every line; just recognize shapes from the last three lessons:
• app/schemas/user.py — Pydantic schemas. Find the zod-like class. Which fields does UserCreate require?
• app/services/users.py — plain async functions. Find an async def, an await, and a type hint with a -> return arrow.
• app/api/v1/users.py — the HTTP layer. Notice how short it is: it validates input via a schema, calls a service, returns the result. Layers.

Exercise 3 — break something (in your head). In app/services/users.py, create_user hashes the password before storing. Predict: what would go wrong if it stored data.password directly? Where in this learning path do you expect the full answer? (Module 5 — Authentication.)

Checkpoint: if the three files read as "typed pseudocode with unfamiliar plumbing" — perfect. The next two modules are the plumbing.
"""

C1_QUIZ_PYTHON = """
Q1. Translate to Python: const names = users.filter(u => u.active).map(u => u.name)

Q2. What does this hint promise, and who enforces it?  def find(email: str) -> User | None

Q3. In this backend, what's the cost of calling a slow synchronous function (no await) inside an async endpoint?

Q4. Pydantic's BaseModel is closest to which frontend tool: Redux, zod, or axios? What happens when incoming JSON doesn't match?

— — — — — — — — — — — — — — — — — — — —

A1. names = [u.name for u in users if u.active]

A2. It promises find takes a string and returns either a User or None. Nothing enforces it at runtime — mypy (run via make lint) checks it statically, like tsc.

A3. It blocks the event loop: every other in-flight request stalls until it finishes. One slow call degrades the whole server, not just one user.

A4. zod. FastAPI validates the body against the schema and returns a 422 with field-level errors before your handler runs.
"""

C1_FASTAPI_ROUTES = """
FastAPI is this project's web framework — the Express. Here's a real endpoint from this repo (app/api/v1/users.py), trimmed for focus:

    @router.post("", response_model=UserRead, status_code=201)
    async def register_user(data: UserCreate, session: AsyncSession = Depends(get_session)):
        return await user_service.create_user(session, data)

Read it against Express: app.post('/users', handler) becomes the @router.post decorator (a decorator is a function that wraps a function — think higher-order component). The handler is async, like yours. Now every piece of that line, one at a time.

• The empty string "" is the path. Routers are mounted under a prefix — app/api/router.py mounts this file at prefix="/users", and everything under /api/v1 — so "" means "at my router's root": /api/v1 + /users + "" = POST /api/v1/users. It's exactly an Express sub-router: users.post('/', handler) then app.use('/api/v1/users', users). The "" plays the role of that '/'.

• status_code=201 — FastAPI's default success status is 200, but REST convention (from the HTTP lesson) says a POST that creates something returns 201 Created. Declared once in the decorator, instead of Express's res.status(201) on every response.

• data: UserCreate vs response_model=UserRead — the same resource, traveling in opposite directions, and the placement tells you which is which. Parameters (line 2) are INPUTS: UserCreate is the JSON body the client sends — email, full_name, role, password. Decorator metadata (line 1) describes the OUTPUT: UserRead is what the client gets back — id, created_at, is_active… and no password field at all. They differ on purpose: the client must SEND a password but must never RECEIVE one (even hashed — UserRead doesn't declare it, so FastAPI strips it); the client can't send an id, the server generates it. In TypeScript you'd write two interfaces — CreateUserRequest and UserResponse — never one for both. The Create/Read suffixes in this codebase are exactly that convention.

• Because data is typed as a Pydantic schema, FastAPI parses the body, validates it, and hands you a typed object. Invalid body? The caller gets a 422 and your code never runs. No req.body, no manual checks.

• session: AsyncSession = Depends(get_session) — a database connection, INJECTED into the handler. That "= Depends(...)" is not a default value; it's a marker meaning "before running this, call get_session() and pass me the result" — like a React hook giving a component the database without prop-drilling. This is dependency injection, and it's the entire subject of the next lesson — park it for now.

• Path and query parameters follow the same trick: declare course_id: uuid.UUID in the signature and FastAPI extracts it from /courses/{course_id}, converting and validating the type. A limit: int = Query(20, ge=1, le=100) gives you a validated ?limit= with defaults and bounds — this exact line paginates the notifications feed you use in this app.

The pattern to internalize: the signature IS the contract. Everything Express makes you write inside the handler body — parse, validate, status, response shaping — FastAPI reads from the declaration.

And the killer feature: because everything is typed, FastAPI generates interactive docs from your code. With the stack running, open http://localhost:8000/docs — every endpoint in this project, executable from the browser, request/response schemas included. It's Storybook for your API, for free, always in sync.
"""

C1_FASTAPI_DI = """
The strangest-looking thing in that endpoint was Depends(get_session). This is dependency injection, and it's simpler than its enterprise-y name.

The problem it solves: nearly every endpoint needs the same setup — a database session, the current user, permission checks. Express solves this with middleware that mutates req. FastAPI solves it with declared dependencies: each parameter says what it needs, and the framework provides it.

    async def enroll(
        data: EnrollmentCreate,
        user: User = Depends(require_role(UserRole.STUDENT)),
        session: AsyncSession = Depends(get_session),
    ):

Read the middle line aloud: "this endpoint needs a user, obtained by requiring the student role." Before your code runs, FastAPI calls require_role — which reads the Authorization header, verifies the JWT, loads the user from the database, and checks the role. Wrong role → 403, and your handler never executes. The parameter is the guard.

Why not middleware? Three wins:

1. Self-documenting: the function signature tells you everything this endpoint needs. No hunting through a middleware chain to learn that req.user exists.
2. Composable: get_current_user depends on the token; require_role depends on get_current_user. Dependencies nest like React hooks composing.
3. Swappable: in tests, this repo overrides get_session to hand endpoints an in-memory database instead of Postgres — one line (app.dependency_overrides), no mocking library. That's how the 46-test suite runs with no Docker.

The React analogy that lands: Depends is like a hook + context. useSession() gives any component the session without prop-drilling; Depends(get_session) gives any endpoint the database without global variables. And like hooks, dependencies are resolved fresh per request — nothing leaks between users.

Where does business logic live, then? Not in the endpoint. This project keeps endpoints thin — parse, authorize, delegate — and puts the rules (can't enroll twice, course must be published) in app/services. Endpoint = controller, service = the brain. When you read the codebase, that's the split to expect.
"""

C1_FASTAPI_TRYIT = """
The best FastAPI teacher is its own docs page. Get the stack running (from the repo root):

    make infra        # data stores in Docker
    make api          # the FastAPI process (or it may already be running in Docker)

Then open http://localhost:8000/docs in your browser.

Exercise 1 — read the map. Every endpoint of the app you're using right now is listed, grouped by tag: auth, users, courses, enrollments, notifications. Expand GET /api/v1/courses. The Parameters section (limit, offset) and the 200 response schema were all generated from type hints you can now read.

Exercise 2 — call an endpoint with no frontend. Expand POST /api/v1/auth/login → "Try it out". Body:
    {"email": "academy@smartcourse.dev", "password": "academy-demo-pw"}
Execute. You get a token back — the same JWT the React app stores after your own login.

Exercise 3 — authorize like the frontend does. Click the green Authorize button (top right), paste the access_token value, then call GET /api/v1/auth/me. That Authorization header the docs UI now attaches? It's exactly what the React client adds to every fetch (see frontend/src/api/client.ts).

Exercise 4 — trigger real validation. Call POST /api/v1/users with "email": "not-an-email". Read the 422 response carefully: field, error type, message. Nobody wrote that error handler — the UserCreate schema did.

Checkpoint: you just exercised auth, validation, and the courses API without one line of frontend code. The backend is a product of its own; the docs page is its UI.
"""

C1_QUIZ_FASTAPI = """
Q1. In Express you'd write validation middleware for the request body. What replaces it in FastAPI, and what status code does the caller get on bad input?

Q2. This project's User model contains hashed_password, yet no API response ever includes it. What mechanism guarantees that?

Q3. What does user: User = Depends(require_role(UserRole.STUDENT)) do before your endpoint body runs — and what does the caller see if they're an instructor?

Q4. In tests, endpoints talk to an in-memory SQLite database instead of Postgres. Which FastAPI feature makes that possible without a mocking library?

— — — — — — — — — — — — — — — — — — — —

A1. A Pydantic schema declared as the endpoint's parameter type (data: UserCreate). Invalid bodies get a 422 with field-level detail.

A2. response_model=UserRead — output is filtered to the response schema's declared fields, so undeclared fields are stripped.

A3. It verifies the JWT, loads the user, and checks the role — all before the handler. A non-student gets a 403 Forbidden.

A4. Dependency overrides: app.dependency_overrides[get_session] = test_session_factory. Endpoints ask for a session; tests hand them a different one.
"""

C1_DB_POSTGRES = """
Your React state dies on refresh. localStorage dies with the browser. Real products need memory that survives everything — that's the database, and this project uses PostgreSQL, the boring, beloved workhorse of the industry (in the best way: boring means predictable under pressure).

Postgres is a relational database: data lives in tables (think spreadsheets with rules), rows are records, and columns are typed fields. This project's tables mirror its nouns — users, courses, modules, assets, enrollments, progress, certificates, notifications, lesson_completions. That last one? Every checkbox you tick in this course adds a row to it.

Tables relate through keys. Every enrollment row stores a student_id and a course_id — foreign keys pointing at rows in users and courses. This is how "Nida is enrolled in Backend Foundations" is actually stored: not as a nested object, but as a row of references. Where MongoDB (which you may have met in JS-land) nests documents, relational databases normalize — store each fact once, join on demand.

Two relational superpowers justify the ceremony:

Constraints — rules the database itself enforces, as the last line of defense. A UNIQUE constraint on users.email makes duplicate accounts impossible even if the application code has a bug. This project has a beautiful example: a partial unique index on enrollments that says "one ACTIVE enrollment per (student, course) — but old cancelled ones may pile up as history." Even a race condition (two enroll requests in the same millisecond) can't create duplicates; the second one hits the constraint and fails cleanly. The service layer catches exactly that error — you'll find IntegrityError handled in app/services/enrollments.py.

Transactions — all-or-nothing groups of changes. Completing a course must update progress AND set the status AND issue a certificate. A transaction guarantees you never end up half-done (certificate issued, progress unsaved) even if the process crashes mid-way. In code it's session.commit(): everything since the last commit lands together, or nothing does.

SQL is the language for all this — SELECT, INSERT, UPDATE, JOIN. You'll rarely write it by hand here, because of what's next: the ORM.
"""

C1_DB_ORM = """
An ORM (Object-Relational Mapper) translates between Python objects and SQL rows. If you've touched Prisma, you already know the shape of this: define models, get typed queries. This project's ORM is SQLAlchemy, the standard in Python.

Models are Python classes that describe tables (from app/models/course.py, trimmed):

    class Course(Base):
        __tablename__ = "courses"
        id: Mapped[uuid.UUID]      # primary key
        title: Mapped[str]
        status: Mapped[CourseStatus]
        instructor_id: Mapped[uuid.UUID]          # FK → users.id
        modules: Mapped[list["Module"]] = relationship(...)

That relationship line is the ORM's party trick: course.modules gives you a course's modules as a Python list, and the ORM writes the JOIN. Compare Prisma's include: { modules: true }.

Queries read like sentences once you've seen a few:

    result = await session.execute(
        select(Course).where(Course.status == CourseStatus.READY).limit(20)
    )
    courses = result.scalars().all()

…which becomes SELECT * FROM courses WHERE status = 'ready' LIMIT 20. Writes go through the session: session.add(course) stages an insert; await session.commit() makes it real (there's the transaction from last lesson).

One trap deserves its own paragraph, because it shaped real code in this repo: lazy loading meets async. Classic SQLAlchemy fetches relationships on first access — touch course.modules and it quietly runs a second query. In async code, "quietly run a query" mid-property-access is not allowed. So this project declares its needs upfront: selectinload(Enrollment.progress) in the query says "fetch the progress relationship along with the enrollment, now." Look at _ENROLLMENT_LOADERS in app/services/enrollments.py — that tuple exists precisely for this.

The mental shift from REST-client thinking: the ORM session is a unit of work, not a connection pool you fire requests at. You load objects, mutate them like normal Python (progress.completed_assets = 3), and commit — the session diffs what changed and writes it. It feels closer to mutating React state and letting the framework reconcile than to hand-writing UPDATE statements.
"""

C1_DB_MIGRATIONS = """
Here's a problem the frontend never has: your code is versioned in git, but your database has exactly one copy, full of real data, and its shape must evolve without losing anything. Renaming a React prop is a refactor; renaming a database column on a live product is surgery.

Migrations are the answer: small, versioned scripts that transform the schema step by step. Each migration knows how to apply itself (upgrade) and undo itself (downgrade). The database remembers which migrations have run. New teammate? Run all of them from zero and get the exact schema. Production behind by two? It runs exactly those two.

This project uses Alembic (SQLAlchemy's migration tool). Look at migrations/versions/ — it reads as the schema's git log:

    0001_initial_schema.py        ← all eight original tables
    0002_add_user_password.py     ← auth arrived
    0003_add_notifications.py     ← the bell in your header
    0004_add_lesson_completions.py ← the checkbox you'll tick on this lesson
    0005_backfill_lesson_completions.py ← data repair for old enrollments

Each file's revision/down_revision pair chains them in order, like linked commits. Apply pending ones with: make migrate.

Two habits distinguish professionals here:

1. Migrations ride with the code that needs them. The pull request that added the notifications feature contains migration 0003 — reviewable, revertable, deployed together.

2. Migrations aren't only structure — sometimes they're data. Look at 0005: when per-lesson tracking shipped, older enrollments had a progress counter but no per-lesson rows, so completed courses displayed unchecked boxes. The fix wasn't frontend code; it was a migration that backfilled the missing rows. When stored data and code assumptions drift apart, a data migration is the honest repair.

The takeaway: schema is code. It's reviewed, versioned, and applied mechanically — never by someone typing ALTER TABLE into production at midnight.
"""

C1_QUIZ_DB = """
Q1. Two requests try to enroll the same student in the same course at the same instant. Application code checked "not already enrolled" for both (both passed — the race). What stops the duplicate, and what does the loser of the race receive?

Q2. Completing a course updates progress, flips enrollment status, and issues a certificate. What guarantees you can't end up with just the certificate after a crash?

Q3. Prisma: prisma.course.findMany({ where: { status: 'ready' } }). Write the SQLAlchemy equivalent (roughly).

Q4. Why does async SQLAlchemy require declaring selectinload(...) for relationships you'll touch, instead of lazy-loading like classic SQLAlchemy?

Q5. A teammate suggests fixing wrong rows in production with a one-off SQL script on their laptop. What's the migration-shaped objection?

— — — — — — — — — — — — — — — — — — — —

A1. The partial unique index on enrollments (unique student+course among ACTIVE rows). The second insert raises IntegrityError; the service catches it and returns a clean 409 duplicate-enrollment error.

A2. A transaction: all three changes commit together or not at all.

A3. await session.execute(select(Course).where(Course.status == CourseStatus.READY)) then .scalars().all().

A4. Lazy loading fires hidden queries on attribute access, which async sessions can't do implicitly — I/O must be awaited at explicit points. Declaring loaders fetches everything in the initial query.

A5. It's invisible history: unversioned, unreviewed, unrepeatable on other environments. Written as a migration (like 0005 in this repo), the fix is code — reviewed, ordered, and applied identically everywhere.
"""

C1_AUTH_PASSWORDS = """
Rule zero of authentication: the database must never contain a password. Not because someone might read the table today, but because you must design for the day a backup leaks or a query gets injected. The defense is storing something that proves knowledge of the password without containing it.

That something is a hash — the output of a one-way function. Same input, same output; but no path back from output to input. When you registered for this app, create_user ran your password through bcrypt and stored the result (see app/core/security.py). At login, the candidate password is hashed again and compared. The plaintext exists in memory for milliseconds and is never written anywhere.

Why bcrypt specifically, and not a general-purpose hash like SHA-256? Because SHA-256 is fast, and fast is fatal here: an attacker with a leaked table can test billions of SHA-256 guesses per second on a GPU. Password hashes are deliberately slow — bcrypt is tuned by a "cost factor" to take real milliseconds per attempt, turning a weekend cracking job into centuries. Slow for you (once per login, imperceptible) is catastrophic for the attacker (times ten billion guesses).

Bcrypt also salts automatically: it mixes a random value into every hash, so two users with the password "hunter2" get completely different stored hashes. This kills rainbow tables (precomputed hash→password dictionaries) and hides the embarrassing fact that half your users share the same twelve passwords.

Notice what this design gives up on purpose: you cannot email anyone their forgotten password, because you genuinely don't have it. "Forgot password" flows issue a reset link instead. If a service ever emails you your actual password, they're storing it — close the account.

What actually gets stored, from this repo's users table: hashed_password = "$2b$12$R9h/cIPz0gi.URNNX3kh2O…" — algorithm, cost, salt, and hash packed into one self-describing string. Even with the full table, an attacker's only move is brute force against a function built to be slow.
"""

C1_AUTH_JWT = """
Passwords answer "who are you?" once. The next problem is staying logged in for the following ten thousand requests without sending the password each time. This project's answer — the modern default for APIs — is the JWT: JSON Web Token.

After a successful login, the backend mints a token: three base64 chunks joined by dots. Decode the middle chunk and it's just JSON — the claims: {"sub": "<your user id>", "exp": <expiry timestamp>}. The third chunk is the point: a signature over the header and claims, computed with a secret key only the server knows.

Read that again, because it's the whole trick: the token is readable by anyone but forgeable by no one. The browser can decode it (it's not encrypted!), a hacker can decode it — but change one character of the claims and the signature stops matching. Only the holder of the secret key can produce a valid signature, so a token that verifies is proof the server issued it, unmodified.

The flow in this app (frontend/src/api/client.ts + app/api/deps.py):

    Login: POST /auth/login with email+password
        → server verifies bcrypt hash, signs a JWT, returns it
    React stores the token (localStorage, key "smartcourse.token")
    Every fetch adds: Authorization: Bearer <token>
    Every endpoint's get_current_user dependency:
        verify signature → check expiry → load user by id in "sub"

Notice what the server does NOT do: look the token up anywhere. Verification is pure math — no session table, no Redis lookup. That statelessness is the payoff: any API instance can verify any token, which is what makes horizontal scaling trivial. It's also the trade-off: a stolen token works until it expires, because there's no session row to delete (that's why this project's logout simply discards the token client-side, and why expiries are kept short — 24h here).

Role-based authorization stacks on top: the user row carries a role (student/instructor/admin), and endpoints declare requirements via Depends(require_role(...)). Identity from the token, permissions from the database, enforcement at the endpoint boundary — three clean layers you can now name in this codebase.
"""

C1_AUTH_ASSIGNMENT = """
Assignment: trace a login, end to end. Deliverable: a short write-up (a paragraph per step, in your notes) naming every file the login touches and what each contributes. Everything you need is in this repo — no step should be "magic happens."

Part 1 — the request. Start in frontend/src/pages/Login.tsx. Find where the form submits and which function it calls. Follow it into frontend/src/auth/AuthContext.tsx and then frontend/src/api/client.ts. Question to answer: where exactly does the token get stored after a successful login, and under what key?

Part 2 — the verification. Move to the backend: app/api/v1/auth.py, the login endpoint. Follow it into app/services/users.py (authenticate) and app/core/security.py (verify_password, create_access_token). Questions: what happens, precisely, when the email exists but the password is wrong? Same response as when the email doesn't exist at all? Why is that sameness deliberate?

Part 3 — the protected request. Now trace GET /auth/me: app/api/deps.py, get_current_user. List the four distinct failure modes that produce a 401 (missing header, malformed header, bad signature, expired token — find each in the code).

Part 4 — break it (safely). With the docs page (http://localhost:8000/docs): authorize with a valid token, then edit one character in the middle of it and call /auth/me again. Predict the exact response before you hit Execute. Then explain, in one sentence, why the server could reject it without a database lookup.

Stretch goal: sketch what adding "logout everywhere" (revoking all a user's tokens) would require, given that JWTs are stateless. There's more than one valid answer — the point is feeling the trade-off you learned in the JWT lesson.

When you're done, tick this lesson complete — and watch what the platform does when your ring hits 100%. You built up to that certificate; the next course explains the machinery that issued it.
"""

# ══════════════════════════════════════════════════════════════════════════════
# COURSE 2 · INSIDE SMARTCOURSE — HOW THIS APP ACTUALLY WORKS
# ══════════════════════════════════════════════════════════════════════════════

C2_MAP = """
You finished Foundations, which means you can read every box in this diagram. This course is about the arrows. Here is the entire system you are using right now:

[diagram:system-map]

The question this course keeps answering is: why so many pieces? A React app has one process; this thing has twenty containers. The reason is a principle you'll see restated in every module: each kind of work goes to the tool shaped for it.

The API answers requests — and does nothing slow, ever, because you learned what blocking the event loop costs. Slow-but-simple work (send an email) goes to a queue and a worker. Durable multi-step work (publish a course: extract → chunk → embed → index, where a crash mid-way must not corrupt anything) is designed for Temporal. Facts other systems might care about ("student enrolled") are designed to be broadcast on Kafka, so analytics and search can react without the API knowing they exist.

That's also why this repo can be half-built and still fully work: the synchronous core (everything you used to take this course) is complete, while the heavy async machinery is scaffolded — the sockets are wired, the appliances arrive in Phase 2. By the end of this course you'll know exactly where the seams are.
"""

C2_STORES = """
Four databases in one docker-compose. Not indecision — division of labor. The rule of this codebase (it's written in CLAUDE.md, the architecture guide): each store owns what it's best at, and PostgreSQL owns the truth.

PostgreSQL — transactional state. Users, courses, enrollments, progress, certificates, notifications, lesson completions. Everything where correctness is non-negotiable and relationships matter. If two stores ever disagree, Postgres is right. You spent a whole module on why: constraints, transactions, foreign keys.

Redis — fast, ephemeral, in-memory. Sub-millisecond reads, data you can afford to lose: cache, rate-limit counters, deduplication keys ("did I already process event abc123?"), and Celery's result backend. Think of it as the backend's useMemo — a cache in front of expensive work, never the system of record.

MongoDB — flexible documents. Designed home for parsed course content (nested module→lesson→chunk trees) and denormalized analytics read-models, where every record can be shaped differently and you fetch whole documents at once. Deliberately NOT for anything transactional — the repo's docs say never, and now you know the word for why.

Qdrant — the vector database, for the Phase-2 AI assistant. Stores embeddings (those meaning-as-numbers vectors) and answers "which course chunks are semantically closest to this student's question?" — the retrieval in Retrieval-Augmented Generation. Payload filtering by course_id keeps answers scoped to the course you're asking about.

The anti-pattern this taxonomy prevents has a name you'll hear in system-design interviews: using one tool for everything. Sessions in Postgres (too slow, wrong shape), source-of-truth in Redis (evicts under memory pressure — poof), transactions in Mongo (weak guarantees). This project's layout is an opinionated answer sheet: state → Postgres, speed → Redis, documents → Mongo, similarity → Qdrant.

One practical detail that will bite you someday, so learn it here: inside Docker, services reach each other by service name (postgres:5432, kafka:9092); from your laptop, via published ports (localhost:5432, localhost:29092). Same database, two addresses depending on where you're standing. Keep that in your pocket for the Docker module.
"""

C2_QUIZ_MAP = """
Q1. A new feature needs to remember "how many requests has this user made in the last minute?" for rate limiting. Which store, and why not Postgres?

Q2. Where does the definitive answer to "is this student enrolled?" live — and what should you say to a teammate proposing to also keep an authoritative copy in Redis for speed?

Q3. The API must respond in milliseconds, yet sending an email takes seconds. Name the two pieces (a place and a process) that let both be true.

Q4. Why can this app be fully usable while Temporal, Kafka, and Qdrant sit idle in docker-compose?

— — — — — — — — — — — — — — — — — — — —

A1. Redis — counters with expiry are its native shape, hit on every request, and losing them is harmless. Postgres would add a disk-backed write to every request for data with zero long-term value.

A2. Postgres, via the enrollments table and its constraints. A Redis copy may be a cache, never authoritative: Redis can evict or restart empty, and cache-vs-truth drift is a classic outage. One source of truth; everything else is a disposable view of it.

A3. RabbitMQ (the queue where the API drops the job in milliseconds) and the Celery worker (the separate process that picks it up and does the slow part).

A4. The synchronous core (API + Postgres + Redis) implements every feature you touch; the idle services back Phase-2 features (durable publishing pipeline, event fan-out, AI answers) that are scaffolded but not yet wired into any user-facing path.
"""

C2_DOCKER_WHAT = """
"Works on my machine" is a disease, and Docker is the vaccine. Before it, setting up this project would read: install Python 3.10 (not 3.9), Postgres 15, Redis, RabbitMQ, Kafka AND Zookeeper, Temporal, four config files, and pray your macOS doesn't fight your teammate's Ubuntu. With it: make infra.

A container is a process in a box. The box contains a frozen filesystem — OS libraries, the exact Postgres 15 binary, config — described by an image (the recipe). Containers share your machine's kernel, which is why they start in about a second and cost megabytes, where a virtual machine boots a whole OS and costs gigabytes. Closer analogy than "mini-VM": it's node_modules for infrastructure — a locked, versioned dependency tree, but for entire programs, isolated so five projects' Postgreses never collide.

The frontend parallel is exact: package.json + lockfile freeze your JS dependencies so every laptop runs identical code. An image freezes the runtime so every laptop — and production — runs identical infrastructure. "It works in the container" IS "it works," everywhere.

Isolation has a consequence you must internalize, because it explains a real bug you may have already hit: each container gets its own network namespace. Inside the Docker network, containers address each other by service name — the API reaches the database at postgres:5432. Your laptop is OUTSIDE that network; it reaches containers only through published ports — mappings like "container's 5432 is exposed on my localhost:5432."

And here's the bug: if your Mac also has a local Postgres installed (Homebrew loves doing this), localhost:5432 might be answered by YOUR Postgres, not Docker's — same port, different database, missing all the tables, cryptic "role does not exist" errors. This literally happened during this project's development; the fix was running commands inside the container (docker compose exec api …) where "postgres" can only mean one thing. Remember this lesson the first time a database mysteriously "loses" your data — you may simply be talking to the wrong one.
"""

C2_DOCKER_COMPOSE = """
One container is easy. This project needs ~20 — API, four databases, two message systems, Temporal, three workers, and an observability stack. Orchestrating that by hand (twenty docker run commands, in dependency order, on a shared network) would be absurd. docker-compose.yml is the answer: the whole topology as one declarative file. Infrastructure as code — same philosophy as React: describe the end state, let the engine make it so.

Open docker-compose.yml and it decodes with what you know:

    services:
      postgres:
        image: postgres:15          ← recipe + version, like a pinned dependency
        ports: ["5432:5432"]        ← publish to laptop (host:container)
        healthcheck: pg_isready…    ← "how do I know it's actually up?"
      api:
        build: .                    ← not a downloaded image — built from ./Dockerfile
        volumes: [".:/app"]         ← mount the repo INTO the container (live code!)
        depends_on:
          postgres: {condition: service_healthy}   ← start order, gated on health

Three lines there punch above their weight:

volumes: [".:/app"] — the container sees your working directory, live. Edit code, the container has it instantly (no rebuild) — Docker's version of Vite hot-reload. It's also why migrations you just wrote can run inside the container: the container is looking at your repo.

depends_on + healthchecks — "up" isn't "ready." Postgres accepts connections a few seconds after the process starts; the healthcheck makes the API wait for actually-ready, killing an entire genus of flaky startup crashes.

The x-app-env anchor (top of the file) — one shared block of environment variables injected into every app service, with in-network hostnames (postgres, kafka:9092). Your local .env uses localhost and host ports instead. Same settings, two vantage points — the two-addresses rule from the stores lesson, now in config form.

Daily driving, via the Makefile: make infra (just data stores + messaging — then run the API on your laptop for fast iteration), make up (everything in containers), docker compose ps (what's running), docker compose logs -f api (tail a service), make down (stop). You now hold the keys to the whole building.
"""

C2_DOCKER_TRYIT = """
Hands on the machinery. From the repo root:

Exercise 1 — census. Run: docker compose ps
Match what you see against the map from lesson one. Which services are Up? Any marked (healthy)? That column is those healthchecks reporting.

Exercise 2 — two addresses, proven. First from your laptop:
    docker compose exec postgres psql -U smartcourse -c "\\dt"
That lists every table the migrations built (spot lesson_completions — your checkboxes). The command ran psql INSIDE the postgres container via exec. Now prove the network boundary: the API container reaches this same database as host "postgres", port 5432 — find that in docker-compose.yml's x-app-env block (DATABASE_URL). Your laptop's .env says localhost. Same rows, two addresses.

Exercise 3 — watch a request from the inside. Terminal A: docker compose logs -f api. Terminal B (or the browser): load any course page in the app. Watch the access lines scroll — GET /api/v1/courses/…, your JWT-authenticated self, status 200. That's the FastAPI process you've been talking to all along.

Exercise 4 — read the recipe. Open ./Dockerfile. Even without knowing every directive you can narrate it now: start from a Python base image, copy dependency manifests, install packages, copy the app, declare the start command. It's the build script for the api service's image — the "compile step" of the backend world.

Exercise 5 — controlled destruction. Run docker compose restart api, then immediately reload the app in your browser. A beat of connection-refused, then normal. Now you know both how resilient (state was safe in Postgres, untouched) and how disposable (the process is cattle, not a pet) an API container is. That disposability is exactly the property production autoscaling relies on.
"""

C2_JOBS_WHY = """
When you registered for this platform, the API inserted your user row, wrote a welcome notification, and returned 201 — in tens of milliseconds. It did NOT send your welcome email. Sending email over SMTP takes one to several seconds, and can hang far longer when a mail server sulks. Multiply by the event-loop lesson from Foundations: seconds of blocking work in a request handler doesn't slow one user — it jams every request in flight behind it.

There's a deeper reason than speed, though: coupling. If the API sent email inline, then the day the mail provider has an outage, user registration breaks. Read that again — people couldn't sign up because email was down. The email is a side effect; it must never decide the fate of the main operation.

So the pattern (and this is among the most load-bearing patterns in backend engineering): do the essential work now, queue the rest.

[diagram:background-jobs]

This project implements exactly that split, and you can now name every part: the enqueue is one line in the endpoint (dispatch.fire(send_registration_welcome, …)); the "somewhere" the job waits is RabbitMQ; the "different process" is a Celery worker.

Notice one more subtlety in that flow, because it's a real design decision in this codebase: the in-app notification (the bell) is an INSERT in the same transaction — guaranteed, atomic, can't be lost. The email is queued — best-effort, retried, but if RabbitMQ is down the request still succeeds and only a warning is logged (see app/tasks/dispatch.py, ~20 lines, worth reading in full). Two channels for the same event, two different reliability contracts, chosen on purpose. Interview-grade insight, that.
"""

C2_JOBS_ANATOMY = """
Three roles make the machine. Learn them as roles, not brands — the brands are swappable:

The broker (RabbitMQ) — a post office for jobs. Producers drop messages in queues; the broker holds them safely (surviving restarts) until a consumer takes delivery. RabbitMQ speaks AMQP and its console at http://localhost:15672 (guest/guest) lets you literally watch queues fill and drain.

The task (Celery's unit of work) — a Python function with a decorator:

    @celery.task(bind=True, max_retries=3)
    def send_course_welcome(self, email, full_name, course_title):
        send_email(to=email, subject=f"You're enrolled: {course_title}", …)

Calling send_course_welcome.delay(args) does NOT run the function — it serializes the call into a message and hands it to the broker. (Echo of Foundations: like a coroutine, calling ≠ running.)

The worker (make celery) — a separate OS process, running the same codebase, whose whole life is: take message → run the matching function → acknowledge. Crucially it's synchronous and allowed to be slow — it can sleep, retry, talk to sulky SMTP servers all day, because no HTTP request is waiting on it. The event-loop discipline that rules the API simply doesn't apply here. That's the point.

Design details in this repo's app/tasks/ worth stealing for any system you ever build:

Plain-string payloads. Tasks receive email/name/title, not a user_id to look up — the worker never needs the async database, and the message is self-contained even if the row changes later.

Retries with acks_late. max_retries=3 with a 30-second countdown handles transient failures; acks_late means a message is only removed from the queue after the task finishes, so a worker crash mid-job = the job is redelivered, not lost.

Failure isolation. dispatch.fire() wraps .delay() in a try/except: broker down → log a warning, drop the email, return 201 anyway. The side effect is never allowed to fail the main operation.

Where's Redis in this? Celery's result backend — task return values and states get parked there. This project's tasks are fire-and-forget (nobody reads results), but the wiring's in app/tasks/celery_app.py: broker=RabbitMQ, backend=Redis. One more "right store for the job."
"""

C2_JOBS_TRYIT = """
Watch a background job live. You need three terminals (or two, if the API already runs in Docker).

Setup:
    Terminal 1: make infra   (ensure rabbitmq is among the up containers)
                make api     (skip if the api container is running)
    Terminal 2: make celery  ← the worker; keep this visible, it's the star
    Terminal 3: your commands

Exercise 1 — trigger a task the honest way. In the app (or the /docs page), register a fresh throwaway user. Snap your eyes to Terminal 2 within a second you'll see:
    Task app.tasks.notifications.send_registration_welcome[…] received
    email (console backend) to=… subject="Welcome to SmartCourse"
    …the full rendered email body…
    Task … succeeded in 0.01s
That's the whole pipeline: endpoint → dispatch.fire → RabbitMQ → worker → "sent" (the console backend logs instead of speaking real SMTP — perfect for dev, flip EMAIL_BACKEND=smtp for the real thing).

Exercise 2 — peek at the post office. Open http://localhost:15672 (guest/guest) → Queues → the smartcourse queue. Enroll in a course in the app and watch the message count blip up and instantly down: deposited by the API, withdrawn by your worker. That blip is the decoupling, visible.

Exercise 3 — prove the "essential vs side effect" contract. Stop the worker (Ctrl-C in Terminal 2). Enroll in another course. Notice: the app works perfectly — enrollment created, bell notification appears (it's transactional, remember). The email task? Parked in RabbitMQ, waiting. Now restart make celery and watch the parked task get processed immediately. Jobs delayed, never lost — and users never blocked.

Exercise 4 — read the 20 lines that encode the philosophy. Open app/tasks/dispatch.py. One function. Explain to your rubber duck why the except is deliberately silent-but-logged, and what would be wrong with letting the exception propagate to the endpoint.
"""

C2_QUIZ_JOBS = """
Q1. A code reviewer asks why registration doesn't just send the email inline — "it's only one SMTP call." Give both counter-arguments (there were two distinct ones).

Q2. In the enrollment flow, the bell notification is written in the database transaction, but the email goes through the queue. What different guarantee does each channel get, and why is the split correct?

Q3. A worker process is killed halfway through sending an email. With acks_late configured, what happens to that job? Without it?

Q4. Why do this project's tasks receive (email, name, course_title) as arguments instead of just enrollment_id?

Q5. Celery's broker here is RabbitMQ and the result backend is Redis. What does each of those two jobs actually entail?

— — — — — — — — — — — — — — — — — — — —

A1. (1) Latency/throughput: SMTP takes seconds and the async API must never block — one slow provider stalls every in-flight request. (2) Coupling/reliability: inline sending makes registration FAIL when the mail provider fails; a queued side effect can never break the essential operation.

A2. The notification INSERT is atomic with the enrollment — if you enrolled, the bell entry exists, guaranteed. The email is best-effort: queued, retried up to 3 times, but droppable (with a logged warning) if the broker is down. Correct because losing an email is annoying while losing the enrollment record is unacceptable — reliability budgets should match importance.

A3. With acks_late: the message wasn't acknowledged, so the broker redelivers it to another worker — retried, not lost. Without: it was acked at delivery, so the crash loses it silently.

A4. Self-contained messages: the synchronous worker never needs async DB access, the task can't fail on a deleted/changed row, and the message means the same thing whenever it's processed.

A5. Broker: holds and delivers task messages durably (the queue itself). Result backend: stores task states/return values for anyone who asks later — unused by these fire-and-forget tasks, but wired for when a caller needs answers back.
"""

C2_TRACE_ENROLL = """
Capstone walk-through: you click Enroll. Every file named below is real — this is the request's actual itinerary, and you have the vocabulary for all of it now.

    frontend/src/pages/CourseDetail.tsx
        useMutation fires → enrollmentsApi.enroll(course.id)
    frontend/src/api/client.ts
        POST /api/v1/enrollments  body {course_id}  + Authorization: Bearer <JWT>
    ── network boundary ──
    app/api/v1/enrollments.py — the endpoint
        Depends(require_role(STUDENT)): verify JWT → load user → check role
        then: thin controller, delegates immediately ↓
    app/services/enrollments.py — enroll(): the business brain
        1  student exists & is a student
        2  course exists & is READY (published)
        3  no duplicate ACTIVE enrollment (query — and the DB index backstops the race)
        4  enrollment_limit not exceeded
        5  prerequisites completed  ← the rule that locked THIS course until you finished Foundations
        then, in ONE transaction: enrollment row + progress row (0 of N) → commit
    back in the endpoint:
        notification_service.create(...)  → bell row (its own quick commit)
        dispatch.fire(send_course_welcome, your email, your name, course title)
            → message to RabbitMQ, fire-and-forget
        201 Created → React invalidates queries → ring renders 0%
    …meanwhile, milliseconds later, elsewhere:
        Celery worker picks up the message → renders the email → "sends" it

Total wall-clock for you: a few dozen milliseconds, most of it network.

Now the part worth a re-read: the failure modes are all designed, not accidental. Enroll twice fast (double-click)? App check might race, but the partial unique index makes Postgres reject the second insert; the service catches IntegrityError and returns a clean 409. Broker down? Warning logged, email skipped, enrollment still succeeds. Worker down? Email waits in the queue. Course not published? 409 before anything writes. Every arm of the flow has an answer to "and what if THIS fails?" — that habit of asking is most of what "backend engineering" means.

One update since this lesson was first written: with ENROLLMENT_WORKFLOW_ENABLED on (the containers' default), the itinerary above gets a durable upgrade — the endpoint still validates rules 1–5 synchronously (you get your 409 immediately), but the writes run inside a Temporal EnrollmentWorkflow on a worker process: record → analytics → notify, each step idempotent and resumable. The response becomes 202 Accepted, and the frontend polls until the enrollment appears. Same steps, same rules — now crash-proof and queued under load.

One exercise: re-read the numbered rules and find each one in app/services/enrollments.py. They're labeled 1-to-5 in the docstring. The code and this lesson are the same document in two languages.
"""

C2_TRACE_PROGRESS = """
The checkbox you're about to tick on this very lesson is a two-table design worth understanding, because it recently replaced a worse one — and the difference is instructive.

Version 1 (how this platform started): progress was a counter. completed_assets = 3 of 5. Simple — but it couldn't answer "WHICH three?" The UI couldn't show ticks next to finished lessons; "mark next complete" was the only possible button. A counter compresses information away.

Version 2 (what runs now): a lesson_completions table — one row per (enrollment, asset) you've finished, with a unique constraint so double-completing is structurally impossible. The counter still exists in progress, but it's derived: recomputed from the rows on every change. Rows are the truth; the counter is a cache of the truth.

When you tick this lesson:

    POST /enrollments/{id}/lessons/{asset_id}/complete
    app/api/v1/enrollments.py → app/services/enrollments.py complete_lesson():
        enrollment must be ACTIVE · asset must belong to this course
        INSERT lesson_completion (idempotent — the unique constraint has your back)
        recompute: completed count → percent → progress row
        if percent hits 100:
            status → COMPLETED, certificate row minted (serial CERT-…)
    and back in the endpoint, the transition (was ACTIVE, now COMPLETED) triggers:
        bell notification "Course complete" + queued congratulations email
        — fired exactly once, guarded by comparing before/after status

Details that separate junior from senior, all present in this small feature:

Idempotency. Tick twice (impatient double-click, retried request) → same end state, no error, no duplicate row. Backend endpoints should be safe to repeat; the unique constraint makes it so at the deepest layer.

Exactly-once side effects. The congrats email fires on the ACTIVE→COMPLETED transition, not on the "is completed" state — otherwise every later request would re-congratulate you.

Data migration honesty. When v2 shipped, old enrollments had counters but no rows — completed courses showed unchecked boxes. The fix was migration 0005: backfill rows from counters. When you change what "truth" means, you must repair existing truth to match.

And one product decision you experienced: once COMPLETED, checkboxes lock (the API returns 409 on un-complete). The certificate was issued; the syllabus becomes a record. State machines need to decide which transitions do NOT exist.

A related edge case, decided the same way: what if the instructor adds a lesson AFTER you finished? Answer — a completed course is an earned record, so your certificate and your 100% freeze (the denominator is not retroactively bumped); you get a soft heads-up notification, no more. An ACTIVE student, by contrast, has their denominator re-synced at republish (2/3 becomes 2/4, the percentage honestly drops) and is nudged to do the new lesson. Same event, two policies, split on "is this a record or a work-in-progress?" — see reconcile_after_content_change in app/services/enrollments.py.
"""

C2_TRACE_NOTIFS = """
One event, two channels — the notification design in this app is a compact case study in matching reliability to importance, and you've now met all its parts separately. Assembled:

Every notable event (you register, you enroll, you complete a course) produces:
    1. an in-app notification — a Postgres row, written with the event
    2. an email — a Celery task through RabbitMQ

Why not one mechanism? Because the two promises are different.

The bell must never lie. If you enrolled, the bell entry exists — full stop. So it's an INSERT alongside the enrollment: transactional, atomic, zero extra infrastructure that can fail independently. Cost: it only exists inside this app.

Email reaches you outside the app — but SMTP is slow and flaky, so it gets the full async treatment: queued, retried three times, and ultimately droppable with a logged warning rather than ever failing the main operation. Best-effort by design.

The read side (everything under the bell icon) is a small REST resource you can now read fluently — app/api/v1/notifications.py: list (paginated), unread-count, mark-one-read, mark-all-read, every route scoped to the authenticated user via the get_current_user dependency. One security nicety worth spotting: asking for someone else's notification returns 404, not 403 — the API refuses to even confirm the ID exists. Small leaks matter.

The frontend half (frontend/src/components/NotificationBell.tsx) holds a lesson about caches you'll reuse in every React app: the badge (unread count) and the panel (the list) are two separate queries with different refresh timings — the badge polls every 30 seconds, the list refetches on open. Early version: enroll → list showed the new notification but the badge lagged 30 seconds behind. Classic split-brain between two views of one truth. The fix was two-layered: mutations that create notifications invalidate the count query immediately (fix at the source), and opening the panel refetches both together (they can never disagree while you look at them). When two UI elements derive from one fact, tie their caches together — or they will eventually contradict each other in front of a user.

Trace to complete the picture: tick a lesson → watch the bell badge bump. You now know every hop: constraint-guarded INSERT → invalidated query → refetched count. No magic left in that little red dot.
"""

C2_ROADMAP = """
Three services in docker-compose still sit idle. They're not decoration — they're the Phase-2 shape of this system, and knowing WHY each was chosen rounds out your architecture literacy.

Temporal — durable workflows. AND AS OF NOW, ONE IS LIVE: enrollment runs as a real Temporal workflow (when ENROLLMENT_WORKFLOW_ENABLED is on — it is, in the containers). The endpoint validates the business rules synchronously, starts the EnrollmentWorkflow, and returns 202; a separate worker process executes three idempotent activities — record enrollment + progress (one ACID transaction), update analytics counters in Mongo (deduped by enrollment id), send the notifications. The workflow ID derives from (student_id, course_id), so duplicate submits join the same run instead of double-processing — the unique-constraint idea, lifted into the workflow layer. Kill the worker mid-flow and restart it: the workflow resumes at the step it died on. That's the whole pitch. The publishing pipeline (extract → chunk → embed → index for the AI assistant) is the remaining Temporal workflow, still scaffolded: same shape, more steps.

Kafka — the event backbone. Today, "student enrolled" is known only to the code that handled it. Phase 2 publishes such facts as events on topics (student.enrolled, course.published), and independent consumers each react: analytics updates dashboards, search reindexes, notifications fan out — none of them known to the API. It's pub/sub across services (versus RabbitMQ's here: deliver this job to one worker), and it's how systems grow new reactions to old events without touching the code that emits them. Consumers will dedupe by event ID via Redis — the exactly-once discipline you met in the completion flow, at fleet scale.

The AI assistant — phase 1 is live: the "Ask about this lesson" box under every text lesson answers questions grounded in the course outline plus the lesson you're reading (context straight from Postgres — no retrieval needed while questions are lesson-scoped). Phase 2 upgrades the grounding to RAG: course text → chunks → embeddings → Qdrant (filtered by course_id); at question time embed the question, retrieve the nearest chunks, and answer only from them. The provider abstraction (app/ai/llm.py) and the Q&A endpoint exist; retrieval.py and the agent graph are the remaining stubs.

Observability — the part already live. Every request is traced with OpenTelemetry (view waterfalls in Jaeger, localhost:16686), metrics scrape to Prometheus, dashboards in Grafana. In a system of twenty moving parts, "which hop was slow?" must be a lookup, not an interrogation.

You now know what every box in the map does, or will do. One assignment left.
"""

C2_CAPSTONE = """
Capstone assignment: design a feature like the engineers of this codebase would. No code required — the deliverable is a one-page design document. The feature:

  "Weekly digest: every Monday, each student receives one email
   summarizing their progress across all active enrollments."

Your document must answer, with justification rooted in this course:

1. Which tool runs the schedule and the work? (Consider: Celery has periodic scheduling via beat; Temporal offers durable cron workflows. Weigh: what happens if the process is down Monday 9:00? Is a missed digest re-sent or skipped? Does multi-step-ness — query, render, send, record — justify Temporal, or is this Celery-shaped?)

2. Where does the data come from? Write the shape (not syntax) of the query: which tables from this schema (enrollments, progress, courses, users, lesson_completions), what filters (active only?), what joins.

3. What's essential vs side effect? If sending fails for one student, do the other 9,999 still get theirs? Retry policy? Where do failures land so a human notices?

4. Idempotency: the job crashes after emailing half the students and restarts. How do you prevent double digests? (You have three known tools: unique constraints, Redis dedupe keys, exactly-once-on-transition logic. Pick and defend.)

5. The two-channel question: does the digest also warrant a bell notification? Apply the reliability-vs-importance framework from the notifications lesson — argue either way, but argue.

6. One observability paragraph: what metric or trace would tell you Monday's run succeeded, and what alert means it didn't?

Grade yourself against this bar: could a teammate implement your design without asking you a single clarifying question? That property — decisions made, trade-offs named, failure modes pre-answered — is the actual deliverable of a backend engineer. The code is just the transcript.

When you tick this lesson, the platform you now understand end-to-end will do its final trick for you: derive 100%, flip your enrollment's state machine, mint a certificate row, write a bell notification, and queue a congratulations email through a broker to a worker. You'll know the file, function, and reason for every single step. That's the whole assignment, passed.
"""

# ══════════════════════════════════════════════════════════════════════════════

FOUNDATIONS = CourseCreate(
    title="Backend Foundations for Frontend Developers",
    description=(
        "Python, FastAPI, databases, and auth — taught from zero through the "
        "frontend concepts you already know. Every lesson maps a new backend idea "
        "onto React/JS ground you stand on, then shows it live in this codebase. "
        "Finish this to unlock the architecture course."
    ),
    modules=[
        ModuleCreate(
            title="From the Browser to the Server",
            order_index=0,
            assets=[
                text("What a backend actually is", C1_WHAT_IS_BACKEND, 0),
                text("The life of a request", C1_LIFE_OF_REQUEST, 1),
                text("Knowledge check · the request path", C1_QUIZ_REQUEST_PATH, 2),
            ],
        ),
        ModuleCreate(
            title="Python for JavaScript Developers",
            order_index=1,
            assets=[
                text("Python syntax through JS eyes", C1_PY_SYNTAX, 0),
                text("Type hints and Pydantic (TypeScript & zod's cousins)", C1_PY_TYPES, 1),
                text("async/await — same idea, different engine", C1_PY_ASYNC, 2),
                text("Try it · your first Python session", C1_PY_TRYIT, 3),
                text("Knowledge check · Python", C1_QUIZ_PYTHON, 4),
            ],
        ),
        ModuleCreate(
            title="FastAPI — the Express You Already Know",
            order_index=2,
            assets=[
                text("Routes, schemas, and free documentation", C1_FASTAPI_ROUTES, 0),
                text("Dependency injection without the buzzwords", C1_FASTAPI_DI, 1),
                text("Try it · drive the API from its docs page", C1_FASTAPI_TRYIT, 2),
                text("Knowledge check · FastAPI", C1_QUIZ_FASTAPI, 3),
            ],
        ),
        ModuleCreate(
            title="Databases, ORMs, and Migrations",
            order_index=3,
            assets=[
                text("PostgreSQL: memory that survives", C1_DB_POSTGRES, 0),
                text("SQLAlchemy: Prisma, but Python", C1_DB_ORM, 1),
                text("Migrations: version control for your schema", C1_DB_MIGRATIONS, 2),
                text("Knowledge check · the data layer", C1_QUIZ_DB, 3),
            ],
        ),
        ModuleCreate(
            title="Authentication from First Principles",
            order_index=4,
            assets=[
                text("Passwords: store the proof, never the secret", C1_AUTH_PASSWORDS, 0),
                text("JWTs: signed identity, no server memory", C1_AUTH_JWT, 1),
                text("Assignment · trace a login end to end", C1_AUTH_ASSIGNMENT, 2),
            ],
        ),
    ],
)

ARCHITECTURE = CourseCreate(
    title="Inside SmartCourse: How This App Actually Works",
    description=(
        "The system you are using right now, explained end to end: Docker, the "
        "four databases, Celery background jobs, the notification pipeline, and "
        "the request traces behind every click — finishing with the Phase-2 "
        "roadmap (Temporal, Kafka, RAG) and a capstone design assignment. "
        "Requires Backend Foundations."
    ),
    modules=[
        ModuleCreate(
            title="The Map",
            order_index=0,
            assets=[
                text("One diagram, the whole system", C2_MAP, 0),
                text("Four databases, one rule: who owns what", C2_STORES, 1),
                text("Knowledge check · the map", C2_QUIZ_MAP, 2),
            ],
        ),
        ModuleCreate(
            title="Docker and Your Dev Environment",
            order_index=1,
            assets=[
                text("Containers, explained to a frontend developer", C2_DOCKER_WHAT, 0),
                text("docker-compose: twenty services, one file", C2_DOCKER_COMPOSE, 1),
                text("Try it · poke the machinery", C2_DOCKER_TRYIT, 2),
            ],
        ),
        ModuleCreate(
            title="Background Jobs: RabbitMQ, Celery, and Redis",
            order_index=2,
            assets=[
                text("Why the API never sends your email", C2_JOBS_WHY, 0),
                text("Broker, task, worker: the anatomy", C2_JOBS_ANATOMY, 1),
                text("Try it · watch a job travel the queue", C2_JOBS_TRYIT, 2),
                text("Knowledge check · background jobs", C2_QUIZ_JOBS, 3),
            ],
        ),
        ModuleCreate(
            title="The Request You Just Made",
            order_index=3,
            assets=[
                text("Enrolling, end to end: every file, every rule", C2_TRACE_ENROLL, 0),
                text("The checkbox: per-lesson progress by design", C2_TRACE_PROGRESS, 1),
                text("One event, two channels: the notification pipeline", C2_TRACE_NOTIFS, 2),
            ],
        ),
        ModuleCreate(
            title="The Road Ahead — and Your Capstone",
            order_index=4,
            assets=[
                text("Temporal, Kafka, and the AI assistant", C2_ROADMAP, 0),
                text("Capstone assignment · design the weekly digest", C2_CAPSTONE, 1),
            ],
        ),
    ],
)


async def main() -> None:
    async with SessionLocal() as session:
        instructor = await user_service.get_user_by_email(session, ACADEMY_INSTRUCTOR.email)
        if instructor is None:
            instructor = await user_service.create_user(session, ACADEMY_INSTRUCTOR)
            print(f"created instructor {instructor.email}")
        else:
            print(f"reusing instructor {instructor.email}")

        # Idempotent refresh: wipe this instructor's courses (cascades content).
        existing = (
            await session.execute(select(Course.id).where(Course.instructor_id == instructor.id))
        ).scalars().all()
        if existing:
            await session.execute(delete(Course).where(Course.instructor_id == instructor.id))
            await session.commit()
            print(f"removed {len(existing)} existing academy course(s)")

        # Course 1, then course 2 with course 1 as a hard prerequisite —
        # the platform itself enforces the learning path.
        foundations = await course_service.create_course(
            session, FOUNDATIONS, instructor_id=instructor.id
        )
        foundations = await course_service.publish_course(session, foundations.id, instructor)

        architecture_spec = ARCHITECTURE.model_copy(
            update={"prerequisite_ids": [foundations.id]}
        )
        architecture = await course_service.create_course(
            session, architecture_spec, instructor_id=instructor.id
        )
        architecture = await course_service.publish_course(session, architecture.id, instructor)

        for course in (foundations, architecture):
            lessons = sum(len(m.assets) for m in course.modules)
            chars = sum(len(a.content or "") for m in course.modules for a in m.assets)
            print(
                f"published '{course.title}': {len(course.modules)} modules, "
                f"{lessons} lessons, {chars:,} chars"
            )

    print("\nAcademy seeded. Enroll as any student; Foundations unlocks Architecture.")


if __name__ == "__main__":
    asyncio.run(main())
