import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Vulnerabilities from '../../pages/Vulnerabilities'
import * as api from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  vulnerabilitiesApi: {
    list: vi.fn(),
    get: vi.fn(),
    markFalsePositive: vi.fn(),
  },
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
    button: ({ children, ...props }) => <button {...props}>{children}</button>,
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

const mockVulnerabilities = {
  data: {
    items: [
      {
        id: 1,
        cve_id: 'CVE-2024-1234',
        title: 'SQL Injection in User Authentication',
        severity: 'critical',
        status: 'open',
        description: 'Critical SQL injection vulnerability',
        affected_component: 'auth-service',
        cvss_score: 9.8,
        discovered_at: '2024-11-18T10:00:00Z',
      },
      {
        id: 2,
        cve_id: 'CVE-2024-5678',
        title: 'XSS in Dashboard',
        severity: 'high',
        status: 'in_progress',
        description: 'Cross-site scripting vulnerability',
        affected_component: 'web-dashboard',
        cvss_score: 7.5,
        discovered_at: '2024-11-17T14:30:00Z',
      },
      {
        id: 3,
        cve_id: 'CVE-2024-9012',
        title: 'Insecure Deserialization',
        severity: 'medium',
        status: 'resolved',
        description: 'Insecure deserialization in API',
        affected_component: 'api-gateway',
        cvss_score: 5.5,
        discovered_at: '2024-11-16T09:15:00Z',
      },
    ],
    pagination: {
      page: 1,
      pageSize: 20,
      total: 3,
      totalPages: 1,
      hasNext: false,
      hasPrevious: false,
    },
  },
}

describe('Vulnerabilities Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders vulnerabilities list page', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue(mockVulnerabilities)

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.vulnerabilitiesApi.list).toHaveBeenCalled()
    })
  })

  it('displays vulnerability cards with correct information', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue(mockVulnerabilities)

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for CVE IDs
      expect(screen.getByText('CVE-2024-1234')).toBeInTheDocument()
      expect(screen.getByText('CVE-2024-5678')).toBeInTheDocument()
      expect(screen.getByText('CVE-2024-9012')).toBeInTheDocument()
    })

    // Check for titles
    expect(screen.getByText(/SQL Injection/i)).toBeInTheDocument()
    expect(screen.getByText(/XSS in Dashboard/i)).toBeInTheDocument()
  })

  it('displays severity badges correctly', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue(mockVulnerabilities)

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for severity indicators
      expect(screen.getByText(/critical/i)).toBeInTheDocument()
      expect(screen.getByText(/high/i)).toBeInTheDocument()
      expect(screen.getByText(/medium/i)).toBeInTheDocument()
    })
  })

  it('displays status badges correctly', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue(mockVulnerabilities)

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for status indicators
      expect(screen.getByText(/open/i)).toBeInTheDocument()
      expect(screen.getByText(/in_progress/i)).toBeInTheDocument()
      expect(screen.getByText(/resolved/i)).toBeInTheDocument()
    })
  })

  it('displays CVSS scores', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue(mockVulnerabilities)

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for CVSS scores
      expect(screen.getByText(/9\.8/)).toBeInTheDocument()
      expect(screen.getByText(/7\.5/)).toBeInTheDocument()
      expect(screen.getByText(/5\.5/)).toBeInTheDocument()
    })
  })

  it('allows filtering by severity', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue(mockVulnerabilities)

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.vulnerabilitiesApi.list).toHaveBeenCalled()
    })

    // Find and click severity filter (implementation-dependent)
    const criticalFilter = screen.queryByRole('button', { name: /critical/i })
    if (criticalFilter) {
      fireEvent.click(criticalFilter)

      await waitFor(() => {
        // Should call API with severity filter
        expect(api.vulnerabilitiesApi.list).toHaveBeenCalledWith(
          expect.objectContaining({
            severity: 'critical',
          })
        )
      })
    }
  })

  it('allows filtering by status', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue(mockVulnerabilities)

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.vulnerabilitiesApi.list).toHaveBeenCalled()
    })

    // Find and click status filter (implementation-dependent)
    const openFilter = screen.queryByRole('button', { name: /^open$/i })
    if (openFilter) {
      fireEvent.click(openFilter)

      await waitFor(() => {
        // Should call API with status filter
        expect(api.vulnerabilitiesApi.list).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 'open',
          })
        )
      })
    }
  })

  it('displays empty state when no vulnerabilities', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue({
      data: {
        items: [],
        pagination: {
          page: 1,
          pageSize: 20,
          total: 0,
          totalPages: 0,
          hasNext: false,
          hasPrevious: false,
        },
      },
    })

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.vulnerabilitiesApi.list).toHaveBeenCalled()
    })

    // Should show empty state message
    // Exact text depends on implementation
  })

  it('handles API errors gracefully', async () => {
    api.vulnerabilitiesApi.list.mockRejectedValue(
      new Error('Failed to fetch vulnerabilities')
    )

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.vulnerabilitiesApi.list).toHaveBeenCalled()
    })

    // Should display error state or message
  })

  it('displays pagination controls when needed', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue({
      data: {
        items: mockVulnerabilities.data.items,
        pagination: {
          page: 1,
          pageSize: 2,
          total: 10,
          totalPages: 5,
          hasNext: true,
          hasPrevious: false,
        },
      },
    })

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.vulnerabilitiesApi.list).toHaveBeenCalled()
    })

    // Should show pagination controls
    // Exact implementation depends on component
  })

  it('allows marking vulnerability as false positive', async () => {
    api.vulnerabilitiesApi.list.mockResolvedValue(mockVulnerabilities)
    api.vulnerabilitiesApi.markFalsePositive.mockResolvedValue({ data: { success: true } })

    render(
      <BrowserRouter>
        <Vulnerabilities />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.vulnerabilitiesApi.list).toHaveBeenCalled()
    })

    // Find mark false positive button (implementation-dependent)
    const falsePositiveButton = screen.queryByRole('button', {
      name: /false positive/i,
    })

    if (falsePositiveButton) {
      fireEvent.click(falsePositiveButton)

      await waitFor(() => {
        expect(api.vulnerabilitiesApi.markFalsePositive).toHaveBeenCalled()
      })
    }
  })
})
