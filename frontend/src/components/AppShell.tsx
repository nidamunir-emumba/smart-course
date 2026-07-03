import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

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
          <NavLink to="/" className="flex items-baseline gap-2">
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
              <NavLink to="/dashboard" className={navClass}>
                My Learning
              </NavLink>
            )}
            {user?.role === 'instructor' && (
              <NavLink to="/instructor" className={navClass}>
                My Courses
              </NavLink>
            )}
            <span
              className="cursor-not-allowed px-3 py-1.5 font-display text-sm font-medium text-faint"
              title="AI assistant — not available yet (backend endpoint is stubbed)"
            >
              Assistant · soon
            </span>
          </nav>

          <div className="ml-auto flex items-center gap-3">
            {user ? (
              <>
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
