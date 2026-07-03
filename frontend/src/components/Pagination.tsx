interface Props {
  offset: number
  limit: number
  count: number // items returned in the current page
  onChange: (offset: number) => void
}

/** Offset/limit pager. `count < limit` signals the last page. */
export function Pagination({ offset, limit, count, onChange }: Props) {
  const page = Math.floor(offset / limit) + 1
  const hasPrev = offset > 0
  const hasNext = count === limit

  if (!hasPrev && !hasNext) return null

  return (
    <div className="flex items-center justify-center gap-4 pt-2">
      <button
        className="btn btn-ghost btn-sm"
        disabled={!hasPrev}
        onClick={() => onChange(Math.max(0, offset - limit))}
      >
        ← Prev
      </button>
      <span className="font-mono text-xs text-faint">page {page}</span>
      <button
        className="btn btn-ghost btn-sm"
        disabled={!hasNext}
        onClick={() => onChange(offset + limit)}
      >
        Next →
      </button>
    </div>
  )
}
