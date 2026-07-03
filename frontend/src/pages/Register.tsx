import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import { InlineError } from '../components/Feedback'

const schema = z.object({
  full_name: z.string().min(1, 'Your name is required'),
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'At least 8 characters'),
  role: z.enum(['student', 'instructor']),
})
type Form = z.infer<typeof schema>

export function Register() {
  const { user, register: signUp } = useAuth()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { role: 'student' } })

  if (user) return <Navigate to="/" replace />

  const role = watch('role')

  async function onSubmit(values: Form) {
    setFormError(null)
    try {
      await signUp(values)
      navigate(role === 'instructor' ? '/instructor' : '/', { replace: true })
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : 'Registration failed.')
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <p className="eyebrow mb-2">Join SmartCourse</p>
      <h1 className="mb-6 font-display text-3xl font-bold text-ink">Create your account</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="card flex flex-col gap-4 p-6" noValidate>
        {/* Role selector — sets what the account can do. */}
        <div>
          <span className="field-label">I want to</span>
          <div className="grid grid-cols-2 gap-3">
            {(['student', 'instructor'] as const).map((r) => (
              <label
                key={r}
                className={[
                  'cursor-pointer rounded-[10px] border px-3 py-3 text-center transition-colors',
                  role === r ? 'border-primary bg-primary/5' : 'border-line hover:border-muted',
                ].join(' ')}
              >
                <input type="radio" value={r} className="sr-only" {...register('role')} />
                <span className="block font-display text-sm font-medium text-ink">
                  {r === 'student' ? 'Take courses' : 'Teach courses'}
                </span>
                <span className="eyebrow">{r}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="field-label" htmlFor="full_name">
            Full name
          </label>
          <input id="full_name" className="field-input" {...register('full_name')} />
          {errors.full_name && <InlineError message={errors.full_name.message!} />}
        </div>
        <div>
          <label className="field-label" htmlFor="email">
            Email
          </label>
          <input id="email" type="email" className="field-input" {...register('email')} />
          {errors.email && <InlineError message={errors.email.message!} />}
        </div>
        <div>
          <label className="field-label" htmlFor="password">
            Password
          </label>
          <input id="password" type="password" className="field-input" {...register('password')} />
          {errors.password && <InlineError message={errors.password.message!} />}
        </div>

        {formError && <InlineError message={formError} />}

        <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
          {isSubmitting ? 'Creating…' : 'Create account'}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-muted">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  )
}
