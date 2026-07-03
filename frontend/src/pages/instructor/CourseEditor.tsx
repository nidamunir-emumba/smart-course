import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { coursesApi } from '../../api/endpoints'
import { ApiError } from '../../api/client'
import type { AssetType, Course, Module } from '../../api/types'
import { CourseStatusBadge } from '../../components/StatusBadge'
import { Spinner, ErrorState, InlineError } from '../../components/Feedback'

export function CourseEditor() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const courseQuery = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => coursesApi.get(courseId!),
    enabled: !!courseId,
  })

  // Any content/lifecycle op returns the full course; write it straight to cache.
  function applyCourse(course: Course) {
    queryClient.setQueryData(['course', courseId], course)
    queryClient.invalidateQueries({ queryKey: ['courses'] })
    setError(null)
  }
  function onError(err: unknown) {
    setError(err instanceof ApiError ? err.message : 'Action failed.')
  }

  const publish = useMutation({ mutationFn: () => coursesApi.publish(courseId!), onSuccess: applyCourse, onError })
  const unpublish = useMutation({ mutationFn: () => coursesApi.unpublish(courseId!), onSuccess: applyCourse, onError })
  const archive = useMutation({ mutationFn: () => coursesApi.archive(courseId!), onSuccess: applyCourse, onError })
  const remove = useMutation({
    mutationFn: () => coursesApi.remove(courseId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['courses'] })
      navigate('/instructor')
    },
    onError,
  })

  if (courseQuery.isLoading) return <Spinner label="Loading course…" />
  if (courseQuery.isError) return <ErrorState error={courseQuery.error} />
  const course = courseQuery.data!
  const editable = course.status === 'draft'

  return (
    <div className="flex flex-col gap-6">
      <Link to="/instructor" className="eyebrow inline-block hover:text-muted">
        ← my courses
      </Link>

      {/* Header + lifecycle actions */}
      <div className="card flex flex-wrap items-center gap-4 p-5">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <CourseStatusBadge status={course.status} />
            <span className="font-mono text-xs text-faint">
              CRS-{course.id.slice(0, 4).toUpperCase()}
            </span>
          </div>
          <h1 className="font-display text-2xl font-bold text-ink">{course.title}</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link to={`/courses/${course.id}`} className="btn btn-ghost btn-sm">
            Preview
          </Link>
          {course.status === 'draft' && (
            <button className="btn btn-primary btn-sm" disabled={publish.isPending} onClick={() => publish.mutate()}>
              Publish
            </button>
          )}
          {course.status === 'ready' && (
            <button className="btn btn-ghost btn-sm" disabled={unpublish.isPending} onClick={() => unpublish.mutate()}>
              Unpublish
            </button>
          )}
          {course.status !== 'archived' && (
            <button className="btn btn-ghost btn-sm" disabled={archive.isPending} onClick={() => archive.mutate()}>
              Archive
            </button>
          )}
          {course.status === 'draft' && (
            <button
              className="btn btn-danger btn-sm"
              disabled={remove.isPending}
              onClick={() => {
                if (confirm('Delete this draft course? This cannot be undone.')) remove.mutate()
              }}
            >
              Delete
            </button>
          )}
        </div>
      </div>

      {error && <InlineError message={error} />}

      {!editable && (
        <p className="rounded-[14px] border border-line bg-surface px-4 py-3 text-sm text-muted">
          Content is locked while <strong>{course.status}</strong>. Unpublish to edit modules and
          lessons.
        </p>
      )}

      {/* Modules */}
      <div className="flex flex-col gap-4">
        <p className="eyebrow">Curriculum · {course.modules.length} modules</p>
        {[...course.modules]
          .sort((a, b) => a.order_index - b.order_index)
          .map((module, i) => (
            <ModuleEditor
              key={module.id}
              index={i}
              course={course}
              module={module}
              editable={editable}
              onCourse={applyCourse}
              onError={onError}
            />
          ))}
        {editable && <AddModule courseId={course.id} nextIndex={course.modules.length} onCourse={applyCourse} onError={onError} />}
      </div>
    </div>
  )
}

// ── Module ───────────────────────────────────────────────────────────────────
interface ModuleProps {
  index: number
  course: Course
  module: Module
  editable: boolean
  onCourse: (c: Course) => void
  onError: (e: unknown) => void
}

