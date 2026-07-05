import type { ReactElement } from 'react'

/** Hand-drawn SVG diagrams for lesson content, in the app's blueprint style.
 *
 * Lessons embed a marker paragraph like `[diagram:request-lifecycle]`; the
 * lesson renderer swaps it for the matching component here. Registry at the
 * bottom. Everything uses the design tokens, so diagrams follow the theme.
 */

const INK = 'var(--color-ink)'
const MUTED = 'var(--color-muted)'
const FAINT = 'var(--color-faint)'
const LINE = 'var(--color-line)'
const PRIMARY = 'var(--color-primary)'
const ACCENT = 'var(--color-accent)'
const SURFACE = 'var(--color-surface)'
const SUCCESS = 'var(--color-success)'

const mono = { fontFamily: 'var(--font-mono)' } as const
const sans = { fontFamily: 'var(--font-display)' } as const

function Box({
  x,
  y,
  w,
  h,
  title,
  sub,
  stroke = LINE,
}: {
  x: number
  y: number
  w: number
  h: number
  title: string
  sub?: string
  stroke?: string
}) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={8} fill={SURFACE} stroke={stroke} strokeWidth={1.5} />
      <text x={x + w / 2} y={y + (sub ? h / 2 - 4 : h / 2 + 4)} textAnchor="middle" fontSize={13} fontWeight={600} fill={INK} style={sans}>
        {title}
      </text>
      {sub && (
        <text x={x + w / 2} y={y + h / 2 + 14} textAnchor="middle" fontSize={10} fill={FAINT} style={mono}>
          {sub}
        </text>
      )}
    </g>
  )
}

function Arrow({
  id,
  d,
  label,
  labelX,
  labelY,
  color = PRIMARY,
  dashed = false,
}: {
  id: string
  d: string
  label?: string
  labelX?: number
  labelY?: number
  color?: string
  dashed?: boolean
}) {
  return (
    <g>
      <defs>
        <marker id={id} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
          <path d="M0,0 L7,3.5 L0,7 Z" fill={color} />
        </marker>
      </defs>
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeDasharray={dashed ? '4 4' : undefined}
        markerEnd={`url(#${id})`}
      />
      {label && (
        <text x={labelX} y={labelY} fontSize={10} fill={MUTED} style={mono}>
          {label}
        </text>
      )}
    </g>
  )
}

/** Course 1 · The life of a request: two network hops, one Python process. */
function RequestLifecycle() {
  return (
    <svg viewBox="0 0 720 560" className="h-auto w-full" role="img"
      aria-label="A request travels from the browser into one Python process (FastAPI, service layer, SQLAlchemy as layers), out to PostgreSQL, and back.">
      {/* Browser */}
      <Box x={230} y={16} w={260} h={54} title="Your browser" sub="React + fetch" stroke={PRIMARY} />

      {/* hop 1 down */}
      <Arrow id="rl-a1" d="M310,70 L310,120" label="GET /api/v1/… + JWT" labelX={40} labelY={100} />
      <text x={40} y={114} fontSize={10} fill={ACCENT} style={mono}>network hop #1</text>

      {/* One Python process boundary */}
      <rect x={120} y={120} width={480} height={272} rx={12} fill="none" stroke={PRIMARY} strokeWidth={1.5} strokeDasharray="6 5" />
      <text x={136} y={144} fontSize={10} fill={PRIMARY} style={mono}>ONE PYTHON PROCESS · PORT 8000</text>

      <Box x={230} y={158} w={260} h={54} title="FastAPI" sub="verify token · validate body" />
      <Arrow id="rl-a2" d="M310,212 L310,240" label="function call · nanoseconds" labelX={330} labelY={230} color={MUTED} />
      <Box x={230} y={240} w={260} h={54} title="Service layer" sub="the business rules" />
      <Arrow id="rl-a3" d="M310,294 L310,322" label="function call" labelX={330} labelY={312} color={MUTED} />
      <Box x={230} y={322} w={260} h={54} title="SQLAlchemy" sub="Python query → SQL text" />

      {/* hop 2 down */}
      <Arrow id="rl-a4" d="M310,376 L310,436" label="SELECT … WHERE id = …" labelX={40} labelY={408} />
      <text x={40} y={422} fontSize={10} fill={ACCENT} style={mono}>network hop #2</text>

      {/* Postgres */}
      <Box x={230} y={436} w={260} h={54} title="PostgreSQL" sub="port 5432 · the disk that remembers" stroke={PRIMARY} />

      {/* return path, right side, amber */}
      <Arrow id="rl-r1" d="M490,463 L560,463 L560,349 L496,349" color={ACCENT} label="rows" labelX={568} labelY={420} />
      <Arrow id="rl-r2" d="M490,185 L560,185 L560,43 L496,43" color={ACCENT} label="200 OK · JSON" labelX={568} labelY={120} />
      <text x={568} y={434} fontSize={10} fill={FAINT} style={mono}>back up the</text>
      <text x={568} y={446} fontSize={10} fill={FAINT} style={mono}>same layers</text>

      {/* footer note */}
      <text x={360} y={540} textAnchor="middle" fontSize={11} fill={MUTED} style={mono}>
        everything inside the dashed box = function calls, not network
      </text>
    </svg>
  )
}

