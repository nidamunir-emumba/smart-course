import { Link } from 'react-router-dom'
import type { Course } from '../api/types'
import { courseAssetCount } from '../api/endpoints'
import { CourseStatusBadge } from './StatusBadge'
import { ProgressRing } from './Progress'
import { ModuleTrack } from './CourseArc'

interface Props {
  course: Course
  percent?: number // student's completion, if enrolled
  index?: number // position in the grid, for a staggered reveal
}

// A short human-readable "catalog code" from the UUID — pure presentation.
function courseCode(id: string): string {
  return `CRS-${id.slice(0, 4).toUpperCase()}`
}

export function CourseCard({ course, percent, index = 0 }: Props) {
  const moduleCount = course.modules.length
  const assetCount = courseAssetCount(course)

  return (
    <Link
      to={`/courses/${course.id}`}
      className="card card-interactive reveal group flex flex-col gap-3 p-5"
      style={{ animationDelay: `${Math.min(index, 8) * 0.05}s` }}
    >
      <div className="flex items-center justify-between">
        <span className="eyebrow">{courseCode(course.id)}</span>
        <CourseStatusBadge status={course.status} />
      </div>

      <div className="flex items-start justify-between gap-3">
        <h3 className="font-display text-lg font-semibold leading-tight text-ink group-hover:text-primary">
          {course.title}
        </h3>
        {percent !== undefined && (
          <ProgressRing percent={percent} size={44} stroke={5} />
        )}
      </div>

      {course.description && (
        <p className="line-clamp-2 text-sm text-muted">{course.description}</p>
      )}

      {/* The course's shape at a glance — one tick per module. */}
      <div className="mt-auto flex flex-col gap-2 pt-1">
        {moduleCount > 0 && <ModuleTrack count={moduleCount} percent={percent} />}
        <div className="flex items-center gap-3 font-mono text-xs text-faint">
          <span>{moduleCount} modules</span>
          <span aria-hidden>·</span>
          <span>{assetCount} lessons</span>
          {course.enrollment_limit != null && (
            <>
              <span aria-hidden>·</span>
              <span>cap {course.enrollment_limit}</span>
            </>
          )}
        </div>
      </div>
    </Link>
  )
}