function ModuleEditor({ index, course, module, editable, onCourse, onError }: ModuleProps) {
  const removeModule = useMutation({
    mutationFn: () => coursesApi.removeModule(course.id, module.id),
    onSuccess: onCourse,
    onError,
  })

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-3 border-b border-line px-5 py-3">
        <span className="font-mono text-sm text-primary">{String(index + 1).padStart(2, '0')}</span>
        <h3 className="flex-1 font-display font-semibold text-ink">{module.title}</h3>
        {editable && (
          <button
            className="btn btn-danger btn-sm"
            disabled={removeModule.isPending}
            onClick={() => removeModule.mutate()}
          >
            Remove
          </button>
        )}
      </div>

      <ul className="divide-y divide-line">
        {[...module.assets]
          .sort((a, b) => a.order_index - b.order_index)
          .map((asset) => (
            <li key={asset.id} className="flex items-center gap-3 px-5 py-2.5">
              <span className="badge shrink-0">{asset.type}</span>
              <span className="flex-1 text-sm text-ink">{asset.title}</span>
              {editable && (
                <RemoveAsset courseId={course.id} moduleId={module.id} assetId={asset.id} onCourse={onCourse} onError={onError} />
              )}
            </li>
          ))}
        {module.assets.length === 0 && (
          <li className="px-5 py-2.5 text-sm text-faint">No lessons yet.</li>
        )}
      </ul>

      {editable && (
        <AddAsset
          courseId={course.id}
          moduleId={module.id}
          nextIndex={module.assets.length}
          onCourse={onCourse}
          onError={onError}
        />
      )}
    </div>
  )
}

function RemoveAsset({
  courseId,
  moduleId,
  assetId,
  onCourse,
  onError,
}: {
  courseId: string
  moduleId: string
  assetId: string
  onCourse: (c: Course) => void
  onError: (e: unknown) => void
}) {
  const m = useMutation({
    mutationFn: () => coursesApi.removeAsset(courseId, moduleId, assetId),
    onSuccess: onCourse,
    onError,
  })
  return (
    <button
      className="font-mono text-xs text-danger hover:underline disabled:opacity-50"
      disabled={m.isPending}
      onClick={() => m.mutate()}
    >
      remove
    </button>
  )
}

// ── Add forms ─────────────────────────────────────────────────────────────────
function AddModule({
  courseId,
  nextIndex,
  onCourse,
  onError,
}: {
  courseId: string
  nextIndex: number
  onCourse: (c: Course) => void
  onError: (e: unknown) => void
}) {
  const [title, setTitle] = useState('')
  const m = useMutation({
    mutationFn: () => coursesApi.addModule(courseId, { title: title.trim(), order_index: nextIndex }),
    onSuccess: (c) => {
      setTitle('')
      onCourse(c)
    },
    onError,
  })

  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        if (title.trim()) m.mutate()
      }}
    >
      <input
        className="field-input"
        placeholder="New module title…"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <button type="submit" className="btn btn-ghost" disabled={!title.trim() || m.isPending}>
        + Module
      </button>
    </form>
  )
}

const ASSET_TYPES: AssetType[] = ['text', 'video', 'pdf', 'link']

function AddAsset({
  courseId,
  moduleId,
  nextIndex,
  onCourse,
  onError,
}: {
  courseId: string
  moduleId: string
  nextIndex: number
  onCourse: (c: Course) => void
  onError: (e: unknown) => void
}) {
  const [title, setTitle] = useState('')
  const [type, setType] = useState<AssetType>('text')
  const [value, setValue] = useState('')

  const m = useMutation({
    mutationFn: () =>
      coursesApi.addAsset(courseId, moduleId, {
        title: title.trim(),
        type,
        order_index: nextIndex,
        // text lessons carry inline content; others carry a URL.
        content: type === 'text' ? value || null : null,
        url: type === 'text' ? null : value || null,
      }),
    onSuccess: (c) => {
      setTitle('')
      setValue('')
      setType('text')
      onCourse(c)
    },
    onError,
  })

  return (
    <form
      className="flex flex-wrap items-end gap-2 border-t border-line bg-paper/40 px-5 py-3"
      onSubmit={(e) => {
        e.preventDefault()
        if (title.trim()) m.mutate()
      }}
    >
      <input
        className="field-input flex-1"
        placeholder="Lesson title…"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <select className="field-select w-28" value={type} onChange={(e) => setType(e.target.value as AssetType)}>
        {ASSET_TYPES.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <input
        className="field-input flex-1"
        placeholder={type === 'text' ? 'Inline content (optional)' : 'URL (optional)'}
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit" className="btn btn-ghost btn-sm" disabled={!title.trim() || m.isPending}>
        + Lesson
      </button>
    </form>
  )
}
