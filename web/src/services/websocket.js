/**
 * WebSocket Service for Real-Time Updates
 *
 * Handles real-time communication for:
 * - Deployment progress updates
 * - New vulnerability notifications
 * - Patch generation status
 * - System alerts
 */

import io from 'socket.io-client'
import toast from 'react-hot-toast'
import { logger } from '../utils/logger'

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'http://localhost:8000'

class WebSocketService {
  constructor() {
    this.socket = null
    this.listeners = new Map()
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.isConnected = false
  }

  /**
   * Connect to WebSocket server
   * @param {Object} options - Connection options
   */
  connect(options = {}) {
    if (this.socket?.connected) {
      logger.websocket('already connected')
      return
    }

    const token = localStorage.getItem('auth_token')

    this.socket = io(WS_BASE_URL, {
      transports: ['websocket', 'polling'],
      auth: {
        token: token || '',
      },
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: this.maxReconnectAttempts,
      ...options,
    })

    this.setupEventHandlers()
  }

  /**
   * Set up WebSocket event handlers
   */
  setupEventHandlers() {
    // Connection events
    this.socket.on('connect', () => {
      logger.websocket('connect', { socketId: this.socket.id })
      this.isConnected = true
      this.reconnectAttempts = 0

      if (import.meta.env.DEV) {
        toast.success('Real-time connection established', { duration: 2000 })
      }

      this.emit('connected', { socketId: this.socket.id })
    })

    this.socket.on('disconnect', (reason) => {
      logger.websocket('disconnect', { reason })
      this.isConnected = false

      if (import.meta.env.DEV) {
        toast.error('Real-time connection lost', { duration: 2000 })
      }

      this.emit('disconnected', { reason })
    })

    this.socket.on('connect_error', (error) => {
      logger.websocket('error', { error: error.message })
      this.reconnectAttempts++

      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        toast.error('Unable to establish real-time connection. Some features may be limited.')
      }

      this.emit('error', { error })
    })

    this.socket.on('reconnect', (attemptNumber) => {
      logger.websocket('reconnect', { attemptNumber })
      toast.success('Real-time connection restored', { duration: 2000 })
      this.emit('reconnected', { attemptNumber })
    })

    // Deployment events
    this.socket.on('deployment_started', (data) => {
      logger.websocket('deployment_started', data)
      this.emit('deployment_started', data)

      toast.success(`Deployment started: ${data.deployment_id}`, {
        icon: '🚀',
        duration: 3000,
      })
    })

    this.socket.on('deployment_progress', (data) => {
      logger.websocket('deployment_progress', data)
      this.emit('deployment_progress', data)
    })

    this.socket.on('deployment_completed', (data) => {
      logger.websocket('deployment_completed', data)
      this.emit('deployment_completed', data)

      toast.success(`Deployment ${data.deployment_id} completed successfully!`, {
        icon: '✅',
        duration: 5000,
      })
    })

    this.socket.on('deployment_failed', (data) => {
      logger.websocket('deployment_failed', data)
      this.emit('deployment_failed', data)

      toast.error(`Deployment ${data.deployment_id} failed: ${data.error}`, {
        icon: '❌',
        duration: 5000,
      })
    })

    this.socket.on('deployment_rolled_back', (data) => {
      logger.websocket('deployment_rolled_back', data)
      this.emit('deployment_rolled_back', data)

      toast.error(`Deployment ${data.deployment_id} was rolled back: ${data.reason}`, {
        icon: '⏪',
        duration: 5000,
      })
    })

    // Vulnerability events
    this.socket.on('vulnerability_detected', (data) => {
      logger.websocket('vulnerability_detected', data)
      this.emit('vulnerability_detected', data)

      const severity = data.severity?.toUpperCase()
      const icon = severity === 'CRITICAL' ? '🚨' : severity === 'HIGH' ? '⚠️' : '🔍'

      toast.error(`New ${severity} vulnerability: ${data.cve_id}`, {
        icon,
        duration: 5000,
      })
    })

