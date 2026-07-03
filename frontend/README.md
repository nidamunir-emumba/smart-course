# SmartCourse — Frontend

A Vite + React + TypeScript SPA for the SmartCourse backend (FastAPI). Covers the
implemented API: auth, course catalog, instructor authoring + lifecycle, student enrollment,
progress, and certificates. The AI assistant is intentionally left out (backend stub).

## Stack

- **Vite 8** + **React 19** + **TypeScript**
- **React Router 7** — routing + role guards (`src/auth/RequireAuth.tsx`)
- **TanStack Query 5** — server state
- **Tailwind CSS 4** — design tokens in `src/index.css`
- **react-hook-form + zod** — forms/validation
- Typed fetch wrapper in `src/api/client.ts` (JWT bearer, 401 handling)

## Run it

The backend must be running first (from the repo root):

```bash
make infra      # postgres (+ the rest); only postgres is strictly required
make migrate    # alembic upgrade head
make api        # uvicorn on http://localhost:8000
```

Then the frontend:

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

In dev, Vite proxies `/api` → `http://localhost:8000` (see `vite.config.ts`), so calls are
same-origin. The backend also enables CORS for `localhost:5173` (`app/main.py`) for a
separately-hosted build. Set `VITE_API_BASE_URL` in `.env` to point at another API origin.

## Structure

```
src/
  api/         client.ts (fetch wrapper) · endpoints.ts (typed calls) · types.ts (mirrors backend schemas)
  auth/        AuthContext.tsx (JWT session) · RequireAuth.tsx (route guard)
  components/  AppShell · CourseCard · Progress (signature ring) · StatusBadge · Pagination · Feedback
  pages/       Catalog · CourseDetail · Login · Register
    student/   Dashboard · CertificatePage
    instructor/ MyCourses · CourseForm · CourseEditor
```

## Notes on the backend contract

- **All course/enrollment endpoints require auth** — there is no anonymous catalog; logged-out
  visitors get a sign-in landing.
- Identity comes from the JWT, not request bodies. Course creation needs the `instructor` role,
  enrollment needs `student`.
- Content editing (modules/assets) is **draft-only**; the editor locks once a course is published.
- Reaching 100% progress auto-completes the enrollment and issues a certificate.

## Build

```bash
npm run build   # tsc -b && vite build
```
