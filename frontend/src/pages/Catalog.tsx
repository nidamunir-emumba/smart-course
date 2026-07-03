import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { coursesApi, enrollmentsApi } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { CourseCard } from '../components/CourseCard'
import { Pagination } from '../components/Pagination'
import { Spinner, ErrorState, EmptyState } from '../components/Feedback'

const LIMIT = 12

export function Catalog() {
  const { user, loading } = useAuth()
  const [offset, setOffset] = useState(0)

  const coursesQuery = useQuery({
    queryKey: ['courses', offset],
    queryFn: () => coursesApi.list(LIMIT, offset),
    enabled: !!user, // the catalog endpoint requires authentication
  })

  // The backend gates all course data behind auth — greet anonymous visitors.
  if (loading) return <Spinner label="Loading…" />
  if (!user) return <Landing />

  // Students see their own completion on each card.
  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', user?.id],
    queryFn: () => enrollmentsApi.forStudent(user!.id),
    enabled: user?.role === 'student',
  })

  const percentByCourse = new Map<string, number>()
  for (const e of enrollmentsQuery.data ?? []) {
    percentByCourse.set(e.course_id, e.progress?.percent_complete ?? 0)
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Hero: states the catalog's job and who it serves. */}
      <section className="flex flex-col gap-3 border-b border-line pb-8">
        <p className="eyebrow">Course catalog</p>
        <h1 className="max-w-2xl font-display text-4xl font-bold leading-[1.1] text-ink">
          {user?.role === 'instructor'
            ? 'Author courses worth finishing.'
            : 'Structured courses, tracked to completion.'}
        </h1>
        <p className="max-w-xl text-muted">
          {user?.role === 'instructor'
            ? 'Draft modules and lessons, then publish when the arc holds together.'
            : 'Browse published courses, enroll, and earn a certificate when you reach 100%.'}
        </p>
        {user?.role === 'instructor' && (
          <div>
            <Link to="/instructor/new" className="btn btn-primary mt-2">
              + New course
            </Link>
          </div>
        )}
      </section>

      {coursesQuery.isLoading ? (
        <Spinner label="Loading courses…" />
      ) : coursesQuery.isError ? (
        <ErrorState error={coursesQuery.error} />
      ) : coursesQuery.data && coursesQuery.data.length > 0 ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {coursesQuery.data.map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                percent={percentByCourse.get(course.id)}
              />
            ))}
          </div>
          <Pagination
            offset={offset}
            limit={LIMIT}
            count={coursesQuery.data.length}
            onChange={setOffset}
          />
        </>
      ) : (
        <EmptyState title="No courses here yet">
          {user?.role === 'instructor'
            ? 'Create your first course to get started.'
            : offset > 0
              ? 'No more courses on this page.'
              : 'Check back soon — published courses will appear here.'}
        </EmptyState>
      )}
    </div>
  )
}

function Landing() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-start gap-6 py-10">
      <p className="eyebrow">SmartCourse · learning platform</p>
      <h1 className="font-display text-5xl font-bold leading-[1.05] text-ink">
        Courses with a clear arc,
        <br />
        tracked to the certificate.
      </h1>
      <p className="max-w-xl text-lg text-muted">
        Sign in to browse the catalog, enroll, and follow each course module by module —
        or create an instructor account to publish your own.
      </p>
      <div className="flex gap-3">
        <Link to="/register" className="btn btn-primary">
          Get started
        </Link>
        <Link to="/login" className="btn btn-ghost">
          Sign in
        </Link>
      </div>
    </div>
  )
}
