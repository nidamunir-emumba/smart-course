import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../api/endpoints'
import type { AppNotification } from '../api/types'

// Relative timestamps for the feed ("3m ago"); falls back to a date for old items.
function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  if (s < 7 * 86400) return `${Math.floor(s / 86400)}d ago`
  return new Date(iso).toLocaleDateString()
}

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  const countQuery = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: notificationsApi.unreadCount,
    refetchInterval: 30_000, // poll — no websocket channel yet
  })
  const listQuery = useQuery({
    queryKey: ['notifications', 'list'],
    queryFn: () => notificationsApi.list(),
    enabled: open, // fetch the feed only when the panel opens
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['notifications'] })

  const markRead = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: invalidate,
  })
  const markAllRead = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: invalidate,
  })

  // Opening the panel fetches the list fresh; refetch the badge alongside so
  // the two can never disagree on screen (the badge otherwise polls at 30s).
  useEffect(() => {
    if (open) {
      queryClient.invalidateQueries({ queryKey: ['notifications', 'unread'] })
    }
  }, [open, queryClient])

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return
    function onPointerDown(e: PointerEvent) {
      if (!panelRef.current?.contains(e.target as Node)) setOpen(false)
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const unread = countQuery.data?.unread ?? 0

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-expanded={open}
        className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-surface text-muted transition-colors hover:text-ink"
        onClick={() => setOpen((v) => !v)}
      >
        {/* Bell, drawn in the same 2px stroke as the brand mark. */}
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M6 9a6 6 0 1 1 12 0c0 4 1.5 5.5 2 6.5H4c.5-1 2-2.5 2-6.5Z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <path d="M10 19a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-primary px-1 font-mono text-[0.62rem] font-medium text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="card absolute right-0 top-11 z-20 w-80 overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <span className="eyebrow">Notifications</span>
            {unread > 0 && (
              <button
                type="button"
                className="font-mono text-xs text-primary hover:underline"
                onClick={() => markAllRead.mutate()}
              >
                mark all read
              </button>
            )}
          </div>

          {listQuery.isLoading ? (
            <p className="px-4 py-6 text-center text-sm text-muted">Loading…</p>
          ) : listQuery.data && listQuery.data.length > 0 ? (
            <ul className="max-h-96 divide-y divide-line overflow-y-auto">
              {listQuery.data.map((n) => (
                <NotificationRow
                  key={n.id}
                  notification={n}
                  onOpen={() => {
                    if (!n.read_at) markRead.mutate(n.id)
                    setOpen(false)
                  }}
                />
              ))}
            </ul>
          ) : (
            <p className="px-4 py-6 text-center text-sm text-muted">
              Nothing yet — enrollment and course updates land here.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function NotificationRow({
  notification: n,
  onOpen,
}: {
  notification: AppNotification
  onOpen: () => void
}) {
  const inner = (
    <>
      <span
        className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
        style={{ background: n.read_at ? 'transparent' : 'var(--color-primary)' }}
        aria-hidden
      />
      <span className="min-w-0">
        <span className={`block text-sm leading-snug ${n.read_at ? 'text-muted' : 'font-medium text-ink'}`}>
          {n.title}
        </span>
        <span className="mt-0.5 line-clamp-2 block text-xs text-faint">{n.body}</span>
        <span className="mt-1 block font-mono text-[0.65rem] text-faint">
          {timeAgo(n.created_at)}
        </span>
      </span>
    </>
  )
  const cls = 'flex w-full gap-2.5 px-4 py-3 text-left transition-colors hover:bg-paper/60'

  return (
    <li>
      {n.link ? (
        <Link to={n.link} className={cls} onClick={onOpen}>
          {inner}
        </Link>
      ) : (
        <button type="button" className={cls} onClick={onOpen}>
          {inner}
        </button>
      )}
    </li>
  )
}
