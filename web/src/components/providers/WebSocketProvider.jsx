/**
 * WebSocket Provider Component
 *
 * Manages WebSocket connection lifecycle for the entire app
 * - Connects on mount
 * - Disconnects on unmount
 * - Provides connection status to children
 */

import { createContext, useContext, useEffect, useState } from 'react'
import wsService from '../../services/websocket'

const WebSocketContext = createContext({
  isConnected: false,
  status: null,
})

export function useWebSocket() {
  return useContext(WebSocketContext)
}

export function WebSocketProvider({ children }) {
  const [isConnected, setIsConnected] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    // Connect to WebSocket on mount
    wsService.connect()

    // Set up connection status listeners
    const unsubscribeConnected = wsService.on('connected', () => {
      setIsConnected(true)
      setStatus(wsService.getStatus())
    })

    const unsubscribeDisconnected = wsService.on('disconnected', () => {
      setIsConnected(false)
      setStatus(wsService.getStatus())
    })

    const unsubscribeReconnected = wsService.on('reconnected', () => {
      setIsConnected(true)
      setStatus(wsService.getStatus())
    })

    // Initial status
    setStatus(wsService.getStatus())

    // Disconnect on unmount
    return () => {
      unsubscribeConnected()
      unsubscribeDisconnected()
      unsubscribeReconnected()
      wsService.disconnect()
    }
  }, [])

  const value = {
    isConnected,
    status,
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}
