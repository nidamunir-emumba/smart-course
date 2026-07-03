import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <p className="eyebrow mb-2">404</p>
      <h1 className="mb-4 font-display text-3xl font-bold text-ink">Page not found</h1>
      <Link to="/" className="btn btn-primary">
        Back to catalog
      </Link>
    </div>
  )
}
