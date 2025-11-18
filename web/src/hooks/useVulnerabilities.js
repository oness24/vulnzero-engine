/**
 * Custom hook for fetching and managing vulnerabilities
 */

import { useState, useEffect, useCallback } from 'react'
import { vulnerabilitiesApi } from '../services/api'
import toast from 'react-hot-toast'

export function useVulnerabilities(filters = {}) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  })

  const fetchVulnerabilities = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await vulnerabilitiesApi.list(filters)

      // Handle both paginated and non-paginated responses
      if (response.data.items) {
        setData(response.data.items)
        setPagination(response.data.pagination || pagination)
      } else {
        setData(response.data)
      }
    } catch (err) {
      console.error('Error fetching vulnerabilities:', err)
      setError(err.response?.data?.detail || 'Failed to load vulnerabilities')
      toast.error('Failed to load vulnerabilities')
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    fetchVulnerabilities()
  }, [fetchVulnerabilities])

  const markFalsePositive = async (id) => {
    try {
      await vulnerabilitiesApi.markFalsePositive(id)
      toast.success('Vulnerability marked as false positive')
      await fetchVulnerabilities() // Refresh list
    } catch (err) {
      console.error('Error marking false positive:', err)
      toast.error('Failed to mark as false positive')
      throw err
    }
  }

  return {
    vulnerabilities: data,
    loading,
    error,
    pagination,
    refetch: fetchVulnerabilities,
    markFalsePositive,
  }
}

export function useVulnerability(id) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchVulnerability = useCallback(async () => {
    if (!id) return

    try {
      setLoading(true)
      setError(null)

      const response = await vulnerabilitiesApi.get(id)
      setData(response.data)
    } catch (err) {
      console.error('Error fetching vulnerability:', err)
      setError(err.response?.data?.detail || 'Failed to load vulnerability')
      toast.error('Failed to load vulnerability details')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchVulnerability()
  }, [fetchVulnerability])

  return {
    vulnerability: data,
    loading,
    error,
    refetch: fetchVulnerability,
  }
}
