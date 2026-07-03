// Signature element: the completion ring. Reused on course cards, the student
// dashboard, and the certificate — the one place amber (achievement) appears.

interface RingProps {
  percent: number // 0..100
  size?: number
  stroke?: number
  showLabel?: boolean
}

export function ProgressRing({ percent, size = 56, stroke = 6, showLabel = true }: RingProps) {
  const clamped = Math.max(0, Math.min(100, percent))
  const r = (size - stroke) / 2
  const circumference = 2 * Math.PI * r
  const offset = circumference * (1 - clamped / 100)
  const done = clamped >= 100

  return (
    <div className="relative inline-flex" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-line)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={done ? 'var(--color-success)' : 'var(--color-accent)'}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.4s ease' }}
        />
      </svg>
      {showLabel && (
        <span className="absolute inset-0 flex items-center justify-center font-mono text-[0.7rem] font-medium text-ink">
          {Math.round(clamped)}%
        </span>
      )}
    </div>
  )
}

export function ProgressBar({ percent }: { percent: number }) {
  const clamped = Math.max(0, Math.min(100, percent))
  const done = clamped >= 100
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-line">
      <div
        className="h-full rounded-full"
        style={{
          width: `${clamped}%`,
          background: done ? 'var(--color-success)' : 'var(--color-accent)',
          transition: 'width 0.4s ease',
        }}
      />
    </div>
  )
}
