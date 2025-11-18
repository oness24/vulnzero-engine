/**
 * Custom hook for fetching dashboard data
 */

import { useState, useEffect, useCallback } from 'react'
import { dashboardApi } from '../services/api'
import wsService from '../services/websocket'
import toast from 'react-hot-toast'

export function useDashboardStats() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await dashboardApi.stats()
      setData(response.data)
    } catch (err) {
      console.error('Error fetching dashboard stats:', err)
      setError(err.response?.data?.detail || 'Failed to load dashboard statistics')
      toast.error('Failed to load dashboard statistics')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()

    // Set up WebSocket listener for real-time updates
    const unsubscribe = wsService.on('metrics_update', () => {
      fetchStats() // Refresh stats when metrics update
    })

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000)

    // Cleanup
    return () => {
      unsubscribe()
      clearInterval(interval)
    }
  }, [fetchStats])

  return {
    stats: data,
    loading,
    error,
    refetch: fetchStats,
  }
}

export function useDashboardActivity(limit = 10) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchActivity = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await dashboardApi.recentActivity(limit)
      setData(response.data)
    } catch (err) {
      console.error('Error fetching recent activity:', err)
      setError(err.response?.data?.detail || 'Failed to load recent activity')
    } finally {
      setLoading(false)
    }
  }, [limit])

  useEffect(() => {
    fetchActivity()

    // Refresh when relevant events occur
    const unsubscribeVuln = wsService.on('vulnerability_detected', fetchActivity)
    const unsubscribePatch = wsService.on('patch_generated', fetchActivity)
    const unsubscribeDeploy = wsService.on('deployment_completed', fetchActivity)

    return () => {
      unsubscribeVuln()
      unsubscribePatch()
      unsubscribeDeploy()
    }
  }, [fetchActivity])

  return {
    activity: data,
    loading,
    error,
    refetch: fetchActivity,
  }
}

export function useDashboardTrends(period = 'week') {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchTrends = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await dashboardApi.trends(period)
      setData(response.data)
    } catch (err) {
      console.error('Error fetching trends:', err)
      setError(err.response?.data?.detail || 'Failed to load trends')
    } finally {
      setLoading(false)
    }
  }, [period])

  useEffect(() => {
    fetchTrends()
  }, [fetchTrends])

  return {
    trends: data,
    loading,
    error,
    refetch: fetchTrends,
  }
}
