import type { CourseStatus, EnrollmentStatus } from '../api/types'

const COURSE_STYLES: Record<CourseStatus, string> = {
  draft: 'text-muted border-line bg-paper',
  publishing: 'text-primary border-primary/30 bg-primary/5',
  ready: 'text-success border-success/30 bg-success-soft',
  archived: 'text-faint border-line bg-paper',
}

const ENROLL_STYLES: Record<EnrollmentStatus, string> = {
  active: 'text-primary border-primary/30 bg-primary/5',
  completed: 'text-success border-success/30 bg-success-soft',
  cancelled: 'text-faint border-line bg-paper',
}

export function CourseStatusBadge({ status }: { status: CourseStatus }) {
  return <span className={`badge ${COURSE_STYLES[status]}`}>{status}</span>
}

export function EnrollmentStatusBadge({ status }: { status: EnrollmentStatus }) {
  return <span className={`badge ${ENROLL_STYLES[status]}`}>{status}</span>
}
