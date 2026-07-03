import type { ReactNode } from 'react'
import { ApiError } from '../api/client'

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted">
      <span
        className="h-6 w-6 animate-spin rounded-full border-2 border-line border-t-primary"
        aria-hidden
      />
      {label && <p className="text-sm">{label}</p>}
    </div>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : 'Something went wrong.'
  return (
    <div
      role="alert"
      className="rounded-[14px] border border-danger/40 bg-danger-soft px-4 py-3 text-sm text-danger"
    >
      {message}
    </div>
  )
}

export function EmptyState({
  title,
  children,
}: {
  title: string
  children?: ReactNode
}) {
  return (
    <div className="card flex flex-col items-center gap-2 px-6 py-14 text-center">
      <p className="font-display text-lg font-medium text-ink">{title}</p>
      {children && <div className="max-w-md text-sm text-muted">{children}</div>}
    </div>
  )
}

export function InlineError({ message }: { message: string }) {
  return (
    <p role="alert" className="mt-1 text-sm text-danger">
      {message}
    </p>
  )
}
