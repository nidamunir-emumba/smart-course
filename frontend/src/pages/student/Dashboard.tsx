import { Link } from 'react-router-dom'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { coursesApi, enrollmentsApi } from '../../api/endpoints'
import { useAuth } from '../../auth/AuthContext'
import type { Course, Enrollment } from '../../api/types'
import { ProgressRing } from '../../components/Progress'
import { EnrollmentStatusBadge } from '../../components/StatusBadge'
import { Spinner, ErrorState, EmptyState } from '../../components/Feedback'

export function Dashboard() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', user?.id],
    queryFn: () => enrollmentsApi.forStudent(user!.id),
    enabled: !!user,
  })

  // Cancelled rows are history — they live in the database, not the dashboard.
  const enrollments = (enrollmentsQuery.data ?? []).filter((e) => e.status !== 'cancelled')
  const shelf = enrollments.filter((e) => e.archived_at !== null)
  const current = enrollments.filter((e) => e.archived_at === null)

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

  const archiveMutation = useMutation({
    mutationFn: ({ id, archived }: { id: string; archived: boolean }) =>
      archived ? enrollmentsApi.unarchive(id) : enrollmentsApi.archive(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['enrollments', user?.id] }),
  })

  const active = current.filter((e) => e.status === 'active').length
  const completed = enrollments.filter((e) => e.status === 'completed').length
  const certificates = enrollments.filter((e) => e.certificate).length

  return (
    <div className="flex flex-col gap-6">
      <div className="reveal flex flex-col gap-5 border-b border-line pb-6">
        <div>
          <p className="eyebrow mb-2">My learning</p>
          <h1 className="font-display text-3xl font-bold text-ink">
            Welcome back, {user?.full_name.split(' ')[0]}
          </h1>
        </div>
        {enrollments.length > 0 && (
          <dl className="flex flex-wrap gap-3">
            <Stat label="In progress" value={active} />
            <Stat label="Completed" value={completed} />
            <Stat label="Certificates" value={certificates} accent />
          </dl>
        )}
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
        <>
          {current.length === 0 ? (
            <EmptyState title="Everything is archived">
              Unarchive a course below, or{' '}
              <Link to="/" className="font-medium text-primary hover:underline">
                find a new one
              </Link>
              .
            </EmptyState>
          ) : (
            <div className="flex flex-col gap-3">
              {current.map((e, i) => (
                <EnrollmentRow
                  key={e.id}
                  enrollment={e}
                  course={courseById.get(e.course_id)}
                  index={i}
                  onToggleArchive={() =>
                    archiveMutation.mutate({ id: e.id, archived: false })
                  }
                  archivePending={archiveMutation.isPending}
                />
              ))}
            </div>
          )}

          {/* The shelf: archived courses, out of the way but never lost. */}
          {shelf.length > 0 && (
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center gap-2 py-1">
                <span className="eyebrow">
                  Archived · {shelf.length}
                </span>
                <span className="font-mono text-xs text-faint transition-transform group-open:rotate-90">
                  ›
                </span>
              </summary>
              <div className="mt-3 flex flex-col gap-3">
                {shelf.map((e, i) => (
                  <EnrollmentRow
                    key={e.id}
                    enrollment={e}
                    course={courseById.get(e.course_id)}
                    index={i}
                    archived
                    onToggleArchive={() =>
                      archiveMutation.mutate({ id: e.id, archived: true })
                    }
                    archivePending={archiveMutation.isPending}
                  />
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  )
}

interface RowProps {
  enrollment: Enrollment
  course?: Course
  index: number
  archived?: boolean
  onToggleArchive: () => void
  archivePending: boolean
}

function EnrollmentRow({
  enrollment: e,
  course,
  index,
  archived = false,
  onToggleArchive,
  archivePending,
}: RowProps) {
  const percent = e.progress?.percent_complete ?? 0
  return (
    <div
      className={`card reveal flex items-center gap-4 p-4 ${archived ? 'opacity-75' : ''}`}
      style={{ animationDelay: `${Math.min(index, 8) * 0.05}s` }}
    >
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

      <button
        className="btn btn-ghost btn-sm"
        disabled={archivePending}
        onClick={onToggleArchive}
        title={archived ? 'Bring back to my learning' : 'Move out of the way — progress is kept'}
      >
        {archived ? 'Unarchive' : 'Archive'}
      </button>
      {e.status === 'completed' && e.certificate ? (
        <Link to={`/certificate/${e.id}`} className="btn btn-primary btn-sm">
          Certificate
        </Link>
      ) : (
        !archived && (
          <Link to={`/courses/${e.course_id}`} className="btn btn-ghost btn-sm">
            Continue
          </Link>
        )
      )}
    </div>
  )
}

// Small drafting-style plate: a measured count with its label underneath.
function Stat({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className="card flex min-w-[7rem] flex-col gap-0.5 px-4 py-3">
      <span
        className="font-display text-2xl font-bold leading-none"
        style={{ color: accent && value > 0 ? 'var(--color-accent)' : 'var(--color-ink)' }}
      >
        {value}
      </span>
      <span className="eyebrow">{label}</span>
    </div>
  )
}
