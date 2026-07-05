import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { coursesApi, enrollmentsApi } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import type { Enrollment } from '../api/types'
import { CourseCard } from '../components/CourseCard'
import { HeroArc } from '../components/CourseArc'
import { Pagination } from '../components/Pagination'
import { Spinner, ErrorState, EmptyState } from '../components/Feedback'

const LIMIT = 12

export function Catalog() {
  const { user, loading } = useAuth()
  const [offset, setOffset] = useState(0)
  const [showArchived, setShowArchived] = useState(false)
  const queryClient = useQueryClient()

  const coursesQuery = useQuery({
    queryKey: ['courses', offset],
    queryFn: () => coursesApi.list(LIMIT, offset),
    enabled: !!user, // the catalog endpoint requires authentication
  })

  // Students see their own completion on each card. Declared before the early
  // returns below so hook order stays stable across anonymous / logged-in
  // renders; `enabled` gates the actual fetch.
  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', user?.id],
    queryFn: () => enrollmentsApi.forStudent(user!.id),
    enabled: user?.role === 'student',
  })

  // Shelve/unshelve straight from the card — no need to open the course.
  const archiveMutation = useMutation({
    mutationFn: ({ id, archived }: { id: string; archived: boolean }) =>
      archived ? enrollmentsApi.unarchive(id) : enrollmentsApi.archive(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['enrollments', user?.id] }),
  })

  // The backend gates all course data behind auth — greet anonymous visitors.
  if (loading) return <Spinner label="Loading…" />
  if (!user) return <Landing />

  const percentByCourse = new Map<string, number>()
  const enrollmentByCourse = new Map<string, Enrollment>()
  for (const e of enrollmentsQuery.data ?? []) {
    if (e.status === 'cancelled') continue // history rows don't show on cards
    percentByCourse.set(e.course_id, e.progress?.percent_complete ?? 0)
    // Prefer the completed row (certificate) over an active one.
    const current = enrollmentByCourse.get(e.course_id)
    if (!current || e.status === 'completed') enrollmentByCourse.set(e.course_id, e)
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Hero: states the catalog's job and who it serves. */}
      <section className="reveal flex flex-col gap-3 border-b border-line pb-8">
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
          {(() => {
            // Courses whose enrollment the student shelved are hidden by
            // default — the filter chip brings them back.
            const isArchived = (courseId: string) =>
              enrollmentByCourse.get(courseId)?.archived_at != null
            const archivedCount = coursesQuery.data.filter((c) => isArchived(c.id)).length
            const visible = showArchived
              ? coursesQuery.data
              : coursesQuery.data.filter((c) => !isArchived(c.id))
            return (
              <>
                {archivedCount > 0 && (
                  <div className="-mt-4 flex justify-end">
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => setShowArchived((v) => !v)}
                    >
                      {showArchived
                        ? 'Hide archived'
                        : `Show archived · ${archivedCount}`}
                    </button>
                  </div>
                )}
                {visible.length === 0 ? (
                  <EmptyState title="Everything on this page is archived">
                    Use “Show archived” above to see your shelved courses.
                  </EmptyState>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {visible.map((course, i) => {
                      const enrollment = enrollmentByCourse.get(course.id)
                      return (
                        <CourseCard
                          key={course.id}
                          course={course}
                          percent={percentByCourse.get(course.id)}
                          index={i}
                          archived={enrollment ? enrollment.archived_at !== null : undefined}
                          onToggleArchive={
                            enrollment
                              ? () =>
                                  archiveMutation.mutate({
                                    id: enrollment.id,
                                    archived: enrollment.archived_at !== null,
                                  })
                              : undefined
                          }
                          archivePending={archiveMutation.isPending}
                        />
                      )
                    })}
                  </div>
                )}
              </>
            )
          })()}
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
    <div className="reveal mx-auto flex max-w-4xl flex-col gap-10 py-6">
      <div className="flex flex-col items-start gap-5">
        <p className="eyebrow">SmartCourse · learning platform</p>
        <h1 className="font-display text-4xl font-bold leading-[1.05] text-ink sm:text-5xl">
          Every course is an arc —
          <br />
          from the first module to the certificate.
        </h1>
        <p className="max-w-xl text-lg text-muted">
          Sign in to browse the catalog, enroll, and work through each course module by
          module. Reach 100% and the certificate is yours. Or teach: publish your own.
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

      {/* The signature: the whole product drawn as one figure on the board. */}
      <figure className="card m-0 flex flex-col gap-4 p-6 sm:p-8">
        <figcaption className="flex items-center justify-between">
          <span className="eyebrow">Fig. 01 — the path to completion</span>
          <span className="eyebrow hidden sm:inline">enroll → modules → certificate</span>
        </figcaption>
        <HeroArc />
      </figure>
    </div>
  )
}
