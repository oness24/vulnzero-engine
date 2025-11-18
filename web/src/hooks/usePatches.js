/**
 * Custom hook for fetching and managing patches
 */

import { useState, useEffect, useCallback } from 'react'
import { patchesApi } from '../services/api'
import toast from 'react-hot-toast'

export function usePatches(filters = {}) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pagination, setPagination] = useState({
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  })

  const fetchPatches = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await patchesApi.list(filters)

      if (response.data.items) {
        setData(response.data.items)
        setPagination(response.data.pagination || pagination)
      } else {
        setData(response.data)
      }
    } catch (err) {
      console.error('Error fetching patches:', err)
      setError(err.response?.data?.detail || 'Failed to load patches')
      toast.error('Failed to load patches')
    } finally {
      setLoading(false)
    }
  }, [JSON.stringify(filters)])

  useEffect(() => {
    fetchPatches()
  }, [fetchPatches])

  const generatePatch = async (vulnerabilityId, patchType = 'code') => {
    try {
      const response = await patchesApi.generate({
        vulnerability_id: vulnerabilityId,
        patch_type: patchType,
      })

      toast.success('Patch generation started')
      await fetchPatches() // Refresh list
      return response.data
    } catch (err) {
      console.error('Error generating patch:', err)
      toast.error('Failed to generate patch')
      throw err
    }
  }

  const approvePatch = async (id) => {
    try {
      await patchesApi.approve(id)
      toast.success('Patch approved successfully')
      await fetchPatches() // Refresh list
    } catch (err) {
      console.error('Error approving patch:', err)
      toast.error('Failed to approve patch')
      throw err
    }
  }

  const rejectPatch = async (id, reason) => {
    try {
      await patchesApi.reject(id, reason)
      toast.success('Patch rejected')
      await fetchPatches() // Refresh list
    } catch (err) {
      console.error('Error rejecting patch:', err)
      toast.error('Failed to reject patch')
      throw err
    }
  }

  const testPatch = async (id) => {
    try {
      const response = await patchesApi.test(id)
      toast.success('Patch testing started in digital twin')
      return response.data
    } catch (err) {
      console.error('Error testing patch:', err)
      toast.error('Failed to start patch testing')
      throw err
    }
  }

  return {
    patches: data,
    loading,
    error,
    pagination,
    refetch: fetchPatches,
    generatePatch,
    approvePatch,
    rejectPatch,
    testPatch,
  }
}

export function usePatch(id) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchPatch = useCallback(async () => {
    if (!id) return

    try {
      setLoading(true)
      setError(null)

      const response = await patchesApi.get(id)
      setData(response.data)
    } catch (err) {
      console.error('Error fetching patch:', err)
      setError(err.response?.data?.detail || 'Failed to load patch')
      toast.error('Failed to load patch details')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchPatch()
  }, [fetchPatch])

  return {
    patch: data,
    loading,
    error,
    refetch: fetchPatch,
  }
}
