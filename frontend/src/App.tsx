import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { RequireAuth } from './auth/RequireAuth'
import { Catalog } from './pages/Catalog'
import { Paths } from './pages/Paths'
import { CourseDetail } from './pages/CourseDetail'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { NotFound } from './pages/NotFound'
import { Dashboard } from './pages/student/Dashboard'
import { CertificatePage } from './pages/student/CertificatePage'
import { MyCourses } from './pages/instructor/MyCourses'
import { CourseForm } from './pages/instructor/CourseForm'
import { CourseEditor } from './pages/instructor/CourseEditor'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Catalog />} />
        <Route
          path="paths"
          element={
            <RequireAuth>
              <Paths />
            </RequireAuth>
          }
        />
        <Route
          path="courses/:courseId"
          element={
            <RequireAuth>
              <CourseDetail />
            </RequireAuth>
          }
        />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />

        {/* Student */}
        <Route
          path="dashboard"
          element={
            <RequireAuth roles={['student']}>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="certificate/:enrollmentId"
          element={
            <RequireAuth roles={['student']}>
              <CertificatePage />
            </RequireAuth>
          }
        />

        {/* Instructor */}
        <Route
          path="instructor"
          element={
            <RequireAuth roles={['instructor']}>
              <MyCourses />
            </RequireAuth>
          }
        />
        <Route
          path="instructor/new"
          element={
            <RequireAuth roles={['instructor']}>
              <CourseForm />
            </RequireAuth>
          }
        />
        <Route
          path="instructor/courses/:courseId"
          element={
            <RequireAuth roles={['instructor']}>
              <CourseEditor />
            </RequireAuth>
          }
        />

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
