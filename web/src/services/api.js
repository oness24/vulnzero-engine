/**
 * API Service Layer for VulnZero Frontend
 *
 * Centralized API client with:
 * - Request/response interceptors
 * - Authentication token handling
 * - Error handling and retries
 * - Request/response logging
 */

import axios from 'axios'
import toast from 'react-hot-toast'
import { logger } from '../utils/logger'

// API Base URL from environment variable or default to localhost
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - Add auth token to all requests
apiClient.interceptors.request.use(
  (config) => {
    // Get auth token from localStorage
    const token = localStorage.getItem('auth_token')

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Add request ID for tracing
    config.headers['X-Request-ID'] = generateRequestId()

    // Log request
    logger.apiRequest(config.method || 'GET', config.url, config.params || config.data)

    return config
  },
  (error) => {
    logger.error('Request interceptor error', error)
    return Promise.reject(error)
  }
)

// Response interceptor - Handle errors globally
apiClient.interceptors.response.use(
  (response) => {
    // Log response
    logger.apiResponse(response.config.method || 'GET', response.config.url, response.data)
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // Log error
    logger.apiError(
      originalRequest?.method || 'GET',
      originalRequest?.url || 'unknown',
      error.response?.status || 0,
      error.response?.data
    )

    // Handle 401 Unauthorized - Token expired
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // Try to refresh token
        const refreshToken = localStorage.getItem('refresh_token')

        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const { access_token } = response.data

          // Save new token
          localStorage.setItem('auth_token', access_token)

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed - redirect to login
        localStorage.removeItem('auth_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      toast.error('Access denied. You do not have permission to perform this action.')
    }

    // Handle 404 Not Found
    if (error.response?.status === 404) {
      toast.error('Resource not found')
    }

    // Handle 429 Rate Limited
    if (error.response?.status === 429) {
      toast.error('Too many requests. Please slow down.')
    }

    // Handle 500 Server Error
    if (error.response?.status >= 500) {
      toast.error('Server error. Please try again later.')
    }

    // Handle network errors
    if (!error.response) {
      toast.error('Network error. Please check your connection.')
    }

    return Promise.reject(error)
  }
)

// Helper: Generate unique request ID
function generateRequestId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

// API Methods

/**
 * Vulnerabilities API
 */
export const vulnerabilitiesApi = {
  /**
   * List all vulnerabilities with optional filters
   * @param {Object} params - Query parameters (severity, status, page, limit)
   */
  list: (params = {}) => apiClient.get('/api/vulnerabilities/', { params }),

  /**
   * Get a single vulnerability by ID
   * @param {string|number} id - Vulnerability ID
   */
  get: (id) => apiClient.get(`/api/vulnerabilities/${id}`),

  /**
   * Create a new vulnerability
   * @param {Object} data - Vulnerability data
   */
  create: (data) => apiClient.post('/api/vulnerabilities/', data),

  /**
   * Update a vulnerability
   * @param {string|number} id - Vulnerability ID
   * @param {Object} data - Updated data
   */
  update: (id, data) => apiClient.patch(`/api/vulnerabilities/${id}`, data),

  /**
   * Delete a vulnerability
   * @param {string|number} id - Vulnerability ID
   */
  delete: (id) => apiClient.delete(`/api/vulnerabilities/${id}`),

  /**
   * Mark vulnerability as false positive
   * @param {string|number} id - Vulnerability ID
   */
  markFalsePositive: (id) => apiClient.post(`/api/vulnerabilities/${id}/false-positive`),
}

/**
 * Patches API
 */
export const patchesApi = {
  /**
   * List all patches with optional filters
   * @param {Object} params - Query parameters (status, vulnerability_id, page, limit)
   */
  list: (params = {}) => apiClient.get('/api/patches/', { params }),

  /**
   * Get a single patch by ID
   * @param {string|number} id - Patch ID
   */
  get: (id) => apiClient.get(`/api/patches/${id}`),

  /**
   * Generate a new patch for a vulnerability
   * @param {Object} data - { vulnerability_id, patch_type }
   */
  generate: (data) => apiClient.post('/api/patches/generate', data),

  /**
   * Approve a patch
   * @param {string|number} id - Patch ID
   */
  approve: (id) => apiClient.post(`/api/patches/${id}/approve`),

  /**
   * Reject a patch
   * @param {string|number} id - Patch ID
   * @param {string} reason - Rejection reason
   */
  reject: (id, reason) => apiClient.post(`/api/patches/${id}/reject`, { reason }),

  /**
   * Test a patch in digital twin
   * @param {string|number} id - Patch ID
   */
  test: (id) => apiClient.post(`/api/patches/${id}/test`),
}

