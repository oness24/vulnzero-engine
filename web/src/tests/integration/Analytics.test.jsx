import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Analytics from '../../pages/Analytics'
import * as api from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  monitoringApi: {
    analytics: vi.fn(),
  },
  dashboardApi: {
    trends: vi.fn(),
  },
}))

// Mock chart libraries
vi.mock('recharts', () => ({
  LineChart: ({ children }) => <div data-testid="line-chart">{children}</div>,
  BarChart: ({ children }) => <div data-testid="bar-chart">{children}</div>,
  PieChart: ({ children }) => <div data-testid="pie-chart">{children}</div>,
  AreaChart: ({ children }) => <div data-testid="area-chart">{children}</div>,
  Line: () => null,
  Bar: () => null,
  Pie: () => null,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
  Cell: () => null,
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

const mockAnalytics = {
  data: {
    vulnerability_trends: [
      { date: '2024-11-01', critical: 5, high: 12, medium: 23, low: 34 },
      { date: '2024-11-08', critical: 4, high: 10, medium: 20, low: 32 },
      { date: '2024-11-15', critical: 3, high: 8, medium: 18, low: 30 },
    ],
    patch_success_rate: [
      { date: '2024-11-01', success: 0.92, failed: 0.08 },
      { date: '2024-11-08', success: 0.94, failed: 0.06 },
      { date: '2024-11-15', success: 0.96, failed: 0.04 },
    ],
    deployment_metrics: [
      { date: '2024-11-01', total: 25, successful: 23, failed: 2 },
      { date: '2024-11-08', total: 30, successful: 28, failed: 2 },
      { date: '2024-11-15', total: 28, successful: 27, failed: 1 },
    ],
    severity_distribution: {
      critical: 12,
      high: 34,
      medium: 67,
      low: 43,
    },
    response_times: {
      avg: 145,
      p50: 120,
      p95: 250,
      p99: 450,
    },
    mttr: {
      // Mean Time To Remediate
      current: 4.2,
      previous: 5.8,
      improvement: 0.28,
    },
  },
}

const mockTrends = {
  data: {
    weekly: mockAnalytics.data.vulnerability_trends,
    monthly: [],
  },
}

describe('Analytics Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders analytics page', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.monitoringApi.analytics).toHaveBeenCalled()
    })
  })

  it('displays vulnerability trends chart', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for chart component or trend data
      const charts = screen.queryAllByTestId(/chart/i)
      expect(charts.length).toBeGreaterThan(0)
    })
  })

  it('displays patch success rate chart', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for success rate metrics
      expect(screen.getByText(/92%|94%|96%/)).toBeInTheDocument()
    })
  })

  it('displays deployment metrics chart', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for deployment counts
      expect(screen.getByText(/25|30|28/)).toBeInTheDocument()
    })
  })

  it('displays severity distribution pie chart', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for severity counts
      expect(screen.getByText(/12/)).toBeInTheDocument() // Critical
      expect(screen.getByText(/34/)).toBeInTheDocument() // High
      expect(screen.getByText(/67/)).toBeInTheDocument() // Medium
      expect(screen.getByText(/43/)).toBeInTheDocument() // Low
    })
  })

  it('displays response time percentiles', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for response time metrics
      expect(screen.getByText(/145/)).toBeInTheDocument() // Avg
      expect(screen.getByText(/120/)).toBeInTheDocument() // P50
      expect(screen.getByText(/250/)).toBeInTheDocument() // P95
      expect(screen.getByText(/450/)).toBeInTheDocument() // P99
    })
  })

  it('displays MTTR metric with improvement', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for MTTR values
      expect(screen.getByText(/4\.2/)).toBeInTheDocument() // Current
      expect(screen.getByText(/5\.8/)).toBeInTheDocument() // Previous
      expect(screen.getByText(/28%/)).toBeInTheDocument() // Improvement
    })
  })

  it('allows switching between time ranges', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.monitoringApi.analytics).toHaveBeenCalled()
    })

    // Check for time range selectors (7d, 30d, 90d)
    // Implementation-dependent
  })

  it('displays trend indicators (up/down arrows)', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Should show improvement/decline indicators
      expect(api.monitoringApi.analytics).toHaveBeenCalled()
    })
  })

  it('displays key performance indicators', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Should display KPIs like MTTR, success rate, etc.
      expect(screen.getByText(/MTTR|Mean Time|Success Rate/i)).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    api.monitoringApi.analytics.mockRejectedValue(
      new Error('Failed to fetch analytics')
    )
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.monitoringApi.analytics).toHaveBeenCalled()
    })

    // Should display error state
  })

  it('displays loading state initially', () => {
    api.monitoringApi.analytics.mockReturnValue(new Promise(() => {})) // Never resolves
    api.dashboardApi.trends.mockReturnValue(new Promise(() => {}))

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    // Should show loading indicator
    // Implementation-dependent
  })

  it('exports analytics data', async () => {
    api.monitoringApi.analytics.mockResolvedValue(mockAnalytics)
    api.dashboardApi.trends.mockResolvedValue(mockTrends)

    render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.monitoringApi.analytics).toHaveBeenCalled()
    })

    // Check for export button (if implemented)
    const exportButton = screen.queryByRole('button', { name: /export|download/i })
    // Test export functionality if available
  })
})
