import { Link } from 'react-router-dom'
import { useQueries, useQuery } from '@tanstack/react-query'
import { coursesApi, enrollmentsApi } from '../../api/endpoints'
import { useAuth } from '../../auth/AuthContext'
import type { Course } from '../../api/types'
import { ProgressRing } from '../../components/Progress'
import { EnrollmentStatusBadge } from '../../components/StatusBadge'
import { Spinner, ErrorState, EmptyState } from '../../components/Feedback'

export function Dashboard() {
  const { user } = useAuth()

  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', user?.id],
    queryFn: () => enrollmentsApi.forStudent(user!.id),
    enabled: !!user,
  })

  const enrollments = enrollmentsQuery.data ?? []

  // Resolve each enrolled course (titles live on the course, not the enrollment).
  const courseQueries = useQueries({
    queries: enrollments.map((e) => ({
      queryKey: ['course', e.course_id],
      queryFn: () => coursesApi.get(e.course_id),
      staleTime: 30_000,
    })),
  })
  const courseById = new Map<string, Course>()
  courseQueries.forEach((q) => q.data && courseById.set(q.data.id, q.data))

  return (
    <div className="flex flex-col gap-6">
      <div className="border-b border-line pb-6">
        <p className="eyebrow mb-2">My learning</p>
        <h1 className="font-display text-3xl font-bold text-ink">
          Welcome back, {user?.full_name.split(' ')[0]}
        </h1>
      </div>

      {enrollmentsQuery.isLoading ? (
        <Spinner label="Loading your courses…" />
      ) : enrollmentsQuery.isError ? (
        <ErrorState error={enrollmentsQuery.error} />
      ) : enrollments.length === 0 ? (
        <EmptyState title="You haven’t enrolled in anything yet">
          <Link to="/" className="font-medium text-primary hover:underline">
            Browse the catalog
          </Link>{' '}
          to find a course.
        </EmptyState>
      ) : (
        <div className="flex flex-col gap-3">
          {enrollments.map((e) => {
            const course = courseById.get(e.course_id)
            const percent = e.progress?.percent_complete ?? 0
            return (
              <div key={e.id} className="card flex items-center gap-4 p-4">
                <ProgressRing percent={percent} size={52} stroke={6} />
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <EnrollmentStatusBadge status={e.status} />
                    {e.progress && (
                      <span className="font-mono text-xs text-faint">
                        {e.progress.completed_assets}/{e.progress.total_assets} lessons
                      </span>
                    )}
                  </div>
                  <Link
                    to={`/courses/${e.course_id}`}
                    className="font-display font-semibold text-ink hover:text-primary"
                  >
                    {course?.title ?? 'Course'}
                  </Link>
                </div>
                {e.status === 'completed' && e.certificate ? (
                  <Link to={`/certificate/${e.id}`} className="btn btn-primary btn-sm">
                    Certificate
                  </Link>
                ) : (
                  <Link to={`/courses/${e.course_id}`} className="btn btn-ghost btn-sm">
                    Continue
                  </Link>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
