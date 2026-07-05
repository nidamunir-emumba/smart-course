import { Link } from 'react-router-dom'
import type { LearningPathStep } from '../api/types'

/** The derived learning path: prerequisite chain in order, target last.
 *  Step icons follow the app's colour story — green ✓ = completed, amber
 *  dot = in progress, empty circle = not started. Used in the course rail
 *  and on the Paths page. */
export function LearningPath({
  steps,
  linkTarget = false, // Paths page links every step; the course rail labels the target "this course"
}: {
  steps: LearningPathStep[]
  linkTarget?: boolean
}) {
  return (
    <div className="flex flex-col gap-1 border-y border-line py-3">
      <p className="eyebrow mb-1">Learning path</p>
      <ol className="flex flex-col">
        {steps.map((step, i) => {
          const inProgress = !step.met && step.enrollment_status === 'active'
          return (
          <li key={step.course_id} className="flex gap-2.5">
            {/* Rail: status dot + connector. ✓ done · dot in progress · empty not started */}
            <span className="flex flex-col items-center">
              <span
                className="flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-full border text-[0.6rem]"
                style={{
                  borderColor: step.met
                    ? 'var(--color-success)'
                    : inProgress
                      ? 'var(--color-accent)'
                      : 'var(--color-line)',
                  background: step.met ? 'var(--color-success-soft)' : 'var(--color-surface)',
                  color: 'var(--color-success)',
                }}
                aria-hidden
              >
                {step.met ? (
                  '✓'
                ) : inProgress ? (
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ background: 'var(--color-accent)' }}
                  />
                ) : (
                  ''
                )}
              </span>
              {i < steps.length - 1 && <span className="w-px flex-1 bg-line" aria-hidden />}
            </span>
            <div className="min-w-0 pb-2.5">
              {step.is_target && !linkTarget ? (
                <span className="text-sm font-medium text-ink">{step.title}</span>
              ) : (
                <Link
                  to={`/courses/${step.course_id}`}
                  className="text-sm font-medium text-ink hover:text-primary"
                >
                  {step.title}
                </Link>
              )}
              <span className="block font-mono text-[0.65rem] text-faint">
                {step.is_target && !linkTarget
                  ? 'this course'
                  : step.met
                    ? 'completed'
                    : step.enrollment_status === 'active'
                      ? `in progress · ${Math.round(step.percent_complete ?? 0)}%`
                      : step.is_target
                        ? 'final course'
                        : 'not started'}
              </span>
            </div>
          </li>
          )
        })}
      </ol>
    </div>
  )
}