/** Course 2 · The system map: live core + phase-2 services. */
function SystemMap() {
  return (
    <svg viewBox="0 0 720 470" className="h-auto w-full" role="img"
      aria-label="System map: React talks to FastAPI; FastAPI uses PostgreSQL and Redis, and queues jobs on RabbitMQ for the Celery worker. Temporal, Kafka, Qdrant and Mongo are provisioned for phase 2.">
      <Box x={40} y={24} w={200} h={54} title="React SPA" sub="Vite · port 5173" stroke={PRIMARY} />
      <Arrow id="sm-a1" d="M140,78 L140,124" label="HTTP + JWT" labelX={152} labelY={106} />
      <Box x={40} y={124} w={200} h={54} title="FastAPI" sub="port 8000 · answers in ms" stroke={PRIMARY} />

      {/* Postgres + Redis */}
      <Arrow id="sm-a2" d="M100,178 L100,232" label="SQL" labelX={64} labelY={210} />
      <Box x={40} y={232} w={130} h={50} title="PostgreSQL" sub="source of truth" />
      <Arrow id="sm-a3" d="M195,178 L195,232" label="cache" labelX={205} labelY={210} />
      <Box x={185} y={232} w={100} h={50} title="Redis" sub="fast · ephemeral" />

      {/* queue path */}
      <Arrow id="sm-a4" d="M240,151 L330,151" label="enqueue task" labelX={246} labelY={143} />
      <Box x={330} y={124} w={140} h={54} title="RabbitMQ" sub="the post office" />
      <Arrow id="sm-a5" d="M400,178 L400,232" label="deliver" labelX={410} labelY={210} />
      <Box x={330} y={232} w={140} h={54} title="Celery worker" sub="slow work lives here" />
      <Arrow id="sm-a6" d="M400,286 L400,330" color={ACCENT} label="✉ email" labelX={410} labelY={314} />

      {/* Phase 2 cluster */}
      <rect x={510} y={100} width={186} height={250} rx={12} fill="none" stroke={FAINT} strokeWidth={1.5} strokeDasharray="6 5" />
      <text x={526} y={124} fontSize={10} fill={FAINT} style={mono}>PHASE 2 · PROVISIONED</text>
      <Box x={526} y={138} w={154} h={44} title="Temporal" sub="durable workflows" />
      <Box x={526} y={192} w={154} h={44} title="Kafka" sub="event backbone" />
      <Box x={526} y={246} w={154} h={44} title="Qdrant + LLM" sub="RAG assistant" />
      <Box x={526} y={300} w={154} h={40} title="MongoDB" sub="content documents" />

      {/* observability strip */}
      <line x1={40} y1={396} x2={696} y2={396} stroke={LINE} strokeWidth={1} />
      <text x={40} y={420} fontSize={10} fill={FAINT} style={mono}>
        watching everything: OpenTelemetry → Jaeger (traces) · Prometheus → Grafana (metrics)
      </text>
      <text x={40} y={444} fontSize={10} fill={MUTED} style={mono}>
        rule of the map: each kind of work goes to the tool shaped for it
      </text>
    </svg>
  )
}

/** Course 2 · Why the API never sends your email. */
function BackgroundJobs() {
  return (
    <svg viewBox="0 0 720 320" className="h-auto w-full" role="img"
      aria-label="Registration returns in milliseconds after queueing the email job; a Celery worker sends the email seconds later, and nobody waits on it.">
      <Box x={24} y={40} w={150} h={54} title="Browser" sub="clicks Register" stroke={PRIMARY} />
      <Arrow id="bj-a1" d="M174,67 L246,67" label="POST /users" labelX={180} labelY={59} />
      <Box x={246} y={40} w={170} h={54} title="FastAPI" sub="INSERT user + bell row" stroke={PRIMARY} />
      <Arrow id="bj-a2" d="M416,67 L488,67" label="queue job" labelX={424} labelY={59} />
      <Box x={488} y={40} w={150} h={54} title="RabbitMQ" sub="job parks here safely" />

      {/* the fast path back */}
      <Arrow id="bj-a3" d="M331,94 L331,140 L99,140 L99,100" color={SUCCESS} label="201 Created — ~20 ms total" labelX={130} labelY={132} />
      <text x={130} y={156} fontSize={10} fill={SUCCESS} style={mono}>the ONLY thing the user waits for</text>

      {/* the slow path, later */}
      <Arrow id="bj-a4" d="M563,94 L563,208" dashed label="…milliseconds later" labelX={575} labelY={150} color={MUTED} />
      <Box x={488} y={208} w={150} h={54} title="Celery worker" sub="separate process" />
      <Arrow id="bj-a5" d="M563,262 L563,296" color={ACCENT} label="✉ SMTP · ~3 s · retries ×3" labelX={330} labelY={284} />
      <text x={330} y={300} fontSize={10} fill={FAINT} style={mono}>nobody is waiting on this</text>

      {/* contract note */}
      <text x={24} y={230} fontSize={11} fill={MUTED} style={mono}>the contract:</text>
      <text x={24} y={248} fontSize={11} fill={MUTED} style={mono}>essential work → in the request</text>
      <text x={24} y={266} fontSize={11} fill={MUTED} style={mono}>side effects → on the queue</text>
    </svg>
  )
}

