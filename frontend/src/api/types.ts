// Mirrors app/schemas/* and app/models/enums.py on the backend.

export type UserRole = 'student' | 'instructor' | 'admin'
export type CourseStatus = 'draft' | 'publishing' | 'ready' | 'archived'
export type AssetType = 'text' | 'video' | 'pdf' | 'link'
export type EnrollmentStatus = 'active' | 'completed' | 'cancelled'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface Token {
  access_token: string
  token_type: string
}

export interface Asset {
  id: string
  title: string
  type: AssetType
  content: string | null
  url: string | null
  order_index: number
}

export interface Module {
  id: string
  title: string
  order_index: number
  assets: Asset[]
}

export interface Course {
  id: string
  title: string
  description: string | null
  instructor_id: string
  status: CourseStatus
  enrollment_limit: number | null
  created_at: string
  updated_at: string
  modules: Module[]
}

export interface Progress {
  total_assets: number
  completed_assets: number
  percent_complete: number
  last_activity_at: string | null
}

export interface Certificate {
  id: string
  serial: string
  issued_at: string
}

export interface Enrollment {
  id: string
  student_id: string
  course_id: string
  status: EnrollmentStatus
  completed_at: string | null
  created_at: string
  progress: Progress | null
  certificate: Certificate | null
}

// ── Request payloads ────────────────────────────────────────────────────────
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  full_name: string
  password: string
  role: UserRole
}

export interface AssetCreate {
  title: string
  type: AssetType
  content?: string | null
  url?: string | null
  order_index?: number
}

export interface AssetUpdate {
  title?: string
  type?: AssetType
  content?: string | null
  url?: string | null
  order_index?: number
}

export interface ModuleCreate {
  title: string
  order_index?: number
  assets?: AssetCreate[]
}

export interface ModuleUpdate {
  title?: string
  order_index?: number
}

export interface CourseCreate {
  title: string
  description?: string | null
  enrollment_limit?: number | null
  prerequisite_ids?: string[]
  modules?: ModuleCreate[]
}

export interface CourseUpdate {
  title?: string
  description?: string | null
  enrollment_limit?: number | null
  prerequisite_ids?: string[]
}
