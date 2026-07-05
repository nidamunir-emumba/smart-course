import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { coursesApi, courseAssetCount, enrollmentsApi } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import type { Asset, Course, Enrollment } from '../api/types'
import { CourseStatusBadge } from '../components/StatusBadge'
import { ProgressRing } from '../components/Progress'
import { Spinner, ErrorState, InlineError } from '../components/Feedback'

export function CourseDetail() {
  const { courseId } = useParams<{ courseId: string }>()
  const { user } = useAuth()

  const courseQuery = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => coursesApi.get(courseId!),
    enabled: !!courseId,
  })

  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', user?.id],
    queryFn: () => enrollmentsApi.forStudent(user!.id),
    enabled: user?.role === 'student',
  })

  if (courseQuery.isLoading) return <Spinner label="Loading course…" />
  if (courseQuery.isError) return <ErrorState error={courseQuery.error} />
  const course = courseQuery.data!

  const enrollment =
    enrollmentsQuery.data?.find((e) => e.course_id === course.id) ?? null
  const isOwner = user?.role === 'instructor' && user.id === course.instructor_id

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
      {/* Main column: course thesis + numbered outline */}
      <div className="flex flex-col gap-6">
        <div>
          <div className="mb-2 flex items-center gap-3">
            <span className="eyebrow">CRS-{course.id.slice(0, 4).toUpperCase()}</span>
            <CourseStatusBadge status={course.status} />
          </div>
          <h1 className="font-display text-3xl font-bold leading-tight text-ink">
            {course.title}
          </h1>
          {course.description && (
            <p className="mt-3 max-w-2xl text-muted">{course.description}</p>
          )}
        </div>

        <Outline course={course} />
      </div>

      {/* Side rail: the single action for this course */}
      <aside className="lg:sticky lg:top-24 lg:self-start">
        <ActionRail
          course={course}
          enrollment={enrollment}
          isOwner={isOwner}
          canEnroll={user?.role === 'student'}
          enrollmentsLoading={user?.role === 'student' && enrollmentsQuery.isLoading}
        />
      </aside>
    </div>
  )
}

function Outline({ course }: { course: Course }) {
  const modules = [...course.modules].sort((a, b) => a.order_index - b.order_index)
  if (modules.length === 0) {
    return (
      <p className="card px-5 py-8 text-center text-sm text-muted">
        No modules yet.
      </p>
    )
  }
  return (
    <div className="flex flex-col gap-4">
      <p className="eyebrow">Syllabus · {modules.length} modules</p>
      {modules.map((module, mi) => (
        <div key={module.id} className="card overflow-hidden">
          <div className="flex items-center gap-3 border-b border-line px-5 py-3">
            <span className="font-mono text-sm text-primary">
              {String(mi + 1).padStart(2, '0')}
            </span>
            <h3 className="font-display font-semibold text-ink">{module.title}</h3>
          </div>
          <ul className="divide-y divide-line">
            {[...module.assets]
              .sort((a, b) => a.order_index - b.order_index)
              .map((asset) => (
                <LessonRow key={asset.id} asset={asset} />
              ))}
            {module.assets.length === 0 && (
              <li className="px-5 py-2.5 text-sm text-faint">No lessons in this module.</li>
            )}
          </ul>
        </div>
      ))}
    </div>
  )
}

function LessonRow({ asset }: { asset: Asset }) {
  const body = asset.type === 'text' ? asset.content?.trim() : null

  // Text lessons expand to reveal their full body; other types link out.
  if (body) {
    const paragraphs = body.split(/\n\s*\n/)
    return (
      <li>
        <details className="group">
          <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-2.5 hover:bg-paper/50">
            <span className="badge shrink-0">{asset.type}</span>
            <span className="text-sm font-medium text-ink">{asset.title}</span>
            <span className="ml-auto font-mono text-xs text-faint transition-transform group-open:rotate-90">
              ›
            </span>
          </summary>
          <div className="space-y-4 border-t border-line bg-paper/30 px-5 py-5 text-[0.925rem] leading-7 text-ink/80">
            {paragraphs.map((p, i) => (
              <p key={i} className="max-w-[62ch] whitespace-pre-wrap">
                {p}
              </p>
            ))}
          </div>
        </details>
      </li>
    )
  }

  return (
    <li className="flex items-center gap-3 px-5 py-2.5">
      <span className="badge shrink-0">{asset.type}</span>
      <span className="text-sm text-ink">{asset.title}</span>
      {asset.url && (
        <a
          href={asset.url}
          target="_blank"
          rel="noreferrer"
          className="ml-auto font-mono text-xs text-primary hover:underline"
        >
          open ↗
        </a>
      )}
    </li>
  )
}