/** Docker course · one computer, many boxes. */
function DockerOneComputer() {
  const boxes = [
    ['api', 'the app'],
    ['postgres', 'saves data'],
    ['redis', 'fast memory'],
    ['rabbitmq', 'to-do list'],
  ]
  return (
    <svg viewBox="0 0 720 250" className="h-auto w-full" role="img"
      aria-label="One computer runs many small boxes side by side: api, postgres, redis, rabbitmq. Each box holds one program.">
      <rect x={16} y={40} width={688} height={160} rx={12} fill="none" stroke={PRIMARY} strokeWidth={1.5} />
      <text x={32} y={30} fontSize={13} fontWeight={600} fill={INK} style={sans}>Your computer</text>
      {boxes.map(([t, s], i) => (
        <Box key={t} x={40 + i * 165} y={80} w={140} h={80} title={t} sub={s} />
      ))}
      <text x={360} y={230} textAnchor="middle" fontSize={12} fill={MUTED} style={mono}>
        one computer, many boxes. each box holds one program.
      </text>
    </svg>
  )
}

/** Docker course · one file lists all the boxes. */
function DockerOneFile() {
  return (
    <svg viewBox="0 0 720 300" className="h-auto w-full" role="img"
      aria-label="One file, docker-compose.yml, lists every box. One command starts them all.">
      {/* the file */}
      <rect x={30} y={40} width={230} height={190} rx={8} fill={SURFACE} stroke={LINE} strokeWidth={1.5} />
      <text x={48} y={68} fontSize={12} fontWeight={600} fill={INK} style={mono}>docker-compose.yml</text>
      {['- api', '- postgres', '- redis', '- rabbitmq'].map((line, i) => (
        <text key={line} x={48} y={100 + i * 26} fontSize={13} fill={MUTED} style={mono}>{line}</text>
      ))}
      <text x={48} y={214} fontSize={11} fill={FAINT} style={mono}>the list of boxes</text>

      <Arrow id="dof-a" d="M270,135 L360,135" color={PRIMARY} label="make up" labelX={278} labelY={126} />

      {/* the running boxes */}
      {['api', 'postgres', 'redis', 'rabbitmq'].map((t, i) => (
        <Box key={t} x={380} y={44 + i * 52} w={300} h={42} title={t} />
      ))}
      <text x={360} y={288} textAnchor="middle" fontSize={12} fill={MUTED} style={mono}>
        one file lists every box. one command starts them all.
      </text>
    </svg>
  )
}

/** Docker course · same thing, two names. */
function DockerTwoNames() {
  return (
    <svg viewBox="0 0 720 300" className="h-auto w-full" role="img"
      aria-label="The same database has two names. From your laptop it is localhost:5432. From inside a Docker box it is postgres:5432.">
      <Box x={470} y={110} w={210} h={72} title="postgres" sub="the database" stroke={PRIMARY} />

      <Box x={40} y={40} w={230} h={56} title="You, on your laptop" />
      <Arrow id="dtn-a1" d="M270,68 L470,132" color={PRIMARY} label="localhost:5432" labelX={286} labelY={92} />

      <Box x={40} y={196} w={230} h={56} title="A box, inside Docker" />
      <Arrow id="dtn-a2" d="M270,224 L470,160" color={ACCENT} label="postgres:5432" labelX={286} labelY={220} />

      <text x={360} y={290} textAnchor="middle" fontSize={12} fill={MUTED} style={mono}>
        same database. two names. the name depends on where you stand.
      </text>
    </svg>
  )
}

const DIAGRAMS: Record<string, () => ReactElement> = {
  'request-lifecycle': RequestLifecycle,
  'system-map': SystemMap,
  'background-jobs': BackgroundJobs,
  'docker-one-computer': DockerOneComputer,
  'docker-one-file': DockerOneFile,
  'docker-two-names': DockerTwoNames,
}

/** Marker syntax used inside lesson text: a paragraph of exactly `[diagram:name]`. */
export const DIAGRAM_MARKER = /^\[diagram:([a-z0-9-]+)\]$/

export function LessonDiagram({ name }: { name: string }) {
  const Diagram = DIAGRAMS[name]
  if (!Diagram) return null // unknown marker → render nothing rather than break the lesson
  return (
    <figure className="card my-2 max-w-2xl p-4">
      <Diagram />
    </figure>
  )
}
