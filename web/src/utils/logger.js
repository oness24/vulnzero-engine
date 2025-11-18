/**
 * Logger Utility for VulnZero Frontend
 *
 * Provides environment-aware logging with Sentry integration
 * - Development: Logs to console
 * - Production: Optionally sends to Sentry as breadcrumbs
 */

import { addBreadcrumb } from './sentry'

const isDev = import.meta.env.DEV
const isVerbose = import.meta.env.VITE_VERBOSE_LOGGING === 'true'

/**
 * Logger class with multiple log levels
 */
class Logger {
  /**
   * Log debug message (development only)
   * @param {string} message - Log message
   * @param {Object} data - Additional data
   */
  debug(message, data = {}) {
    if (isDev || isVerbose) {
      console.log(`🔍 [DEBUG] ${message}`, data)
    }

    // Add breadcrumb for debugging in Sentry
    if (!isDev) {
      addBreadcrumb(message, data, 'debug')
    }
  }

  /**
   * Log info message
   * @param {string} message - Log message
   * @param {Object} data - Additional data
   */
  info(message, data = {}) {
    if (isDev || isVerbose) {
      console.log(`ℹ️  [INFO] ${message}`, data)
    }

    // Add breadcrumb in production
    if (!isDev) {
      addBreadcrumb(message, data, 'info')
    }
  }

  /**
   * Log warning message
   * @param {string} message - Log message
   * @param {Object} data - Additional data
   */
  warn(message, data = {}) {
    if (isDev || isVerbose) {
      console.warn(`⚠️  [WARN] ${message}`, data)
    }

    // Always add warning breadcrumb
    addBreadcrumb(message, data, 'warning')
  }

  /**
   * Log error message
   * @param {string} message - Log message
   * @param {Error|Object} error - Error object or data
   */
  error(message, error = {}) {
    if (isDev || isVerbose) {
      console.error(`❌ [ERROR] ${message}`, error)
    }

    // Always add error breadcrumb
    addBreadcrumb(message, { error: error.message || error }, 'error')
  }

  /**
   * Log WebSocket event (development and verbose mode only)
   * @param {string} event - Event name
   * @param {Object} data - Event data
   */
  websocket(event, data = {}) {
    if (isDev || isVerbose) {
      const emoji = this._getWebSocketEmoji(event)
      console.log(`${emoji} [WebSocket] ${event}`, data)
    }

    // Add breadcrumb for important WebSocket events
    const importantEvents = ['connect', 'disconnect', 'error', 'reconnect']
    if (importantEvents.includes(event.toLowerCase())) {
      addBreadcrumb(`WebSocket: ${event}`, data, 'websocket')
    }
  }

  /**
   * Log API request (development and verbose mode only)
   * @param {string} method - HTTP method
   * @param {string} url - Request URL
   * @param {Object} data - Request data
   */
  apiRequest(method, url, data = {}) {
    if (isDev || isVerbose) {
      console.log(`🚀 [API Request] ${method.toUpperCase()} ${url}`, data)
    }
  }

  /**
   * Log API response (development and verbose mode only)
   * @param {string} method - HTTP method
   * @param {string} url - Request URL
   * @param {Object} data - Response data
   */
  apiResponse(method, url, data = {}) {
    if (isDev || isVerbose) {
      console.log(`✅ [API Response] ${method.toUpperCase()} ${url}`, data)
    }
  }

  /**
   * Log API error (always logged)
   * @param {string} method - HTTP method
   * @param {string} url - Request URL
   * @param {number} status - HTTP status code
   * @param {Object} error - Error data
   */
  apiError(method, url, status, error = {}) {
    if (isDev || isVerbose) {
      console.error(`❌ [API Error] ${method.toUpperCase()} ${url} - ${status}`, error)
    }

    // Always log API errors as breadcrumbs
    addBreadcrumb(`API Error: ${method} ${url}`, { status, error }, 'http')
  }

  /**
   * Get emoji for WebSocket event type
   * @param {string} event - Event name
   * @returns {string} Emoji
   * @private
   */
  _getWebSocketEmoji(event) {
    const eventLower = event.toLowerCase()

    if (eventLower.includes('connect')) return '✅'
    if (eventLower.includes('disconnect')) return '❌'
    if (eventLower.includes('error')) return '⚠️'
    if (eventLower.includes('deployment')) return '🚀'
    if (eventLower.includes('vulnerability')) return '🔍'
    if (eventLower.includes('patch')) return '🔧'
    if (eventLower.includes('alert')) return '🚨'
    if (eventLower.includes('health')) return '💚'
    if (eventLower.includes('metrics')) return '📊'
    if (eventLower.includes('progress')) return '📊'
    if (eventLower.includes('rollback')) return '⏪'

    return '📡'
  }

  /**
   * Create a performance timer
   * @param {string} label - Timer label
   * @returns {Object} Timer object with stop() method
   */
  time(label) {
    const startTime = performance.now()

    return {
      stop: () => {
        const duration = performance.now() - startTime
        if (isDev || isVerbose) {
          console.log(`⏱️  [TIMING] ${label}: ${duration.toFixed(2)}ms`)
        }

        // Add performance breadcrumb
        addBreadcrumb(`Timing: ${label}`, { duration: `${duration.toFixed(2)}ms` }, 'performance')
      },
    }
  }

  /**
   * Group console logs (development only)
   * @param {string} label - Group label
   * @param {Function} callback - Callback function
   */
  group(label, callback) {
    if (isDev) {
      console.group(label)
      callback()
      console.groupEnd()
    } else {
      callback()
    }
  }

  /**
   * Log table data (development only)
   * @param {Array|Object} data - Data to display
   */
  table(data) {
    if (isDev) {
      console.table(data)
    }
  }
}

// Export singleton instance
export const logger = new Logger()
export default logger
