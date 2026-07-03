import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { coursesApi, enrollmentsApi } from '../../api/endpoints'
import { useAuth } from '../../auth/AuthContext'
import { formatDate } from '../../lib/format'
import { Spinner, ErrorState, EmptyState } from '../../components/Feedback'

export function CertificatePage() {
  const { enrollmentId } = useParams<{ enrollmentId: string }>()
  const { user } = useAuth()

  const enrollmentQuery = useQuery({
    queryKey: ['enrollment', enrollmentId],
    queryFn: () => enrollmentsApi.get(enrollmentId!),
    enabled: !!enrollmentId,
  })

  const courseId = enrollmentQuery.data?.course_id
  const courseQuery = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => coursesApi.get(courseId!),
    enabled: !!courseId,
  })

  if (enrollmentQuery.isLoading) return <Spinner label="Loading certificate…" />
  if (enrollmentQuery.isError) return <ErrorState error={enrollmentQuery.error} />

  const enrollment = enrollmentQuery.data!
  const cert = enrollment.certificate

  if (!cert) {
    return (
      <EmptyState title="No certificate yet">
        Finish all lessons to earn your certificate.{' '}
        <Link to={`/courses/${enrollment.course_id}`} className="text-primary hover:underline">
          Go to course
        </Link>
      </EmptyState>
    )
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link to="/dashboard" className="eyebrow mb-4 inline-block hover:text-muted">
        ← my learning
      </Link>

      {/* The achievement moment — the one place the amber accent takes the stage. */}
      <div className="relative overflow-hidden rounded-[14px] border border-accent/40 bg-surface p-10">
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-accent-soft opacity-60" />
        <div className="relative flex flex-col items-center gap-5 text-center">
          <span className="eyebrow text-accent">Certificate of completion</span>

          <div className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-accent text-2xl text-accent">
            ✓
          </div>

          <div>
            <p className="text-sm text-muted">This certifies that</p>
            <p className="mt-1 font-display text-2xl font-bold text-ink">{user?.full_name}</p>
            <p className="mt-3 text-sm text-muted">has successfully completed</p>
            <p className="mt-1 font-display text-xl font-semibold text-primary">
              {courseQuery.data?.title ?? 'the course'}
            </p>
          </div>

          <div className="mt-4 flex w-full items-center justify-between border-t border-line pt-5 text-left">
            <div>
              <p className="eyebrow">Serial</p>
              <p className="font-mono text-sm text-ink">{cert.serial}</p>
            </div>
            <div className="text-right">
              <p className="eyebrow">Issued</p>
              <p className="font-mono text-sm text-ink">{formatDate(cert.issued_at)}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
