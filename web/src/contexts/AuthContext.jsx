import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi } from '../services/api'
import toast from 'react-hot-toast'

const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Check if user is authenticated on mount
  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      // Verify token and get user info
      fetchUser()
    } else {
      setLoading(false)
    }
  }, [])

  const fetchUser = async () => {
    try {
      const response = await authApi.me()
      setUser(response.data)
      setIsAuthenticated(true)
    } catch (error) {
      // Token is invalid or expired
      console.error('Failed to fetch user:', error)
      logout()
    } finally {
      setLoading(false)
    }
  }

  const login = async (username, password) => {
    try {
      const response = await authApi.login({ username, password })
      const { access_token, refresh_token } = response.data

      // Store tokens
      localStorage.setItem('auth_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      // Fetch user info
      await fetchUser()

      toast.success('Login successful!')
      return true
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed'
      toast.error(message)
      return false
    }
  }

  const logout = useCallback(() => {
    // Clear tokens
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')

    // Clear user state
    setUser(null)
    setIsAuthenticated(false)

    toast.success('Logged out successfully')
  }, [])

  const hasRole = useCallback(
    (role) => {
      if (!user) return false
      return user.role === role
    },
    [user]
  )

  const hasAnyRole = useCallback(
    (...roles) => {
      if (!user) return false
      return roles.includes(user.role)
    },
    [user]
  )

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    hasRole,
    hasAnyRole,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
