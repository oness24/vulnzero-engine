import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

/**
 * ProtectedRoute component
 *
 * Redirects to login if user is not authenticated
 * Optionally checks for required roles
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children - Child components to render if authorized
 * @param {string|string[]} props.roles - Required role(s) for access
 */
function ProtectedRoute({ children, roles = null }) {
  const { isAuthenticated, loading, user } = useAuth()
  const location = useLocation()

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <div className="min-h-screen bg-cyber-darker flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-500"></div>
          <p className="mt-4 text-gray-400">Loading...</p>
        </div>
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Check role-based access control
  if (roles) {
    const requiredRoles = Array.isArray(roles) ? roles : [roles]
    const hasRequiredRole = requiredRoles.includes(user?.role) || user?.is_superuser

    if (!hasRequiredRole) {
      return (
        <div className="min-h-screen bg-cyber-darker flex items-center justify-center p-4">
          <div className="glass-card p-8 max-w-md w-full text-center">
            <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-red-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Access Denied</h2>
            <p className="text-gray-400 mb-6">
              You don't have permission to access this resource.
            </p>
            <p className="text-sm text-gray-500">
              Required role(s): <span className="text-cyan-500">{requiredRoles.join(', ')}</span>
              <br />
              Your role: <span className="text-gray-400">{user?.role}</span>
            </p>
          </div>
        </div>
      )
    }
  }

  // Render children if authenticated and authorized
  return children
}

export default ProtectedRoute
