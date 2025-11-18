/**
 * Custom hook for fetching monitoring and health data
 */

import { useState, useEffect, useCallback } from 'react'
import { monitoringApi } from '../services/api'
import wsService from '../services/websocket'
import toast from 'react-hot-toast'

export function useSystemHealth() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchHealth = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await monitoringApi.health()
      setData(response.data)
    } catch (err) {
      console.error('Error fetching system health:', err)
      setError(err.response?.data?.detail || 'Failed to load system health')
      // Don't show toast for health checks - they run frequently
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHealth()

    // Set up WebSocket listeners
    const unsubscribeDegraded = wsService.on('health_degraded', () => {
      fetchHealth()
    })

    const unsubscribeRestored = wsService.on('health_restored', () => {
      fetchHealth()
    })

    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchHealth, 10000)

    return () => {
      unsubscribeDegraded()
      unsubscribeRestored()
      clearInterval(interval)
    }
  }, [fetchHealth])

  return {
    health: data,
    loading,
    error,
    refetch: fetchHealth,
  }
}

export function useMetrics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await monitoringApi.metrics()
      setData(response.data)
    } catch (err) {
      console.error('Error fetching metrics:', err)
      setError(err.response?.data?.detail || 'Failed to load metrics')
      toast.error('Failed to load metrics')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMetrics()

    // Set up WebSocket listener
    const unsubscribe = wsService.on('metrics_update', (metricsData) => {
      setData(metricsData)
    })

    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchMetrics, 5000)

    return () => {
      unsubscribe()
      clearInterval(interval)
    }
  }, [fetchMetrics])

  return {
    metrics: data,
    loading,
    error,
    refetch: fetchMetrics,
  }
}

export function useAlerts(filters = {}) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  })

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await monitoringApi.alerts(filters)

      if (response.data.items) {
        setData(response.data.items)
        setPagination(response.data.pagination || pagination)
      } else {
        setData(response.data)
      }
    } catch (err) {
      console.error('Error fetching alerts:', err)
      setError(err.response?.data?.detail || 'Failed to load alerts')
      toast.error('Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    fetchAlerts()

    // Set up WebSocket listener for new alerts
    const unsubscribe = wsService.on('alert', () => {
      fetchAlerts() // Refresh alerts when new one arrives
    })

    return unsubscribe
  }, [fetchAlerts])

  const acknowledgeAlert = async (id) => {
    try {
      await monitoringApi.acknowledgeAlert(id)
      toast.success('Alert acknowledged')
      await fetchAlerts() // Refresh list
    } catch (err) {
      console.error('Error acknowledging alert:', err)
      toast.error('Failed to acknowledge alert')
      throw err
    }
  }

  return {
    alerts: data,
    loading,
    error,
    pagination,
    refetch: fetchAlerts,
    acknowledgeAlert,
  }
}

export function useAnalytics(params = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await monitoringApi.analytics(params)
      setData(response.data)
    } catch (err) {
      console.error('Error fetching analytics:', err)
      setError(err.response?.data?.detail || 'Failed to load analytics')
      toast.error('Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(params)])

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  return {
    analytics: data,
    loading,
    error,
    refetch: fetchAnalytics,
  }
}
