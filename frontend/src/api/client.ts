// Typed fetch wrapper for the SmartCourse REST API.
// - prepends the API base path (VITE_API_BASE_URL, proxied to :8000 in dev)
// - attaches the JWT bearer token
// - normalizes errors into ApiError (carrying the backend's `detail`)
// - on 401, clears the token and broadcasts so the app can redirect to login

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const TOKEN_KEY = 'smartcourse.token'

export const UNAUTHORIZED_EVENT = 'smartcourse:unauthorized'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  auth?: boolean // default true
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true } = options
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const token = getToken()
  if (auth && token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Network error — is the API running on :8000?')
  }

  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    throw new ApiError(401, 'Your session has expired. Please sign in again.')
  }

  if (!res.ok) {
    throw new ApiError(res.status, await extractDetail(res))
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

async function extractDetail(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') return data.detail
    // FastAPI validation errors: detail is an array of {msg, loc}.
    if (Array.isArray(data?.detail)) {
      return data.detail.map((e: { msg?: string }) => e.msg).filter(Boolean).join('; ')
    }
  } catch {
    /* fall through */
  }
  return `Request failed (${res.status})`
}

export const api = {
  get: <T>(path: string, auth = true) => request<T>(path, { method: 'GET', auth }),
  post: <T>(path: string, body?: unknown, auth = true) =>
    request<T>(path, { method: 'POST', body, auth }),
  patch: <T>(path: string, body?: unknown, auth = true) =>
    request<T>(path, { method: 'PATCH', body, auth }),
  del: <T>(path: string, auth = true) => request<T>(path, { method: 'DELETE', auth }),
}
