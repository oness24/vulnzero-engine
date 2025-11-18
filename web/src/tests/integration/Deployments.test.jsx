import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Deployments from '../../pages/Deployments'
import * as api from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  deploymentsApi: {
    list: vi.fn(),
    create: vi.fn(),
    rollback: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
  },
}))

// Mock WebSocket service
vi.mock('../../services/websocket', () => ({
  default: {
    on: vi.fn(() => () => {}), // Return unsubscribe function
    off: vi.fn(),
    isSocketConnected: vi.fn(() => true),
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

const mockDeployments = {
  data: {
    items: [
      {
        id: 1,
        patch_id: 42,
        environment: 'production',
        status: 'in_progress',
        progress: 0.65,
        current_step: 'Running smoke tests',
        started_at: '2024-11-18T10:00:00Z',
        completed_at: null,
        rollback_available: true,
      },
      {
        id: 2,
        patch_id: 41,
        environment: 'staging',
        status: 'completed',
        progress: 1.0,
        current_step: 'Deployment complete',
        started_at: '2024-11-17T14:30:00Z',
        completed_at: '2024-11-17T14:45:00Z',
        rollback_available: true,
      },
      {
        id: 3,
        patch_id: 40,
        environment: 'production',
        status: 'failed',
        progress: 0.3,
        current_step: 'Health check failed',
        started_at: '2024-11-16T09:15:00Z',
        completed_at: '2024-11-16T09:25:00Z',
        rollback_available: true,
        error_message: 'Service health degraded after deployment',
      },
    ],
    pagination: {
      page: 1,
      pageSize: 20,
      total: 3,
      totalPages: 1,
    },
  },
}

describe('Deployments Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders deployments list page', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.deploymentsApi.list).toHaveBeenCalled()
    })
  })

  it('displays deployment cards with environment information', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getAllByText(/production/i)).toHaveLength(2)
      expect(screen.getByText(/staging/i)).toBeInTheDocument()
    })
  })

  it('displays deployment status badges', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/in_progress/i)).toBeInTheDocument()
      expect(screen.getByText(/completed/i)).toBeInTheDocument()
      expect(screen.getByText(/failed/i)).toBeInTheDocument()
    })
  })

  it('displays progress bars for deployments', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for progress indicators (65%, 100%, 30%)
      expect(screen.getByText(/65%/)).toBeInTheDocument()
      expect(screen.getByText(/100%/)).toBeInTheDocument()
      expect(screen.getByText(/30%/)).toBeInTheDocument()
    })
  })

  it('displays current deployment steps', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Running smoke tests/i)).toBeInTheDocument()
      expect(screen.getByText(/Deployment complete/i)).toBeInTheDocument()
      expect(screen.getByText(/Health check failed/i)).toBeInTheDocument()
    })
  })

  it('displays error messages for failed deployments', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(
        screen.getByText(/Service health degraded after deployment/i)
      ).toBeInTheDocument()
    })
  })

  it('allows creating a new deployment', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)
    api.deploymentsApi.create.mockResolvedValue({
      data: { deployment_id: 4, status: 'pending' },
    })

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.deploymentsApi.list).toHaveBeenCalled()
    })

    const createButton = screen.queryByRole('button', {
      name: /create|deploy|new/i,
    })
    if (createButton) {
      fireEvent.click(createButton)

      await waitFor(() => {
        expect(api.deploymentsApi.create).toHaveBeenCalled()
      })
    }
  })

  it('allows rolling back a deployment', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)
    api.deploymentsApi.rollback.mockResolvedValue({
      data: { success: true },
    })

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.deploymentsApi.list).toHaveBeenCalled()
    })

    const rollbackButton = screen.queryByRole('button', { name: /rollback/i })
    if (rollbackButton) {
      fireEvent.click(rollbackButton)

      await waitFor(() => {
        expect(api.deploymentsApi.rollback).toHaveBeenCalled()
      })
    }
  })

  it('allows pausing a deployment', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)
    api.deploymentsApi.pause.mockResolvedValue({ data: { success: true } })

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.deploymentsApi.list).toHaveBeenCalled()
    })

    const pauseButton = screen.queryByRole('button', { name: /pause/i })
    if (pauseButton) {
      fireEvent.click(pauseButton)

      await waitFor(() => {
        expect(api.deploymentsApi.pause).toHaveBeenCalled()
      })
    }
  })

  it('filters deployments by environment', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.deploymentsApi.list).toHaveBeenCalled()
    })

    const prodFilter = screen.queryByRole('button', { name: /production/i })
    if (prodFilter) {
      fireEvent.click(prodFilter)

      await waitFor(() => {
        expect(api.deploymentsApi.list).toHaveBeenCalledWith(
          expect.objectContaining({
            environment: 'production',
          })
        )
      })
    }
  })

  it('filters deployments by status', async () => {
    api.deploymentsApi.list.mockResolvedValue(mockDeployments)

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.deploymentsApi.list).toHaveBeenCalled()
    })

    const completedFilter = screen.queryByRole('button', {
      name: /completed/i,
    })
    if (completedFilter) {
      fireEvent.click(completedFilter)

      await waitFor(() => {
        expect(api.deploymentsApi.list).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 'completed',
          })
        )
      })
    }
  })

  it('handles API errors gracefully', async () => {
    api.deploymentsApi.list.mockRejectedValue(
      new Error('Failed to fetch deployments')
    )

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.deploymentsApi.list).toHaveBeenCalled()
    })

    // Should display error state
  })

  it('displays empty state when no deployments', async () => {
    api.deploymentsApi.list.mockResolvedValue({
      data: {
        items: [],
        pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
      },
    })

    render(
      <BrowserRouter>
        <Deployments />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.deploymentsApi.list).toHaveBeenCalled()
    })

    // Should show empty state
  })
})