interface RailProps {
  course: Course
  enrollment: Enrollment | null
  isOwner: boolean
  canEnroll: boolean
  enrollmentsLoading?: boolean
}

function ActionRail({ course, enrollment, isOwner, canEnroll, enrollmentsLoading }: RailProps) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const totalAssets = courseAssetCount(course)

  const enrollMutation = useMutation({
    mutationFn: () => enrollmentsApi.enroll(course.id),
    onSuccess: () => {
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['enrollments', user?.id] })
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : 'Could not enroll.'),
  })

  if (isOwner) {
    return (
      <div className="card flex flex-col gap-3 p-5">
        <p className="eyebrow">You own this course</p>
        <Link to={`/instructor/courses/${course.id}`} className="btn btn-primary">
          Manage course
        </Link>
      </div>
    )
  }

  if (enrollment) {
    return <ProgressRail course={course} enrollment={enrollment} />
  }

  // Not enrolled.
  return (
    <div className="card flex flex-col gap-4 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">Enroll</p>
          <p className="font-display text-lg font-semibold text-ink">
            {totalAssets} lessons
          </p>
        </div>
        <ProgressRing percent={0} size={48} stroke={5} showLabel={false} />
      </div>

      {course.status !== 'ready' ? (
        <p className="text-sm text-muted">This course isn’t open for enrollment yet.</p>
      ) : canEnroll ? (
        <>
          <button
            className="btn btn-primary"
            disabled={enrollMutation.isPending || enrollmentsLoading}
            onClick={() => enrollMutation.mutate()}
          >
            {enrollMutation.isPending ? 'Enrolling…' : 'Enroll now'}
          </button>
          {error && <InlineError message={error} />}
        </>
      ) : user ? (
        <p className="text-sm text-muted">Only students can enroll in courses.</p>
      ) : (
        <Link to="/login" className="btn btn-primary">
          Sign in to enroll
        </Link>
      )}
    </div>
  )
}

function ProgressRail({ course, enrollment }: { course: Course; enrollment: Enrollment }) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const total = enrollment.progress?.total_assets ?? courseAssetCount(course)
  const completed = enrollment.progress?.completed_assets ?? 0
  const percent = enrollment.progress?.percent_complete ?? 0

  const progressMutation = useMutation({
    mutationFn: (completedAssets: number) =>
      enrollmentsApi.setProgress(enrollment.id, completedAssets),
    onSuccess: () => {
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['enrollments', user?.id] })
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : 'Could not update progress.'),
  })

  return (
    <div className="card flex flex-col gap-4 p-5">
      <div className="flex items-center gap-4">
        <ProgressRing percent={percent} size={64} stroke={7} />
        <div>
          <p className="eyebrow">Your progress</p>
          <p className="font-display text-lg font-semibold text-ink">
            {completed} / {total} lessons
          </p>
        </div>
      </div>

      {enrollment.status === 'completed' && enrollment.certificate ? (
        <Link to={`/certificate/${enrollment.id}`} className="btn btn-primary">
          View certificate
        </Link>
      ) : (
        <div className="flex flex-col gap-2">
          <button
            className="btn btn-ghost btn-sm"
            disabled={progressMutation.isPending || completed >= total}
            onClick={() => progressMutation.mutate(Math.min(total, completed + 1))}
          >
            Mark next lesson complete
          </button>
          <button
            className="btn btn-primary btn-sm"
            disabled={progressMutation.isPending || completed >= total || total === 0}
            onClick={() => progressMutation.mutate(total)}
          >
            Complete all {total} lessons
          </button>
        </div>
      )}

      {error && <InlineError message={error} />}
      <Link to="/dashboard" className="text-center font-mono text-xs text-faint hover:text-muted">
        ← back to my learning
      </Link>
    </div>
  )
}
