/** FEN → SVG chess board, drawn in the app's blueprint style.
 *
 * Lessons embed a marker paragraph:
 *   [fen:<FEN>|<caption>]
 * The lesson renderer swaps it for this component. Only the piece-placement
 * and side-to-move fields of the FEN are used.
 */

const GLYPHS: Record<string, string> = {
  K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
  k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
}

const SQ = 46 // square size
const M = 22 // margin for coordinates

const mono = { fontFamily: 'var(--font-mono)' } as const

/** Marker syntax: a paragraph of exactly `[fen:FEN]` or `[fen:FEN|caption]`. */
export const CHESS_MARKER = /^\[fen:([^|\]]+?)(?:\|([^\]]*))?\]$/

export function ChessBoard({ fen, caption }: { fen: string; caption?: string }) {
  const parts = fen.trim().split(/\s+/)
  const placement = parts[0]
  const whiteToMove = (parts[1] ?? 'w') !== 'b'

  // Parse placement into an 8x8 grid (rank 8 first).
  const ranks = placement.split('/')
  if (ranks.length !== 8) return null
  const grid: (string | null)[][] = ranks.map((rank) => {
    const row: (string | null)[] = []
    for (const ch of rank) {
      if (/[1-8]/.test(ch)) row.push(...Array<null>(Number(ch)).fill(null))
      else row.push(ch)
    }
    return row.slice(0, 8)
  })

  const size = SQ * 8
  return (
    <figure className="card my-2 inline-block p-4">
      <svg
        viewBox={`0 0 ${size + M} ${size + M}`}
        width={Math.min(390, size + M)}
        className="h-auto max-w-full"
        role="img"
        aria-label={`Chess position, ${whiteToMove ? 'White' : 'Black'} to move. FEN: ${fen}`}
      >
        {grid.map((row, r) =>
          row.map((piece, f) => {
            const light = (r + f) % 2 === 0
            const x = M + f * SQ
            const y = r * SQ
            return (
              <g key={`${r}-${f}`}>
                <rect
                  x={x}
                  y={y}
                  width={SQ}
                  height={SQ}
                  fill={light ? 'var(--color-surface)' : 'var(--color-line)'}
                />
                {piece && (
                  <text
                    x={x + SQ / 2}
                    y={y + SQ / 2 + 13}
                    textAnchor="middle"
                    fontSize={36}
                    fill={piece === piece.toUpperCase() ? '#ffffff' : 'var(--color-ink)'}
                    stroke="var(--color-ink)"
                    strokeWidth={piece === piece.toUpperCase() ? 1.1 : 0}
                    style={{ paintOrder: 'stroke' }}
                  >
                    {GLYPHS[piece] ?? ''}
                  </text>
                )}
              </g>
            )
          })
        )}
        {/* board frame */}
        <rect x={M} y={0} width={size} height={size} fill="none" stroke="var(--color-muted)" strokeWidth={1.5} />
        {/* coordinates */}
        {Array.from({ length: 8 }, (_, i) => (
          <g key={i}>
            <text x={M - 8} y={i * SQ + SQ / 2 + 3} textAnchor="middle" fontSize={10} fill="var(--color-faint)" style={mono}>
              {8 - i}
            </text>
            <text x={M + i * SQ + SQ / 2} y={size + 14} textAnchor="middle" fontSize={10} fill="var(--color-faint)" style={mono}>
              {'abcdefgh'[i]}
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="mt-2 flex items-center gap-2 font-mono text-xs text-muted">
        <span
          className="inline-block h-3 w-3 rounded-full border"
          style={{
            background: whiteToMove ? '#ffffff' : 'var(--color-ink)',
            borderColor: 'var(--color-ink)',
          }}
          aria-hidden
        />
        {whiteToMove ? 'White to move' : 'Black to move'}
        {caption && <span className="text-faint">· {caption}</span>}
      </figcaption>
    </figure>
  )
}
