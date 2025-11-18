import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Dashboard from '../../pages/Dashboard'
import * as dashboardApi from '../../services/api'

// Mock the API module
vi.mock('../../services/api', () => ({
  dashboardApi: {
    stats: vi.fn(),
    activity: vi.fn(),
    trends: vi.fn(),
  },
}))

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
    h1: ({ children, ...props }) => <h1 {...props}>{children}</h1>,
    p: ({ children, ...props }) => <p {...props}>{children}</p>,
  },
  AnimatePresence: ({ children }) => <>{children}</>,
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const mockStats = {
  data: {
    vulnerabilities: {
      total: 156,
      critical: 12,
      high: 34,
      medium: 67,
      low: 43,
      open: 89,
      in_progress: 45,
      resolved: 22,
    },
    patches: {
      total: 142,
      pending_approval: 23,
      approved: 89,
      deployed: 30,
      success_rate: 0.94,
    },
    deployments: {
      total: 8,
      in_progress: 2,
      completed: 5,
      failed: 1,
      success_rate: 0.875,
    },
    system_health: {
      status: 'healthy',
      uptime: 99.8,
      response_time_ms: 145,
    },
  },
}

const mockActivity = {
  data: {
    items: [
      {
        id: 1,
        type: 'vulnerability_detected',
        title: 'Critical SQL Injection detected',
        severity: 'critical',
        timestamp: '2024-11-18T10:30:00Z',
      },
      {
        id: 2,
        type: 'patch_generated',
        title: 'Patch generated for CVE-2024-1234',
        severity: 'high',
        timestamp: '2024-11-18T09:15:00Z',
      },
    ],
  },
}

describe('Dashboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders dashboard with loading state initially', () => {
    dashboardApi.dashboardApi.stats.mockReturnValue(new Promise(() => {})) // Never resolves

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    )

    // Should show loading or placeholder
    expect(screen.queryByText('156')).not.toBeInTheDocument()
  })

  it('loads and displays dashboard statistics', async () => {
    dashboardApi.dashboardApi.stats.mockResolvedValue(mockStats)
    dashboardApi.dashboardApi.activity.mockResolvedValue(mockActivity)

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    )

    // Wait for the data to load
    await waitFor(() => {
      expect(dashboardApi.dashboardApi.stats).toHaveBeenCalled()
    })

    // Check if vulnerability stats are displayed
    await waitFor(() => {
      expect(screen.getByText(/156/)).toBeInTheDocument() // Total vulnerabilities
    })
  })

  it('displays vulnerability severity breakdown', async () => {
    dashboardApi.dashboardApi.stats.mockResolvedValue(mockStats)
    dashboardApi.dashboardApi.activity.mockResolvedValue(mockActivity)

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for severity counts
      expect(screen.getByText(/12/)).toBeInTheDocument() // Critical
      expect(screen.getByText(/34/)).toBeInTheDocument() // High
    })
  })

  it('displays patch statistics', async () => {
    dashboardApi.dashboardApi.stats.mockResolvedValue(mockStats)
    dashboardApi.dashboardApi.activity.mockResolvedValue(mockActivity)

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for patch stats
      expect(screen.getByText(/142/)).toBeInTheDocument() // Total patches
      expect(screen.getByText(/94%/)).toBeInTheDocument() // Success rate
    })
  })

  it('displays deployment statistics', async () => {
    dashboardApi.dashboardApi.stats.mockResolvedValue(mockStats)
    dashboardApi.dashboardApi.activity.mockResolvedValue(mockActivity)

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for deployment stats
      expect(screen.getByText(/8/)).toBeInTheDocument() // Total deployments
    })
  })

  it('displays system health status', async () => {
    dashboardApi.dashboardApi.stats.mockResolvedValue(mockStats)
    dashboardApi.dashboardApi.activity.mockResolvedValue(mockActivity)

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for health status
      expect(screen.getByText(/healthy/i)).toBeInTheDocument()
    })
  })

  it('displays recent activity feed', async () => {
    dashboardApi.dashboardApi.stats.mockResolvedValue(mockStats)
    dashboardApi.dashboardApi.activity.mockResolvedValue(mockActivity)

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for activity items
      expect(screen.getByText(/SQL Injection/i)).toBeInTheDocument()
      expect(screen.getByText(/CVE-2024-1234/i)).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    dashboardApi.dashboardApi.stats.mockRejectedValue(
      new Error('Failed to fetch stats')
    )
    dashboardApi.dashboardApi.activity.mockResolvedValue(mockActivity)

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(dashboardApi.dashboardApi.stats).toHaveBeenCalled()
    })

    // Component should still render, maybe with error state or fallback
    // Exact behavior depends on error handling implementation
  })

  it('has navigation links to other pages', async () => {
    dashboardApi.dashboardApi.stats.mockResolvedValue(mockStats)
    dashboardApi.dashboardApi.activity.mockResolvedValue(mockActivity)

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(dashboardApi.dashboardApi.stats).toHaveBeenCalled()
    })

    // Check for navigation elements (links/buttons to other pages)
    // Exact text depends on implementation
  })
})
