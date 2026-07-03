import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { coursesApi, courseAssetCount } from '../../api/endpoints'
import { useAuth } from '../../auth/AuthContext'
import { CourseStatusBadge } from '../../components/StatusBadge'
import { Spinner, ErrorState, EmptyState } from '../../components/Feedback'

export function MyCourses() {
  const { user } = useAuth()

  // Instructor listing returns ready courses + all of their own; narrow to own.
  const query = useQuery({
    queryKey: ['courses', 'mine'],
    queryFn: () => coursesApi.list(100, 0),
  })
  const mine = (query.data ?? []).filter((c) => c.instructor_id === user?.id)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between border-b border-line pb-6">
        <div>
          <p className="eyebrow mb-2">Instructor</p>
          <h1 className="font-display text-3xl font-bold text-ink">My courses</h1>
        </div>
        <Link to="/instructor/new" className="btn btn-primary">
          + New course
        </Link>
      </div>

      {query.isLoading ? (
        <Spinner label="Loading your courses…" />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : mine.length === 0 ? (
        <EmptyState title="You haven’t created any courses">
          Start with a draft, add modules and lessons, then publish.
        </EmptyState>
      ) : (
        <div className="flex flex-col gap-3">
          {mine.map((course) => (
            <Link
              key={course.id}
              to={`/instructor/courses/${course.id}`}
              className="card flex items-center gap-4 p-4 transition-colors hover:border-primary/40"
            >
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex items-center gap-2">
                  <CourseStatusBadge status={course.status} />
                  <span className="font-mono text-xs text-faint">
                    {course.modules.length} modules · {courseAssetCount(course)} lessons
                  </span>
                </div>
                <p className="font-display font-semibold text-ink">{course.title}</p>
              </div>
              <span className="font-mono text-xs text-primary">manage →</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
