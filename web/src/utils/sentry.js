/**
 * Sentry Error Tracking Configuration
 *
 * Initializes and configures Sentry for error tracking and performance monitoring.
 * Only enabled when VITE_SENTRY_DSN is set in environment variables.
 */

import * as Sentry from '@sentry/react'

/**
 * Initialize Sentry
 *
 * Call this once at app startup (in main.jsx)
 */
export function initSentry() {
  const sentryDsn = import.meta.env.VITE_SENTRY_DSN
  const environment = import.meta.env.VITE_ENVIRONMENT || import.meta.env.MODE || 'development'
  const release = import.meta.env.VITE_APP_VERSION || '1.0.0'

  // Only initialize Sentry if DSN is provided
  if (!sentryDsn) {
    console.info('Sentry DSN not configured. Error tracking disabled.')
    return false
  }

  try {
    Sentry.init({
      dsn: sentryDsn,
      environment,
      release: `vulnzero-web@${release}`,

      // Performance Monitoring
      integrations: [
        new Sentry.BrowserTracing({
          // Set sampling rate for performance monitoring
          tracePropagationTargets: [
            'localhost',
            /^https:\/\/.*\.vulnzero\.io/,
            /^https:\/\/api\.vulnzero\.io/,
          ],
        }),
        new Sentry.Replay({
          // Mask all text and input content for privacy
          maskAllText: true,
          blockAllMedia: true,
        }),
      ],

      // Set tracesSampleRate to 1.0 to capture 100% of transactions for performance monitoring
      // In production, adjust this to a lower value (e.g., 0.1 for 10%)
      tracesSampleRate: environment === 'production' ? 0.1 : 1.0,

      // Capture 10% of sessions for replay in production
      replaysSessionSampleRate: environment === 'production' ? 0.1 : 0,

      // If the entire session is not sampled, use the below sample rate to sample
      // sessions when an error occurs
      replaysOnErrorSampleRate: 1.0,

      // Filter out errors that are not useful
      beforeSend(event, hint) {
        // Filter out development errors
        if (environment === 'development') {
          console.error('Sentry event (dev):', event, hint)
          // Don't send to Sentry in development
          return null
        }

        // Filter out specific errors
        const error = hint.originalException

        // Ignore network errors (these are expected and handled)
        if (error && error.message) {
          if (
            error.message.includes('Network Error') ||
            error.message.includes('Failed to fetch') ||
            error.message.includes('NetworkError')
          ) {
            return null
          }
        }

        // Ignore ResizeObserver errors (common browser quirk)
        if (error && error.message && error.message.includes('ResizeObserver')) {
          return null
        }

        return event
      },

      // Add additional context to all events
      beforeBreadcrumb(breadcrumb) {
        // Filter out noisy breadcrumbs
        if (breadcrumb.category === 'console') {
          return null
        }
        return breadcrumb
      },

      // Don't send PII
      sendDefaultPii: false,

      // Ignore certain URLs from being captured
      denyUrls: [
        // Browser extensions
        /extensions\//i,
        /^chrome:\/\//i,
        /^moz-extension:\/\//i,
      ],

      // Set maximum breadcrumbs
      maxBreadcrumbs: 50,
    })

    console.info('Sentry initialized successfully')
    return true
  } catch (error) {
    console.error('Failed to initialize Sentry:', error)
    return false
  }
}

/**
 * Capture exception manually
 *
 * @param {Error} error - The error to capture
 * @param {Object} context - Additional context
 */
export function captureException(error, context = {}) {
  if (import.meta.env.DEV) {
    console.error('Error captured:', error, context)
  }

  Sentry.captureException(error, {
    extra: context,
  })
}

/**
 * Capture message manually
 *
 * @param {string} message - The message to capture
 * @param {string} level - Severity level (info, warning, error)
 * @param {Object} context - Additional context
 */
export function captureMessage(message, level = 'info', context = {}) {
  if (import.meta.env.DEV) {
    console.log(`[${level}] ${message}`, context)
  }

  Sentry.captureMessage(message, {
    level,
    extra: context,
  })
}

/**
 * Set user context for error tracking
 *
 * @param {Object} user - User information
 */
export function setUser(user) {
  if (!user) {
    Sentry.setUser(null)
    return
  }

  Sentry.setUser({
    id: user.id,
    username: user.username,
    email: user.email,
    // Don't send sensitive data
  })
}

/**
 * Add breadcrumb for debugging
 *
 * @param {string} message - Breadcrumb message
 * @param {Object} data - Additional data
 * @param {string} category - Breadcrumb category
 */
export function addBreadcrumb(message, data = {}, category = 'custom') {
  Sentry.addBreadcrumb({
    message,
    category,
    data,
    level: 'info',
  })
}

/**
 * Set custom tag
 *
 * @param {string} key - Tag key
 * @param {string} value - Tag value
 */
export function setTag(key, value) {
  Sentry.setTag(key, value)
}

/**
 * Set custom context
 *
 * @param {string} name - Context name
 * @param {Object} context - Context data
 */
export function setContext(name, context) {
  Sentry.setContext(name, context)
}

export default Sentry
