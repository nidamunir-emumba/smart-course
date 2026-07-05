// Typed endpoint functions grouped by resource. Query/mutation hooks in the
// pages compose these with TanStack Query.
import { api } from './client'
import type {
  AppNotification,
  AskRequest,
  AskResponse,
  LearningPathStep,
  Course,
  CourseCreate,
  CourseUpdate,
  Enrollment,
  LoginRequest,
  Module,
  ModuleCreate,
  ModuleUpdate,
  AssetCreate,
  AssetUpdate,
  RegisterRequest,
  Token,
  UnreadCount,
  User,
} from './types'

// ── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (body: LoginRequest) => api.post<Token>('/auth/login', body, false),
  me: () => api.get<User>('/auth/me'),
  logout: () => api.post<void>('/auth/logout'),
}

// ── Users (registration is open / unauthenticated) ──────────────────────────
export const usersApi = {
  register: (body: RegisterRequest) => api.post<User>('/users', body, false),
  get: (id: string) => api.get<User>(`/users/${id}`),
}

// ── Courses + lifecycle ─────────────────────────────────────────────────────
export const coursesApi = {
  list: (limit = 50, offset = 0) =>
    api.get<Course[]>(`/courses?limit=${limit}&offset=${offset}`),
  get: (id: string) => api.get<Course>(`/courses/${id}`),
  path: (id: string) => api.get<LearningPathStep[]>(`/courses/${id}/path`),
  create: (body: CourseCreate) => api.post<Course>('/courses', body),
  update: (id: string, body: CourseUpdate) => api.patch<Course>(`/courses/${id}`, body),
  publish: (id: string) => api.post<Course>(`/courses/${id}/publish`),
  unpublish: (id: string) => api.post<Course>(`/courses/${id}/unpublish`),
  archive: (id: string) => api.post<Course>(`/courses/${id}/archive`),
  remove: (id: string) => api.del<void>(`/courses/${id}`),

  // Content authoring (draft-only on the backend). Each returns the full course.
  addModule: (courseId: string, body: ModuleCreate) =>
    api.post<Course>(`/courses/${courseId}/modules`, body),
  updateModule: (courseId: string, moduleId: string, body: ModuleUpdate) =>
    api.patch<Course>(`/courses/${courseId}/modules/${moduleId}`, body),
  removeModule: (courseId: string, moduleId: string) =>
    api.del<Course>(`/courses/${courseId}/modules/${moduleId}`),
  addAsset: (courseId: string, moduleId: string, body: AssetCreate) =>
    api.post<Course>(`/courses/${courseId}/modules/${moduleId}/assets`, body),
  updateAsset: (courseId: string, moduleId: string, assetId: string, body: AssetUpdate) =>
    api.patch<Course>(`/courses/${courseId}/modules/${moduleId}/assets/${assetId}`, body),
  removeAsset: (courseId: string, moduleId: string, assetId: string) =>
    api.del<Course>(`/courses/${courseId}/modules/${moduleId}/assets/${assetId}`),
}

// Convenience: total asset count across a course's modules.
export function courseAssetCount(course: Pick<Course, 'modules'>): number {
  return course.modules.reduce((n: number, m: Module) => n + m.assets.length, 0)
}

// ── Enrollments + progress ──────────────────────────────────────────────────
export const enrollmentsApi = {
  enroll: (courseId: string) => api.post<Enrollment>('/enrollments', { course_id: courseId }),
  get: (id: string) => api.get<Enrollment>(`/enrollments/${id}`),
  forStudent: (studentId: string) =>
    api.get<Enrollment[]>(`/enrollments/student/${studentId}`),
  setProgress: (id: string, completedAssets: number) =>
    api.post<Enrollment>(`/enrollments/${id}/progress`, { completed_assets: completedAssets }),
  unenroll: (id: string) => api.post<Enrollment>(`/enrollments/${id}/unenroll`),
  archive: (id: string) => api.post<Enrollment>(`/enrollments/${id}/archive`),
  unarchive: (id: string) => api.post<Enrollment>(`/enrollments/${id}/unarchive`),
  completeLesson: (id: string, assetId: string) =>
    api.post<Enrollment>(`/enrollments/${id}/lessons/${assetId}/complete`),
  uncompleteLesson: (id: string, assetId: string) =>
    api.del<Enrollment>(`/enrollments/${id}/lessons/${assetId}/complete`),
}

// ── Notifications ───────────────────────────────────────────────────────────
export const notificationsApi = {
  list: (limit = 20) => api.get<AppNotification[]>(`/notifications?limit=${limit}`),
  unreadCount: () => api.get<UnreadCount>('/notifications/unread-count'),
  markRead: (id: string) => api.post<AppNotification>(`/notifications/${id}/read`),
  markAllRead: () => api.post<UnreadCount>('/notifications/read-all'),
}

// ── AI assistant ────────────────────────────────────────────────────────────
export const assistantApi = {
  ask: (body: AskRequest) => api.post<AskResponse>('/assistant/qa', body),
}
