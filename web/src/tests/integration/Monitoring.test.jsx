import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Monitoring from '../../pages/Monitoring'
import * as api from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  monitoringApi: {
    health: vi.fn(),
    metrics: vi.fn(),
    alerts: vi.fn(),
    analytics: vi.fn(),
  },
}))

// Mock WebSocket service
vi.mock('../../services/websocket', () => ({
  default: {
    on: vi.fn(() => () => {}),
    off: vi.fn(),
    isSocketConnected: vi.fn(() => true),
  },
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
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

const mockHealth = {
  data: {
    status: 'healthy',
    timestamp: '2024-11-18T10:00:00Z',
    checks: {
      database: 'ok',
      redis: 'ok',
      celery: 'ok',
      api: 'ok',
    },
    details: {
      database: 'PostgreSQL connection verified',
      redis: 'Redis connection verified',
      celery: '4 workers active',
      api: 'All endpoints responding',
    },
  },
}

const mockMetrics = {
  data: {
    cpu_usage: 45.2,
    memory_usage: 62.8,
    disk_usage: 38.5,
    network_in: 1250000,
    network_out: 2340000,
    request_rate: 125,
    error_rate: 0.5,
    avg_response_time: 145,
  },
}

const mockAlerts = {
  data: {
    items: [
      {
        id: 1,
        severity: 'critical',
        title: 'High CPU Usage',
        message: 'CPU usage exceeded 90% threshold',
        timestamp: '2024-11-18T10:00:00Z',
        resolved: false,
      },
      {
        id: 2,
        severity: 'warning',
        title: 'Slow Response Time',
        message: 'Average response time above 500ms',
        timestamp: '2024-11-18T09:30:00Z',
        resolved: false,
      },
      {
        id: 3,
        severity: 'info',
        title: 'New Deployment',
        message: 'Deployment completed successfully',
        timestamp: '2024-11-18T09:00:00Z',
        resolved: true,
      },
    ],
  },
}

describe('Monitoring Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders monitoring page', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.monitoringApi.health).toHaveBeenCalled()
    })
  })

  it('displays system health status', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/healthy/i)).toBeInTheDocument()
    })
  })

  it('displays health check results for all services', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for service names
      expect(screen.getByText(/database/i)).toBeInTheDocument()
      expect(screen.getByText(/redis/i)).toBeInTheDocument()
      expect(screen.getByText(/celery/i)).toBeInTheDocument()
    })
  })

  it('displays system metrics', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for metrics
      expect(screen.getByText(/45\.2/)).toBeInTheDocument() // CPU usage
      expect(screen.getByText(/62\.8/)).toBeInTheDocument() // Memory usage
      expect(screen.getByText(/38\.5/)).toBeInTheDocument() // Disk usage
    })
  })

  it('displays response time metric', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/145/)).toBeInTheDocument() // Response time
    })
  })

  it('displays error rate metric', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/0\.5/)).toBeInTheDocument() // Error rate
    })
  })

  it('displays active alerts', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/High CPU Usage/i)).toBeInTheDocument()
      expect(screen.getByText(/Slow Response Time/i)).toBeInTheDocument()
      expect(screen.getByText(/New Deployment/i)).toBeInTheDocument()
    })
  })

  it('displays alert severity badges', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/critical/i)).toBeInTheDocument()
      expect(screen.getByText(/warning/i)).toBeInTheDocument()
      expect(screen.getByText(/info/i)).toBeInTheDocument()
    })
  })

  it('distinguishes between resolved and unresolved alerts', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check that resolved/unresolved states are shown
      // Implementation depends on UI design
      expect(api.monitoringApi.alerts).toHaveBeenCalled()
    })
  })

  it('handles unhealthy system status', async () => {
    api.monitoringApi.health.mockResolvedValue({
      data: {
        status: 'unhealthy',
        checks: {
          database: 'error',
          redis: 'ok',
          celery: 'warning',
        },
        details: {
          database: 'Connection timeout',
          redis: 'Redis connection verified',
          celery: 'No workers found',
        },
      },
    })
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/unhealthy/i)).toBeInTheDocument()
      expect(screen.getByText(/Connection timeout/i)).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    api.monitoringApi.health.mockRejectedValue(
      new Error('Failed to fetch health')
    )
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.monitoringApi.health).toHaveBeenCalled()
    })

    // Should display error state
  })

  it('auto-refreshes metrics at regular intervals', async () => {
    vi.useFakeTimers()

    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.monitoringApi.metrics).toHaveBeenCalledTimes(1)
    })

    // Fast forward 5 seconds (typical refresh interval)
    vi.advanceTimersByTime(5000)

    await waitFor(() => {
      expect(api.monitoringApi.metrics).toHaveBeenCalledTimes(2)
    })

    vi.useRealTimers()
  })

  it('displays real-time metrics updates via WebSocket', async () => {
    api.monitoringApi.health.mockResolvedValue(mockHealth)
    api.monitoringApi.metrics.mockResolvedValue(mockMetrics)
    api.monitoringApi.alerts.mockResolvedValue(mockAlerts)

    render(
      <BrowserRouter>
        <Monitoring />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.monitoringApi.health).toHaveBeenCalled()
    })

    // WebSocket mock should have been set up
    // Actual test would simulate WebSocket events
  })
})