    // Patch events
    this.socket.on('patch_generated', (data) => {
      logger.websocket('patch_generated', data)
      this.emit('patch_generated', data)

      toast.success(`Patch generated for ${data.vulnerability_cve} (Confidence: ${(data.confidence * 100).toFixed(0)}%)`, {
        icon: '🔧',
        duration: 4000,
      })
    })

    this.socket.on('patch_approved', (data) => {
      logger.websocket('patch_approved', data)
      this.emit('patch_approved', data)

      toast.success(`Patch ${data.patch_id} approved`, {
        icon: '✅',
        duration: 3000,
      })
    })

    this.socket.on('patch_rejected', (data) => {
      logger.websocket('patch_rejected', data)
      this.emit('patch_rejected', data)

      toast.error(`Patch ${data.patch_id} rejected: ${data.reason}`, {
        icon: '❌',
        duration: 4000,
      })
    })

    // Alert events
    this.socket.on('alert', (data) => {
      logger.websocket('alert', data)
      this.emit('alert', data)

      const severity = data.severity?.toUpperCase()
      const icon = severity === 'CRITICAL' ? '🚨' : severity === 'HIGH' ? '⚠️' : 'ℹ️'

      toast.error(data.message, {
        icon,
        duration: 5000,
      })
    })

    // Health/Monitoring events
    this.socket.on('health_degraded', (data) => {
      logger.websocket('health_degraded', data)
      this.emit('health_degraded', data)

      toast.error(`System health degraded: ${data.service}`, {
        icon: '⚠️',
        duration: 4000,
      })
    })

    this.socket.on('health_restored', (data) => {
      logger.websocket('health_restored', data)
      this.emit('health_restored', data)

      toast.success(`System health restored: ${data.service}`, {
        icon: '✅',
        duration: 3000,
      })
    })

    // Metrics updates
    this.socket.on('metrics_update', (data) => {
      logger.websocket('metrics_update', data)
      this.emit('metrics_update', data)
    })
  }

  /**
   * Subscribe to a specific event
   * @param {string} event - Event name
   * @param {Function} callback - Callback function
   * @returns {Function} Unsubscribe function
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }

    this.listeners.get(event).push(callback)

    // Return unsubscribe function
    return () => this.off(event, callback)
  }

  /**
   * Unsubscribe from an event
   * @param {string} event - Event name
   * @param {Function} callback - Callback function to remove
   */
  off(event, callback) {
    const callbacks = this.listeners.get(event)

    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  /**
   * Emit event to all listeners
   * @param {string} event - Event name
   * @param {*} data - Event data
   */
  emit(event, data) {
    const callbacks = this.listeners.get(event) || []
    callbacks.forEach((callback) => {
      try {
        callback(data)
      } catch (error) {
        logger.error(`Error in event listener for ${event}`, error)
      }
    })
  }

  /**
   * Send a message to the server
   * @param {string} event - Event name
   * @param {*} data - Data to send
   */
  send(event, data) {
    if (!this.socket?.connected) {
      logger.warn('WebSocket not connected, cannot send message', { event })
      return
    }

    this.socket.emit(event, data)
  }

  /**
   * Join a room (for filtered updates)
   * @param {string} room - Room name (e.g., 'deployment:123')
   */
  joinRoom(room) {
    if (!this.socket?.connected) {
      logger.warn('WebSocket not connected, cannot join room', { room })
      return
    }

    this.socket.emit('join_room', { room })
    logger.debug(`Joined room: ${room}`)
  }

  /**
   * Leave a room
   * @param {string} room - Room name
   */
  leaveRoom(room) {
    if (!this.socket?.connected) {
      logger.warn('WebSocket not connected, cannot leave room', { room })
      return
    }

    this.socket.emit('leave_room', { room })
    logger.debug(`Left room: ${room}`)
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.isConnected = false
      this.listeners.clear()
      logger.websocket('disconnect (manual)')
    }
  }

  /**
   * Check if connected
   * @returns {boolean}
   */
  isSocketConnected() {
    return this.isConnected && this.socket?.connected
  }

  /**
   * Get connection status
   * @returns {Object}
   */
  getStatus() {
    return {
      connected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      socketId: this.socket?.id,
    }
  }
}

// Create singleton instance
const wsService = new WebSocketService()

export default wsService
