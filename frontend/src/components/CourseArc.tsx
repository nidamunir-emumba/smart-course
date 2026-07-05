// Signature element: a course drawn as a rising arc — a syllabus plotted on
// drafting paper. Indigo carries the structure (enroll → modules); the single
// warm amber is reserved for the terminal seal, the same achievement colour as
// the completion ring. See tokens in index.css.

// Cubic-bezier sample point — used to seat the module nodes on the arc.
function onCurve(
  t: number,
  p0: [number, number],
  p1: [number, number],
  p2: [number, number],
  p3: [number, number],
): [number, number] {
  const u = 1 - t
  const a = u * u * u
  const b = 3 * u * u * t
  const c = 3 * u * t * t
  const d = t * t * t
  return [
    a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
  ]
}

const P0: [number, number] = [64, 190]
const P1: [number, number] = [250, 190]
const P2: [number, number] = [470, 96]
const P3: [number, number] = [696, 80]
const PATH = `M${P0[0]},${P0[1]} C${P1[0]},${P1[1]} ${P2[0]},${P2[1]} ${P3[0]},${P3[1]}`

// Interior module nodes, seated along the arc.
const MODULE_T = [0.22, 0.44, 0.63, 0.82]

/**
 * The landing hero visual: the whole product in one drawing — you enroll, work
 * through the modules, and the arc resolves into the certificate seal.
 */
export function HeroArc() {
  const start = onCurve(0, P0, P1, P2, P3)
  const end = onCurve(1, P0, P1, P2, P3)

  return (
    <svg
      viewBox="0 0 760 236"
      className="h-auto w-full"
      role="img"
      aria-label="A course drawn as a rising arc: enroll, work through the modules, and earn the certificate."
    >
      {/* faint dropline under the terminal seal — a drafting dimension mark */}
      <line
        x1={end[0]}
        y1={end[1]}
        x2={end[0]}
        y2={214}
        stroke="var(--color-line)"
        strokeWidth={1}
        strokeDasharray="3 4"
      />
      <line
        x1={start[0]}
        y1={start[1]}
        x2={start[0]}
        y2={214}
        stroke="var(--color-line)"
        strokeWidth={1}
        strokeDasharray="3 4"
      />
      <line x1={40} y1={214} x2={720} y2={214} stroke="var(--color-line)" strokeWidth={1} />

      {/* the arc itself, drawing in left → right */}
      <path
        d={PATH}
        className="arc-line"
        pathLength={1}
        fill="none"
        stroke="var(--color-primary)"
        strokeWidth={2.5}
        strokeLinecap="round"
        style={{ strokeDasharray: 1, ['--draw-length' as string]: 1 }}
      />

      {/* start node — enrollment */}
      <g className="arc-node" style={{ animationDelay: '0.15s' }}>
        <circle cx={start[0]} cy={start[1]} r={7} fill="var(--color-surface)" stroke="var(--color-primary)" strokeWidth={2.5} />
        <text x={start[0]} y={230} textAnchor="middle" className="fill-[var(--color-faint)] font-mono text-[11px]">
          enroll
        </text>
      </g>

      {/* module nodes, settling in behind the line */}
      {MODULE_T.map((t, i) => {
        const [x, y] = onCurve(t, P0, P1, P2, P3)
        return (
          <g key={i} className="arc-node" style={{ animationDelay: `${0.7 + i * 0.12}s` }}>
            <circle cx={x} cy={y} r={5} fill="var(--color-surface)" stroke="var(--color-primary)" strokeWidth={2} />
            <text x={x} y={y - 14} textAnchor="middle" className="fill-[var(--color-faint)] font-mono text-[10px]">
              {String(i + 1).padStart(2, '0')}
            </text>
          </g>
        )
      })}

      {/* terminal — the certificate seal, the one place amber takes the stage */}
      <g className="arc-node" style={{ animationDelay: '1.25s' }}>
        <circle cx={end[0]} cy={end[1]} r={22} fill="var(--color-accent-soft)" stroke="var(--color-accent)" strokeWidth={2.5} />
        <path
          d={`M${end[0] - 9},${end[1]} l6,6 l12,-13`}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <text x={end[0]} y={230} textAnchor="middle" className="fill-[var(--color-accent)] font-mono text-[11px]">
          certificate
        </text>
      </g>
    </svg>
  )
}

/**
 * Card-scale version of the arc: a course's shape read at a glance. Each tick is
 * a module; when a student is enrolled, completed modules fill amber.
 */
export function ModuleTrack({ count, percent }: { count: number; percent?: number }) {
  const n = Math.max(count, 1)
  // How many ticks read as "done" — round so any progress lights the first tick.
  const done = percent === undefined ? 0 : Math.round((percent / 100) * n)

  return (
    <div className="flex items-center gap-[3px]" aria-hidden>
      {Array.from({ length: n }).map((_, i) => (
        <span
          key={i}
          className="h-1.5 flex-1 rounded-full"
          style={{
            background:
              percent === undefined
                ? 'color-mix(in srgb, var(--color-primary) 22%, transparent)'
                : i < done
                  ? 'var(--color-accent)'
                  : 'var(--color-line)',
          }}
        />
      ))}
    </div>
  )
}
