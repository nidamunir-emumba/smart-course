import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { coursesApi, courseAssetCount, enrollmentsApi } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import type { Asset, Course, Enrollment } from '../api/types'
import { CourseStatusBadge } from '../components/StatusBadge'
import { ProgressRing } from '../components/Progress'
import { AskLesson } from '../components/AskLesson'
import { LearningPath } from '../components/LearningPath'
import { DIAGRAM_MARKER, LessonDiagram } from '../components/LessonDiagram'
import { CHESS_MARKER, ChessBoard } from '../components/ChessBoard'
import { Spinner, ErrorState, InlineError } from '../components/Feedback'

export function CourseDetail() {
  const { courseId } = useParams<{ courseId: string }>()
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const courseQuery = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => coursesApi.get(courseId!),
    enabled: !!courseId,
  })

  // Durable enrollment returns 202 before the row exists — while pending,
  // poll the enrollments list until the workflow lands (or we time out).
  const [pendingEnroll, setPendingEnroll] = useState(false)

  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', user?.id],
    queryFn: () => enrollmentsApi.forStudent(user!.id),
    enabled: user?.role === 'student',
    refetchInterval: pendingEnroll ? 1200 : false,
  })

  // Toggle one lesson's completion; completing the last lesson can finish the
  // course, which creates a notification — refresh the bell alongside.
  const toggleMutation = useMutation({
    mutationFn: ({ enrollmentId, assetId, completed }: {
      enrollmentId: string
      assetId: string
      completed: boolean
    }) =>
      completed
        ? enrollmentsApi.uncompleteLesson(enrollmentId, assetId)
        : enrollmentsApi.completeLesson(enrollmentId, assetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enrollments', user?.id] })
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  // pendingEnroll resolves when the workflow's enrollment shows up; the
  // timeout stops the poll if processing stalls (worker down, etc.).
  const enrollmentArrived =
    pendingEnroll &&
    (enrollmentsQuery.data ?? []).some(
      (e) => e.course_id === courseQuery.data?.id && e.status !== 'cancelled'
    )
  useEffect(() => {
    if (enrollmentArrived) setPendingEnroll(false)
  }, [enrollmentArrived])
  useEffect(() => {
    if (!pendingEnroll) return
    const t = setTimeout(() => setPendingEnroll(false), 30_000)
    return () => clearTimeout(t)
  }, [pendingEnroll])

  // Content is gated per-enrollment: once a live enrollment exists but the
  // cached course still has bodies withheld, refetch it so lessons unlock
  // without a manual page refresh (covers the inline and durable paths).
  const hasLiveEnrollment = (enrollmentsQuery.data ?? []).some(
    (e) => e.course_id === courseQuery.data?.id && e.status !== 'cancelled'
  )
  useEffect(() => {
    if (hasLiveEnrollment && courseQuery.data?.content_locked) {
      queryClient.invalidateQueries({ queryKey: ['course', courseId] })
    }
  }, [hasLiveEnrollment, courseQuery.data?.content_locked, courseId, queryClient])

  if (courseQuery.isLoading) return <Spinner label="Loading course…" />
  if (courseQuery.isError) return <ErrorState error={courseQuery.error} />
  const course = courseQuery.data!

  // A student may hold history rows (cancelled) for this course — only a live
  // enrollment counts, preferring completed (certificate) over active.
  const rows = enrollmentsQuery.data?.filter((e) => e.course_id === course.id) ?? []
  const enrollment =
    rows.find((e) => e.status === 'completed') ??
    rows.find((e) => e.status === 'active') ??
    null
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

        <Outline
          course={course}
          enrollment={enrollment}
          onToggle={(assetId, completed) =>
            enrollment &&
            toggleMutation.mutate({ enrollmentId: enrollment.id, assetId, completed })
          }
          togglePending={toggleMutation.isPending}
        />
      </div>

      {/* Side rail: the single action for this course */}
      <aside className="lg:sticky lg:top-24 lg:self-start">
        <ActionRail
          course={course}
          enrollment={enrollment}
          isOwner={isOwner}
          canEnroll={user?.role === 'student'}
          enrollmentsLoading={user?.role === 'student' && enrollmentsQuery.isLoading}
          pendingEnroll={pendingEnroll}
          onEnrollPending={() => setPendingEnroll(true)}
        />
      </aside>
    </div>
  )
}

interface OutlineProps {
  course: Course
  enrollment: Enrollment | null
  onToggle: (assetId: string, completed: boolean) => void
  togglePending: boolean
}

function Outline({ course, enrollment, onToggle, togglePending }: OutlineProps) {
  const modules = [...course.modules].sort((a, b) => a.order_index - b.order_index)
  const completedIds = new Set(enrollment?.completed_asset_ids ?? [])
  // Toggling only makes sense while the enrollment is active; a completed
  // course shows its checks as a locked record — and says so on hover.
  const locked = enrollment != null && enrollment.status !== 'active'
  const canToggle = enrollment?.status === 'active'

  // Expansion is controlled so "Complete & continue" can advance the reader
  // to the next lesson. Reading order: modules, then lessons within each.
  const [openId, setOpenId] = useState<string | null>(null)
  // Modules collapse too — a set of collapsed module ids.
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const toggleModule = (moduleId: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(moduleId)) next.delete(moduleId)
      else next.add(moduleId)
      return next
    })

  // Fully-completed modules start collapsed — attention goes to what's left.
  // Runs once per enrollment (its data arrives async); manual toggles win after.
  const collapsedInitFor = useRef<string | null>(null)
  useEffect(() => {
    if (!enrollment || collapsedInitFor.current === enrollment.id) return
    collapsedInitFor.current = enrollment.id
    const done = new Set(enrollment.completed_asset_ids)
    setCollapsed(
      new Set(
        course.modules
          .filter((m) => m.assets.length > 0 && m.assets.every((a) => done.has(a.id)))
          .map((m) => m.id)
      )
    )
  }, [enrollment, course.modules])
  const readingOrder = modules.flatMap((m) =>
    [...m.assets].sort((a, b) => a.order_index - b.order_index)
  )
  const nextReadable = (assetId: string): Asset | null => {
    const i = readingOrder.findIndex((a) => a.id === assetId)
    // The next expandable lesson (text with a body); links/videos are opened externally.
    return readingOrder.slice(i + 1).find((a) => a.type === 'text' && a.content?.trim()) ?? null
  }
  // Scroll to the next lesson only AFTER React has expanded it (and its
  // module) in the DOM — scrolling inside the click handler targets the
  // pre-expansion layout. A ref marks the id to scroll to; the effect below
  // runs post-commit.
  const scrollToRef = useRef<string | null>(null)
  useEffect(() => {
    const id = scrollToRef.current
    if (!id || openId !== id) return
    scrollToRef.current = null
    requestAnimationFrame(() =>
      document.getElementById(`lesson-${id}`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    )
  }, [openId, collapsed])

  const completeAndContinue = (asset: Asset) => {
    if (canToggle && !togglePending && !completedIds.has(asset.id)) {
      onToggle(asset.id, false) // mark complete
    }
    const next = nextReadable(asset.id)
    setOpenId(next?.id ?? null)
    if (next) {
      // Continuing may land in a collapsed module — open it so the lesson shows.
      const home = modules.find((m) => m.assets.some((a) => a.id === next.id))
      if (home && collapsed.has(home.id)) toggleModule(home.id)
      scrollToRef.current = next.id // effect scrolls once the row is expanded
    }
  }

  if (modules.length === 0) {
    return (
      <p className="card px-5 py-8 text-center text-sm text-muted">
        No modules yet.
      </p>
    )
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="eyebrow">Syllabus · {modules.length} modules</p>
        {course.content_locked && (
          <p className="font-mono text-xs text-faint">🔒 lesson content unlocks when you enroll</p>
        )}
      </div>
      {modules.map((module, mi) => {
        const done = module.assets.filter((a) => completedIds.has(a.id)).length
        const isCollapsed = collapsed.has(module.id)
        return (
          <div key={module.id} className="card overflow-hidden">
            {/* Module header doubles as the collapse/expand control. */}
            <button
              type="button"
              aria-expanded={!isCollapsed}
              className={`flex w-full items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-paper/50 ${
                isCollapsed ? '' : 'border-b border-line'
              }`}
              onClick={() => toggleModule(module.id)}
            >
              <span className="font-mono text-sm text-primary">
                {String(mi + 1).padStart(2, '0')}
              </span>
              <h3 className="font-display font-semibold text-ink">{module.title}</h3>
              <span className="ml-auto flex shrink-0 items-center gap-3">
                {enrollment && module.assets.length > 0 && (
                  <span className="font-mono text-xs text-faint">
                    {done}/{module.assets.length} done
                  </span>
                )}
                {isCollapsed && (
                  <span className="font-mono text-xs text-faint">
                    {module.assets.length} lessons
                  </span>
                )}
                <span
                  className={`font-mono text-xs text-faint transition-transform ${
                    isCollapsed ? '' : 'rotate-90'
                  }`}
                  aria-hidden
                >
                  ›
                </span>
              </span>
            </button>
            {!isCollapsed && (
              <ul className="divide-y divide-line">
                {[...module.assets]
                  .sort((a, b) => a.order_index - b.order_index)
                  .map((asset) => (
                    <LessonRow
                      key={asset.id}
                      asset={asset}
                      courseId={course.id}
                      contentLocked={course.content_locked}
                      completed={enrollment ? completedIds.has(asset.id) : undefined}
                      canToggle={canToggle && !togglePending}
                      locked={locked}
                      onToggle={() => onToggle(asset.id, completedIds.has(asset.id))}
                      open={openId === asset.id}
                      onOpenChange={(o) => setOpenId(o ? asset.id : null)}
                      hasNext={nextReadable(asset.id) !== null}
                      onCompleteContinue={() => completeAndContinue(asset)}
                    />
                  ))}
                {module.assets.length === 0 && (
                  <li className="px-5 py-2.5 text-sm text-faint">No lessons in this module.</li>
                )}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )
}

interface LessonRowProps {
  asset: Asset
  courseId: string
  contentLocked: boolean
  completed?: boolean // undefined → not enrolled, no completion UI
  canToggle: boolean
  locked: boolean // enrollment finished — checks are a record, not controls
  onToggle: () => void
  open: boolean // expansion is controlled by the outline (reading flow)
  onOpenChange: (open: boolean) => void
  hasNext: boolean // a further readable lesson exists after this one
  onCompleteContinue: () => void
}

/** The completion check: empty circle → green check (success colour — same
 *  green as the completed ring and status badges). On a completed course the
 *  checks are locked — the tooltip says so. */
function LessonCheck({
  completed,
  canToggle,
  locked,
  onToggle,
}: Pick<LessonRowProps, 'completed' | 'canToggle' | 'locked' | 'onToggle'>) {
  if (completed === undefined) return null
  const label = locked
    ? 'Course completed — the syllabus is locked as your record'
    : completed
      ? 'Mark lesson not complete'
      : 'Mark lesson complete'
  return (
    <button
      type="button"
      aria-label={label}
      aria-disabled={!canToggle}
      title={label}
      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
        locked ? 'cursor-not-allowed' : canToggle ? '' : 'cursor-default'
      }`}
      style={{
        borderColor: completed ? 'var(--color-success)' : 'var(--color-line)',
        background: completed ? 'var(--color-success-soft)' : 'transparent',
      }}
      onClick={(e) => {
        // Inside a <summary>: don't let the check also expand the lesson.
        e.preventDefault()
        e.stopPropagation()
        if (canToggle) onToggle()
      }}
    >
      {completed && (
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden>
          <path
            d="M1.5 5.5 4 8l4.5-6"
            fill="none"
            stroke="var(--color-success)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </button>
  )
}

/** Status marker on the right of a completed lesson row — success green,
 *  matching the completed ring and enrollment badges. */
function DoneBadge() {
  return (
    <span
      className="badge shrink-0"
      style={{
        color: 'var(--color-success)',
        borderColor: 'var(--color-success)',
        background: 'var(--color-success-soft)',
      }}
    >
      ✓ done
    </span>
  )
}

function LessonRow({
  asset,
  courseId,
  completed,
  canToggle,
  locked,
  onToggle,
  open,
  onOpenChange,
  hasNext,
  onCompleteContinue,
  contentLocked,
}: LessonRowProps) {
  const body = asset.type === 'text' ? asset.content?.trim() : null
  // A text lesson with no body on a locked course = withheld behind enrollment.
  const gated = asset.type === 'text' && !body && contentLocked
  const check = (
    <LessonCheck completed={completed} canToggle={canToggle} locked={locked} onToggle={onToggle} />
  )
  const titleCls = `text-sm ${completed ? 'text-muted' : 'text-ink'}`

  // Withheld lesson: show the title and a lock, expand to an enroll nudge.
  if (gated) {
    return (
      <li id={`lesson-${asset.id}`} className="scroll-mt-20">
        <details className="group" open={open}>
          <summary
            className="flex cursor-pointer list-none items-center gap-3 px-5 py-2.5 hover:bg-paper/50"
            onClick={(e) => {
              e.preventDefault()
              onOpenChange(!open)
            }}
          >
            <span className="badge shrink-0">{asset.type}</span>
            <span className="text-sm font-medium text-muted">{asset.title}</span>
            <span className="ml-auto flex shrink-0 items-center gap-2 font-mono text-xs text-faint">
              <span aria-hidden>🔒</span>
              <span className="transition-transform group-open:rotate-90">›</span>
            </span>
          </summary>
          <div className="border-t border-line bg-paper/30 px-5 py-4 text-sm text-muted">
            Enroll to read this lesson — the syllabus is open, the content unlocks when you enroll.
          </div>
        </details>
      </li>
    )
  }

  // Text lessons expand to reveal their full body; other types link out.
  if (body) {
    const paragraphs = body.split(/\n\s*\n/)
    return (
      <li id={`lesson-${asset.id}`} className="scroll-mt-20">
        <details className="group" open={open}>
          <summary
            className="flex cursor-pointer list-none items-center gap-3 px-5 py-2.5 hover:bg-paper/50"
            onClick={(e) => {
              e.preventDefault() // expansion is controlled by the outline
              onOpenChange(!open)
            }}
          >
            {check}
            <span className="badge shrink-0">{asset.type}</span>
            <span className={`${titleCls} font-medium`}>{asset.title}</span>
            <span className="ml-auto flex shrink-0 items-center gap-2">
              {completed && <DoneBadge />}
              <span className="font-mono text-xs text-faint transition-transform group-open:rotate-90">
                ›
              </span>
            </span>
          </summary>
          <div className="space-y-4 border-t border-line bg-paper/30 px-5 py-5 text-[0.925rem] leading-7 text-ink/80">
            {paragraphs.map((p, i) => {
              // Marker paragraphs render as drawings: [diagram:name] or [fen:…].
              const trimmed = p.trim()
              const diagram = trimmed.match(DIAGRAM_MARKER)
              if (diagram) return <LessonDiagram key={i} name={diagram[1]} />
              const chess = trimmed.match(CHESS_MARKER)
              if (chess) return <ChessBoard key={i} fen={chess[1]} caption={chess[2]} />
              return (
                <p key={i} className="max-w-[62ch] whitespace-pre-wrap">
                  {p}
                </p>
              )
            })}
          </div>
          {/* Finish (or just keep reading) right where you stopped. Completing
              is only offered on an active enrollment; everyone else — completed
              courses, browsing visitors — still gets the reading flow. */}
          <div className="flex justify-end bg-paper/30 px-5 pb-4">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={completed === false && !locked && !canToggle}
              onClick={onCompleteContinue}
            >
              {completed === false && !locked
                ? hasNext
                  ? 'Complete & continue →'
                  : 'Complete lesson ✓'
                : hasNext
                  ? 'Continue →'
                  : 'Close'}
            </button>
          </div>
          {/* Ask the assistant about this lesson, right where you're reading it. */}
          <AskLesson courseId={courseId} assetId={asset.id} />
        </details>
      </li>
    )
  }

  return (
    <li id={`lesson-${asset.id}`} className="scroll-mt-20 flex items-center gap-3 px-5 py-2.5">
      {check}
      <span className="badge shrink-0">{asset.type}</span>
      <span className={titleCls}>{asset.title}</span>
      <span className="ml-auto flex shrink-0 items-center gap-2">
        {completed && <DoneBadge />}
        {asset.url && (
          <a
            href={asset.url}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-xs text-primary hover:underline"
          >
            open ↗
          </a>
        )}
      </span>
    </li>
  )
}

interface RailProps {
  course: Course
  enrollment: Enrollment | null
  isOwner: boolean
  canEnroll: boolean
  enrollmentsLoading?: boolean
  pendingEnroll?: boolean
  onEnrollPending?: () => void
}

function ActionRail({
  course,
  enrollment,
  isOwner,
  canEnroll,
  enrollmentsLoading,
  pendingEnroll,
  onEnrollPending,
}: RailProps) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const totalAssets = courseAssetCount(course)

  // The automatically derived learning path (prerequisites, transitively).
  const pathQuery = useQuery({
    queryKey: ['course-path', course.id],
    queryFn: () => coursesApi.path(course.id),
  })
  const path = pathQuery.data ?? []
  const unmetPrereqs = path.filter((s) => !s.is_target && !s.met)

  const enrollMutation = useMutation({
    mutationFn: () => enrollmentsApi.enroll(course.id),
    onSuccess: (res) => {
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['enrollments', user?.id] })
      // Enrolling creates an in-app notification — refresh the bell badge too.
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      // 202 = queued on the durable workflow; poll until the row appears.
      if (!('id' in res)) onEnrollPending?.()
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
  const blocked = canEnroll && unmetPrereqs.length > 0
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

      {/* The learning path this course sits on, derived from prerequisites. */}
      {path.length > 1 && <LearningPath steps={path} />}

      {course.status !== 'ready' ? (
        <p className="text-sm text-muted">This course isn’t open for enrollment yet.</p>
      ) : blocked ? (
        <p className="text-sm text-muted">
          Finish{' '}
          {unmetPrereqs.map((s, i) => (
            <span key={s.course_id}>
              {i > 0 && (i === unmetPrereqs.length - 1 ? ' and ' : ', ')}
              <Link to={`/courses/${s.course_id}`} className="font-medium text-primary hover:underline">
                {s.title}
              </Link>
            </span>
          ))}{' '}
          to unlock this course.
        </p>
      ) : canEnroll ? (
        <>
          <button
            className="btn btn-primary"
            disabled={enrollMutation.isPending || enrollmentsLoading || pendingEnroll}
            onClick={() => enrollMutation.mutate()}
          >
            {enrollMutation.isPending || pendingEnroll ? 'Enrolling…' : 'Enroll now'}
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
      // Completing the course creates an in-app notification — refresh the bell.
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : 'Could not update progress.'),
  })

  const unenrollMutation = useMutation({
    mutationFn: () => enrollmentsApi.unenroll(enrollment.id),
    onSuccess: () => {
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['enrollments', user?.id] })
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : 'Could not unenroll.'),
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
        <div className="flex flex-col gap-2">
          <Link to={`/certificate/${enrollment.id}`} className="btn btn-primary">
            View certificate
          </Link>
          <p className="text-center text-xs text-muted">
            Completed — the syllabus is locked as your record.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-muted">
            Check off each lesson in the syllabus as you finish it.
          </p>
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

      {/* Leaving is allowed while active; a completed course keeps its certificate. */}
      {enrollment.status === 'active' && (
        <button
          className="btn btn-danger btn-sm"
          disabled={unenrollMutation.isPending}
          onClick={() => {
            if (
              window.confirm(
                'Unenroll from this course? Your progress is kept as history, ' +
                  'but re-enrolling starts fresh.'
              )
            ) {
              unenrollMutation.mutate()
            }
          }}
        >
          {unenrollMutation.isPending ? 'Unenrolling…' : 'Unenroll'}
        </button>
      )}

      <Link to="/dashboard" className="text-center font-mono text-xs text-faint hover:text-muted">
        ← back to my learning
      </Link>
    </div>
  )
}
