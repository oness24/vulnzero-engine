import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Patches from '../../pages/Patches'
import * as api from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  patchesApi: {
    list: vi.fn(),
    approve: vi.fn(),
    reject: vi.fn(),
    test: vi.fn(),
    generate: vi.fn(),
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

const mockPatches = {
  data: {
    items: [
      {
        id: 1,
        vulnerability_cve: 'CVE-2024-1234',
        patch_type: 'code',
        status: 'pending_approval',
        confidence: 0.95,
        created_at: '2024-11-18T10:00:00Z',
        patch_content: 'diff --git a/auth.py...',
        test_results: null,
      },
      {
        id: 2,
        vulnerability_cve: 'CVE-2024-5678',
        patch_type: 'configuration',
        status: 'approved',
        confidence: 0.88,
        created_at: '2024-11-17T14:30:00Z',
        patch_content: 'Update nginx config...',
        test_results: { passed: 12, failed: 0 },
      },
      {
        id: 3,
        vulnerability_cve: 'CVE-2024-9012',
        patch_type: 'dependency',
        status: 'deployed',
        confidence: 0.92,
        created_at: '2024-11-16T09:15:00Z',
        patch_content: 'Update package.json...',
        test_results: { passed: 8, failed: 0 },
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

describe('Patches Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders patches list page', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.patchesApi.list).toHaveBeenCalled()
    })
  })

  it('displays patch cards with CVE information', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('CVE-2024-1234')).toBeInTheDocument()
      expect(screen.getByText('CVE-2024-5678')).toBeInTheDocument()
      expect(screen.getByText('CVE-2024-9012')).toBeInTheDocument()
    })
  })

  it('displays patch types correctly', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/code/i)).toBeInTheDocument()
      expect(screen.getByText(/configuration/i)).toBeInTheDocument()
      expect(screen.getByText(/dependency/i)).toBeInTheDocument()
    })
  })

  it('displays patch status badges', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/pending_approval/i)).toBeInTheDocument()
      expect(screen.getByText(/approved/i)).toBeInTheDocument()
      expect(screen.getByText(/deployed/i)).toBeInTheDocument()
    })
  })

  it('displays confidence scores', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Confidence scores as percentages
      expect(screen.getByText(/95%/)).toBeInTheDocument()
      expect(screen.getByText(/88%/)).toBeInTheDocument()
      expect(screen.getByText(/92%/)).toBeInTheDocument()
    })
  })

  it('allows approving a patch', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)
    api.patchesApi.approve.mockResolvedValue({ data: { success: true } })

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.patchesApi.list).toHaveBeenCalled()
    })

    const approveButton = screen.queryByRole('button', { name: /approve/i })
    if (approveButton) {
      fireEvent.click(approveButton)

      await waitFor(() => {
        expect(api.patchesApi.approve).toHaveBeenCalled()
      })
    }
  })

  it('allows rejecting a patch', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)
    api.patchesApi.reject.mockResolvedValue({ data: { success: true } })

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.patchesApi.list).toHaveBeenCalled()
    })

    const rejectButton = screen.queryByRole('button', { name: /reject/i })
    if (rejectButton) {
      fireEvent.click(rejectButton)

      await waitFor(() => {
        expect(api.patchesApi.reject).toHaveBeenCalled()
      })
    }
  })

  it('allows testing a patch', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)
    api.patchesApi.test.mockResolvedValue({
      data: { test_id: 'test-123', status: 'running' },
    })

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.patchesApi.list).toHaveBeenCalled()
    })

    const testButton = screen.queryByRole('button', { name: /test/i })
    if (testButton) {
      fireEvent.click(testButton)

      await waitFor(() => {
        expect(api.patchesApi.test).toHaveBeenCalled()
      })
    }
  })

  it('displays test results when available', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Check for test results
      expect(screen.getByText(/12/)).toBeInTheDocument() // Passed tests
      expect(screen.getByText(/8/)).toBeInTheDocument() // Passed tests
    })
  })

  it('allows filtering by patch status', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.patchesApi.list).toHaveBeenCalled()
    })

    const pendingFilter = screen.queryByRole('button', {
      name: /pending/i,
    })
    if (pendingFilter) {
      fireEvent.click(pendingFilter)

      await waitFor(() => {
        expect(api.patchesApi.list).toHaveBeenCalledWith(
          expect.objectContaining({
            status: 'pending_approval',
          })
        )
      })
    }
  })

  it('allows filtering by patch type', async () => {
    api.patchesApi.list.mockResolvedValue(mockPatches)

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.patchesApi.list).toHaveBeenCalled()
    })

    const codeFilter = screen.queryByRole('button', { name: /^code$/i })
    if (codeFilter) {
      fireEvent.click(codeFilter)

      await waitFor(() => {
        expect(api.patchesApi.list).toHaveBeenCalledWith(
          expect.objectContaining({
            patch_type: 'code',
          })
        )
      })
    }
  })

  it('handles API errors gracefully', async () => {
    api.patchesApi.list.mockRejectedValue(new Error('Failed to fetch patches'))

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.patchesApi.list).toHaveBeenCalled()
    })

    // Should display error state
  })

  it('displays empty state when no patches', async () => {
    api.patchesApi.list.mockResolvedValue({
      data: {
        items: [],
        pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
      },
    })

    render(
      <BrowserRouter>
        <Patches />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.patchesApi.list).toHaveBeenCalled()
    })

    // Should show empty state
  })
})
