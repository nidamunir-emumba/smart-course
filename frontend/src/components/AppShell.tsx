import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { NotificationBell } from './NotificationBell'

function navClass({ isActive }: { isActive: boolean }): string {
  return [
    'font-display text-sm font-medium px-3 py-1.5 rounded-lg transition-colors',
    isActive ? 'bg-primary/8 text-primary' : 'text-muted hover:text-ink',
  ].join(' ')
}

export function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-line bg-paper/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-5 py-3">
          <NavLink to="/" className="flex items-center gap-2">
            {/* Brand mark: the rising arc in miniature, echoing the hero figure. */}
            <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden className="shrink-0">
              <path
                d="M3 17 C7 17 11 15 14 8"
                fill="none"
                stroke="var(--color-primary)"
                strokeWidth={2}
                strokeLinecap="round"
              />
              <circle cx="17" cy="6" r="3.5" fill="var(--color-accent-soft)" stroke="var(--color-accent)" strokeWidth={2} />
            </svg>
            <span className="font-display text-xl font-bold tracking-tight text-ink">
              SmartCourse
            </span>
            <span className="eyebrow hidden sm:inline">/ learning platform</span>
          </NavLink>

          <nav className="ml-4 flex items-center gap-1">
            <NavLink to="/" end className={navClass}>
              Catalog
            </NavLink>
            {user?.role === 'student' && (
              <Link
                to="/?filter=enrolled"
                className="px-3 py-1.5 font-display text-sm font-medium text-muted transition-colors hover:text-ink"
              >
                Enrolled
              </Link>
            )}
            {user && (
              <NavLink to="/paths" className={navClass}>
                Paths
              </NavLink>
            )}
            {user?.role === 'student' && (
              <NavLink to="/dashboard" className={navClass}>
                My Learning
              </NavLink>
            )}
            {user?.role === 'instructor' && (
              <NavLink to="/instructor" className={navClass}>
                My Courses
              </NavLink>
            )}
            {/* The assistant lives inside lessons — open any text lesson and
                ask about it there. A standalone assistant page arrives with
                the Phase-2 RAG upgrade. */}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            {user ? (
              <>
                <NotificationBell />
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-medium text-ink">{user.full_name}</p>
                  <p className="eyebrow">{user.role}</p>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={handleLogout}>
                  Sign out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className="btn btn-ghost btn-sm">
                  Sign in
                </NavLink>
                <NavLink to="/register" className="btn btn-primary btn-sm">
                  Get started
                </NavLink>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        <Outlet />
      </main>
    </div>
  )
}
