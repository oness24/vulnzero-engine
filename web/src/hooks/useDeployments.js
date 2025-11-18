/**
 * Custom hook for fetching and managing deployments
 */

import { useState, useEffect, useCallback } from 'react'
import { deploymentsApi } from '../services/api'
import wsService from '../services/websocket'
import toast from 'react-hot-toast'

export function useDeployments(filters = {}) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  })

  const fetchDeployments = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await deploymentsApi.list(filters)

      if (response.data.items) {
        setData(response.data.items)
        setPagination(response.data.pagination || pagination)
      } else {
        setData(response.data)
      }
    } catch (err) {
      console.error('Error fetching deployments:', err)
      setError(err.response?.data?.detail || 'Failed to load deployments')
      toast.error('Failed to load deployments')
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    fetchDeployments()

    // Set up WebSocket listeners for real-time updates
    const unsubscribeProgress = wsService.on('deployment_progress', (data) => {
      // Update specific deployment in list
      setData((prev) =>
        prev.map((deployment) =>
          deployment.id === data.deployment_id
            ? {
                ...deployment,
                progress: data.progress,
                status: data.status,
                current_step: data.current_step,
              }
            : deployment
        )
      )
    })

    const unsubscribeCompleted = wsService.on('deployment_completed', () => {
      fetchDeployments() // Refresh full list
    })

    const unsubscribeFailed = wsService.on('deployment_failed', () => {
      fetchDeployments() // Refresh full list
    })

    const unsubscribeRolledBack = wsService.on('deployment_rolled_back', () => {
      fetchDeployments() // Refresh full list
    })

    // Cleanup
    return () => {
      unsubscribeProgress()
      unsubscribeCompleted()
      unsubscribeFailed()
      unsubscribeRolledBack()
    }
  }, [fetchDeployments])

  const createDeployment = async (patchId, strategy, environment) => {
    try {
      const response = await deploymentsApi.create({
        patch_id: patchId,
        strategy,
        target_environment: environment,
      })

      toast.success('Deployment started')
      await fetchDeployments() // Refresh list
      return response.data
    } catch (err) {
      console.error('Error creating deployment:', err)
      toast.error('Failed to start deployment')
      throw err
    }
  }

  const rollbackDeployment = async (id) => {
    try {
      await deploymentsApi.rollback(id)
      toast.success('Deployment rollback initiated')
      await fetchDeployments() // Refresh list
    } catch (err) {
      console.error('Error rolling back deployment:', err)
      toast.error('Failed to rollback deployment')
      throw err
    }
  }

  const pauseDeployment = async (id) => {
    try {
      await deploymentsApi.pause(id)
      toast.success('Deployment paused')
      await fetchDeployments() // Refresh list
    } catch (err) {
      console.error('Error pausing deployment:', err)
      toast.error('Failed to pause deployment')
      throw err
    }
  }

  const resumeDeployment = async (id) => {
    try {
      await deploymentsApi.resume(id)
      toast.success('Deployment resumed')
      await fetchDeployments() // Refresh list
    } catch (err) {
      console.error('Error resuming deployment:', err)
      toast.error('Failed to resume deployment')
      throw err
    }
  }

  return {
    deployments: data,
    loading,
    error,
    pagination,
    refetch: fetchDeployments,
    createDeployment,
    rollbackDeployment,
    pauseDeployment,
    resumeDeployment,
  }
}

export function useDeployment(id) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchDeployment = useCallback(async () => {
    if (!id) return

    try {
      setLoading(true)
      setError(null)

      const response = await deploymentsApi.get(id)
      setData(response.data)
    } catch (err) {
      console.error('Error fetching deployment:', err)
      setError(err.response?.data?.detail || 'Failed to load deployment')
      toast.error('Failed to load deployment details')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchDeployment()

    // Set up WebSocket listener for this specific deployment
    const unsubscribe = wsService.on('deployment_progress', (wsData) => {
      if (wsData.deployment_id === id) {
        setData((prev) =>
          prev
            ? {
                ...prev,
                progress: wsData.progress,
                status: wsData.status,
                current_step: wsData.current_step,
              }
            : prev
        )
      }
    })

    // Cleanup
    return unsubscribe
  }, [fetchDeployment, id])

  return {
    deployment: data,
    loading,
    error,
    refetch: fetchDeployment,
  }
}
