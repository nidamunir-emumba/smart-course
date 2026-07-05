import { useQueries, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { coursesApi } from '../api/endpoints'
import { LearningPath } from '../components/LearningPath'
import { Spinner, ErrorState, EmptyState } from '../components/Feedback'

/** Learning paths, derived automatically from prerequisite links: every chain
 *  is shown once, rooted at its final course. Each step carries the student's
 *  own progress. */
export function Paths() {
  const coursesQuery = useQuery({
    queryKey: ['courses', 'all-for-paths'],
    queryFn: () => coursesApi.list(100, 0),
  })

  const courses = coursesQuery.data ?? []
  // A path is anchored at a "terminal" course: it has prerequisites, and no
  // other course builds on it — so each chain appears exactly once, whole.
  const isPrereqOfSomething = new Set(courses.flatMap((c) => c.prerequisite_ids))
  const terminals = courses.filter(
    (c) => c.prerequisite_ids.length > 0 && !isPrereqOfSomething.has(c.id)
  )

  const pathQueries = useQueries({
    queries: terminals.map((c) => ({
      queryKey: ['course-path', c.id],
      queryFn: () => coursesApi.path(c.id),
    })),
  })
  const loading = coursesQuery.isLoading || pathQueries.some((q) => q.isLoading)

  if (coursesQuery.isError) return <ErrorState error={coursesQuery.error} />

  return (
    <div className="flex flex-col gap-8">
      <section className="reveal flex flex-col gap-3 border-b border-line pb-8">
        <p className="eyebrow">Learning paths</p>
        <h1 className="max-w-2xl font-display text-4xl font-bold leading-[1.1] text-ink">
          Courses that build on each other.
        </h1>
        <p className="max-w-xl text-muted">
          Each path is a sequence: finish a course to unlock the next. Your progress is
          marked on every step.
        </p>
      </section>

      {loading ? (
        <Spinner label="Loading paths…" />
      ) : terminals.length === 0 ? (
        <EmptyState title="No learning paths yet">
          Paths appear automatically when a course lists another as its prerequisite.{' '}
          <Link to="/" className="font-medium text-primary hover:underline">
            Browse the catalog
          </Link>{' '}
          in the meantime.
        </EmptyState>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {terminals.map((course, i) => {
            const steps = pathQueries[i]?.data
            if (!steps || steps.length < 2) return null
            const done = steps.filter((s) => s.met).length
            return (
              <div key={course.id} className="card reveal flex flex-col gap-3 p-5">
                <div className="flex items-center justify-between">
                  <h2 className="font-display text-lg font-semibold leading-tight text-ink">
                    Path to {course.title}
                  </h2>
                  <span className="font-mono text-xs text-faint">
                    {done}/{steps.length} done
                  </span>
                </div>
                <LearningPath steps={steps} linkTarget />
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
