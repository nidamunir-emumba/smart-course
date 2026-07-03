import {
  createContext,
  use,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { authApi, usersApi } from '../api/endpoints'
import { clearToken, getToken, setToken, UNAUTHORIZED_EVENT } from '../api/client'
import type { RegisterRequest, User } from '../api/types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (payload: RegisterRequest) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Bootstrap: if a token is present, resolve the current user.
  useEffect(() => {
    let active = true
    if (!getToken()) {
      setLoading(false)
      return
    }
    authApi
      .me()
      .then((u) => active && setUser(u))
      .catch(() => {
        clearToken()
        if (active) setUser(null)
      })
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  // A 401 anywhere clears the session.
  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const token = await authApi.login({ email, password })
    setToken(token.access_token)
    setUser(await authApi.me())
  }, [])

  const register = useCallback(
    async (payload: RegisterRequest) => {
      await usersApi.register(payload)
      await login(payload.email, payload.password)
    },
    [login],
  )

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch {
      /* logout is best-effort; token is discarded regardless */
    }
    clearToken()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}

export function useAuth(): AuthContextValue {
  const ctx = use(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