/**
 * Deployments API
 */
export const deploymentsApi = {
  /**
   * List all deployments with optional filters
   * @param {Object} params - Query parameters (status, environment, page, limit)
   */
  list: (params = {}) => apiClient.get('/api/deployments/', { params }),

  /**
   * Get a single deployment by ID
   * @param {string|number} id - Deployment ID
   */
  get: (id) => apiClient.get(`/api/deployments/${id}`),

  /**
   * Create a new deployment
   * @param {Object} data - { patch_id, strategy, target_environment }
   */
  create: (data) => apiClient.post('/api/deployments/', data),

  /**
   * Get deployment status
   * @param {string|number} id - Deployment ID
   */
  status: (id) => apiClient.get(`/api/deployments/${id}/status`),

  /**
   * Rollback a deployment
   * @param {string|number} id - Deployment ID
   */
  rollback: (id) => apiClient.post(`/api/deployments/${id}/rollback`),

  /**
   * Pause a deployment
   * @param {string|number} id - Deployment ID
   */
  pause: (id) => apiClient.post(`/api/deployments/${id}/pause`),

  /**
   * Resume a deployment
   * @param {string|number} id - Deployment ID
   */
  resume: (id) => apiClient.post(`/api/deployments/${id}/resume`),
}

/**
 * Monitoring API
 */
export const monitoringApi = {
  /**
   * Get system health status
   */
  health: () => apiClient.get('/health'),

  /**
   * Get system metrics
   */
  metrics: () => apiClient.get('/api/monitoring/metrics'),

  /**
   * Get alerts
   * @param {Object} params - Query parameters (severity, acknowledged, page, limit)
   */
  alerts: (params = {}) => apiClient.get('/api/monitoring/alerts', { params }),

  /**
   * Acknowledge an alert
   * @param {string|number} id - Alert ID
   */
  acknowledgeAlert: (id) => apiClient.post(`/api/monitoring/alerts/${id}/acknowledge`),

  /**
   * Get deployment analytics
   * @param {Object} params - Query parameters (start_date, end_date)
   */
  analytics: (params = {}) => apiClient.get('/api/monitoring/analytics', { params }),
}

/**
 * Dashboard API
 */
export const dashboardApi = {
  /**
   * Get dashboard statistics
   */
  stats: () => apiClient.get('/api/dashboard/stats'),

  /**
   * Get recent activity
   * @param {number} limit - Number of items to return
   */
  recentActivity: (limit = 10) => apiClient.get('/api/dashboard/activity', { params: { limit } }),

  /**
   * Get vulnerability trends
   * @param {string} period - Time period (day, week, month)
   */
  trends: (period = 'week') => apiClient.get('/api/dashboard/trends', { params: { period } }),
}

/**
 * Settings/Configuration API
 */
export const settingsApi = {
  /**
   * Get user settings
   */
  get: () => apiClient.get('/api/settings'),

  /**
   * Update user settings
   * @param {Object} data - Settings data
   */
  update: (data) => apiClient.patch('/api/settings', data),

  /**
   * Get integrations
   */
  integrations: () => apiClient.get('/api/settings/integrations'),

  /**
   * Update integration
   * @param {string} name - Integration name
   * @param {Object} config - Integration configuration
   */
  updateIntegration: (name, config) => apiClient.patch(`/api/settings/integrations/${name}`, config),

  /**
   * Test integration connection
   * @param {string} name - Integration name
   */
  testIntegration: (name) => apiClient.post(`/api/settings/integrations/${name}/test`),
}

/**
 * Authentication API
 */
export const authApi = {
  /**
   * Login
   * @param {Object} credentials - { username, password }
   */
  login: (credentials) => apiClient.post('/api/auth/login', credentials),

  /**
   * Logout
   */
  logout: () => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    return Promise.resolve()
  },

  /**
   * Refresh token
   * @param {string} refreshToken - Refresh token
   */
  refresh: (refreshToken) => apiClient.post('/api/auth/refresh', { refresh_token: refreshToken }),

  /**
   * Get current user
   */
  me: () => apiClient.get('/api/auth/me'),

  /**
   * Register new user (Admin only)
   * @param {Object} data - { username, email, password, full_name, role }
   */
  register: (data) => apiClient.post('/api/auth/register', data),

  /**
   * List all users (Admin only)
   * @param {Object} params - Query parameters { skip, limit }
   */
  listUsers: (params = {}) => apiClient.get('/api/auth/users', { params }),

  /**
   * Delete user (Admin only)
   * @param {number} userId - User ID
   */
  deleteUser: (userId) => apiClient.delete(`/api/auth/users/${userId}`),
}

// Export the axios instance for custom requests
export default apiClient
