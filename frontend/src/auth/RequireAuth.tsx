import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './AuthContext'
import type { UserRole } from '../api/types'
import { Spinner } from '../components/Feedback'

interface Props {
  children: ReactNode
  roles?: UserRole[] // if set, user.role must be one of these
}

/** Gate a route on authentication (and optionally role). */
export function RequireAuth({ children, roles }: Props) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <Spinner label="Loading session…" />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />

  return <>{children}</>
}
