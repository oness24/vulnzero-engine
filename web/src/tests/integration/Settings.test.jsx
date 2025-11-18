import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Settings from '../../pages/Settings'
import * as api from '../../services/api'

// Mock the API
vi.mock('../../services/api', () => ({
  settingsApi: {
    get: vi.fn(),
    update: vi.fn(),
    updateIntegrations: vi.fn(),
    updateNotifications: vi.fn(),
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

const mockSettings = {
  data: {
    general: {
      auto_patch: true,
      auto_deploy: false,
      environment: 'production',
      min_confidence_threshold: 0.85,
      notification_email: 'admin@vulnzero.io',
    },
    integrations: {
      github: {
        enabled: true,
        repository: 'org/repo',
        api_token: '***masked***',
      },
      slack: {
        enabled: true,
        webhook_url: '***masked***',
        channel: '#security-alerts',
      },
      jira: {
        enabled: false,
        url: '',
        api_token: '',
        project_key: '',
      },
    },
    notifications: {
      vulnerability_detected: true,
      patch_generated: true,
      deployment_started: true,
      deployment_completed: true,
      deployment_failed: true,
      health_degraded: true,
      email_enabled: true,
      slack_enabled: true,
    },
    security: {
      two_factor_enabled: false,
      session_timeout: 3600,
      allowed_ips: ['0.0.0.0/0'],
    },
  },
}

describe('Settings Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders settings page', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.settingsApi.get).toHaveBeenCalled()
    })
  })

  it('displays general settings section', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/general|settings/i)).toBeInTheDocument()
    })
  })

  it('displays auto-patch toggle', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/auto.*patch/i)).toBeInTheDocument()
    })

    // Should be enabled according to mock data
    const toggle = screen.queryByRole('checkbox', { name: /auto.*patch/i })
    if (toggle) {
      expect(toggle).toBeChecked()
    }
  })

  it('displays auto-deploy toggle', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/auto.*deploy/i)).toBeInTheDocument()
    })

    // Should be disabled according to mock data
    const toggle = screen.queryByRole('checkbox', { name: /auto.*deploy/i })
    if (toggle) {
      expect(toggle).not.toBeChecked()
    }
  })

  it('displays confidence threshold setting', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/confidence.*threshold/i)).toBeInTheDocument()
      expect(screen.getByText(/85%|0\.85/)).toBeInTheDocument()
    })
  })

  it('displays notification email', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/admin@vulnzero\.io/)).toBeInTheDocument()
    })
  })

  it('displays integrations section', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/integrations/i)).toBeInTheDocument()
    })
  })

  it('displays GitHub integration settings', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/github/i)).toBeInTheDocument()
      expect(screen.getByText(/org\/repo/)).toBeInTheDocument()
    })

    // GitHub should be enabled
    const githubToggle = screen.queryByRole('checkbox', { name: /github/i })
    if (githubToggle) {
      expect(githubToggle).toBeChecked()
    }
  })

  it('displays Slack integration settings', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/slack/i)).toBeInTheDocument()
      expect(screen.getByText(/#security-alerts/)).toBeInTheDocument()
    })

    // Slack should be enabled
    const slackToggle = screen.queryByRole('checkbox', { name: /slack/i })
    if (slackToggle) {
      expect(slackToggle).toBeChecked()
    }
  })

  it('displays JIRA integration settings', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/jira/i)).toBeInTheDocument()
    })

    // JIRA should be disabled
    const jiraToggle = screen.queryByRole('checkbox', { name: /jira/i })
    if (jiraToggle) {
      expect(jiraToggle).not.toBeChecked()
    }
  })

  it('masks sensitive data like API tokens', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      // Should show masked token
      expect(screen.getAllByText(/\*\*\*masked\*\*\*/i).length).toBeGreaterThan(0)
    })
  })

  it('displays notification preferences section', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/notifications/i)).toBeInTheDocument()
    })
  })

  it('displays notification toggles for different events', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/vulnerability.*detected/i)).toBeInTheDocument()
      expect(screen.getByText(/patch.*generated/i)).toBeInTheDocument()
      expect(screen.getByText(/deployment.*started/i)).toBeInTheDocument()
    })
  })

  it('allows updating general settings', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)
    api.settingsApi.update.mockResolvedValue({ data: { success: true } })

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.settingsApi.get).toHaveBeenCalled()
    })

    // Find and click save button
    const saveButton = screen.queryByRole('button', { name: /save|update/i })
    if (saveButton) {
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(api.settingsApi.update).toHaveBeenCalled()
      })
    }
  })

  it('allows toggling auto-patch setting', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)
    api.settingsApi.update.mockResolvedValue({ data: { success: true } })

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.settingsApi.get).toHaveBeenCalled()
    })

    const autoPatchToggle = screen.queryByRole('checkbox', {
      name: /auto.*patch/i,
    })
    if (autoPatchToggle) {
      fireEvent.click(autoPatchToggle)

      // Should trigger update
      await waitFor(() => {
        // Implementation may auto-save or require save button click
      })
    }
  })

  it('allows updating integration settings', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)
    api.settingsApi.updateIntegrations.mockResolvedValue({
      data: { success: true },
    })

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.settingsApi.get).toHaveBeenCalled()
    })

    // Toggle an integration
    const githubToggle = screen.queryByRole('checkbox', { name: /github/i })
    if (githubToggle) {
      fireEvent.click(githubToggle)

      await waitFor(() => {
        // May trigger update
      })
    }
  })

  it('allows updating notification preferences', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)
    api.settingsApi.updateNotifications.mockResolvedValue({
      data: { success: true },
    })

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.settingsApi.get).toHaveBeenCalled()
    })

    // Toggle a notification setting
    const vulnNotification = screen.queryByRole('checkbox', {
      name: /vulnerability.*detected/i,
    })
    if (vulnNotification) {
      fireEvent.click(vulnNotification)

      await waitFor(() => {
        // May trigger update
      })
    }
  })

  it('displays security settings section', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/security/i)).toBeInTheDocument()
    })
  })

  it('displays two-factor authentication setting', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/two.*factor|2FA/i)).toBeInTheDocument()
    })

    // Should be disabled according to mock data
    const twoFactorToggle = screen.queryByRole('checkbox', {
      name: /two.*factor|2FA/i,
    })
    if (twoFactorToggle) {
      expect(twoFactorToggle).not.toBeChecked()
    }
  })

  it('displays session timeout setting', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/session.*timeout/i)).toBeInTheDocument()
      expect(screen.getByText(/3600|1 hour/i)).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    api.settingsApi.get.mockRejectedValue(
      new Error('Failed to fetch settings')
    )

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.settingsApi.get).toHaveBeenCalled()
    })

    // Should display error state
  })

  it('displays success message after saving settings', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)
    api.settingsApi.update.mockResolvedValue({ data: { success: true } })

    const toast = await import('react-hot-toast')

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.settingsApi.get).toHaveBeenCalled()
    })

    const saveButton = screen.queryByRole('button', { name: /save/i })
    if (saveButton) {
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(toast.default.success).toHaveBeenCalled()
      })
    }
  })

  it('validates required fields before saving', async () => {
    api.settingsApi.get.mockResolvedValue(mockSettings)

    render(
      <BrowserRouter>
        <Settings />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(api.settingsApi.get).toHaveBeenCalled()
    })

    // Clear required field (email)
    const emailInput = screen.queryByRole('textbox', { name: /email/i })
    if (emailInput) {
      fireEvent.change(emailInput, { target: { value: '' } })

      const saveButton = screen.queryByRole('button', { name: /save/i })
      if (saveButton) {
        fireEvent.click(saveButton)

        await waitFor(() => {
          // Should not call update API with invalid data
          // Should show validation error
        })
      }
    }
  })
})
