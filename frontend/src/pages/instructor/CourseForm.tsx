import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { coursesApi } from '../../api/endpoints'
import { ApiError } from '../../api/client'
import { InlineError } from '../../components/Feedback'

const schema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  enrollment_limit: z
    .string()
    .optional()
    .refine((v) => !v || Number(v) > 0, 'Must be a positive number'),
})
type Form = z.infer<typeof schema>

export function CourseForm() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Form>({ resolver: zodResolver(schema) })

  const mutation = useMutation({
    mutationFn: (values: Form) =>
      coursesApi.create({
        title: values.title,
        description: values.description || null,
        enrollment_limit: values.enrollment_limit ? Number(values.enrollment_limit) : null,
      }),
    onSuccess: (course) => {
      queryClient.invalidateQueries({ queryKey: ['courses'] })
      navigate(`/instructor/courses/${course.id}`)
    },
    onError: (err) =>
      setFormError(err instanceof ApiError ? err.message : 'Could not create course.'),
  })

  return (
    <div className="mx-auto max-w-xl">
      <Link to="/instructor" className="eyebrow mb-4 inline-block hover:text-muted">
        ← my courses
      </Link>
      <h1 className="mb-6 font-display text-3xl font-bold text-ink">New course</h1>

      <form
        onSubmit={handleSubmit((v) => mutation.mutate(v))}
        className="card flex flex-col gap-4 p-6"
        noValidate
      >
        <div>
          <label className="field-label" htmlFor="title">
            Title
          </label>
          <input id="title" className="field-input" {...register('title')} />
          {errors.title && <InlineError message={errors.title.message!} />}
        </div>
        <div>
          <label className="field-label" htmlFor="description">
            Description
          </label>
          <textarea id="description" rows={4} className="field-textarea" {...register('description')} />
        </div>
        <div>
          <label className="field-label" htmlFor="enrollment_limit">
            Enrollment limit <span className="text-faint">(optional)</span>
          </label>
          <input
            id="enrollment_limit"
            type="number"
            min={1}
            className="field-input"
            placeholder="Unlimited"
            {...register('enrollment_limit')}
          />
          {errors.enrollment_limit && <InlineError message={errors.enrollment_limit.message!} />}
        </div>

        {formError && <InlineError message={formError} />}

        <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
          {mutation.isPending ? 'Creating…' : 'Create draft'}
        </button>
        <p className="text-center text-xs text-faint">
          Courses start as a draft. Add modules and lessons next, then publish.
        </p>
      </form>
    </div>
  )
}
