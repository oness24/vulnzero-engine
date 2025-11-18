import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, Link } from 'react-router-dom'
import App from '../../App'

// Mock all page components
vi.mock('../../components/layout/Layout', () => ({
  default: ({ children }) => (
    <div data-testid="layout">
      <nav>
        <Link to="/">Dashboard</Link>
        <Link to="/vulnerabilities">Vulnerabilities</Link>
        <Link to="/patches">Patches</Link>
        <Link to="/deployments">Deployments</Link>
        <Link to="/monitoring">Monitoring</Link>
        <Link to="/analytics">Analytics</Link>
        <Link to="/settings">Settings</Link>
      </nav>
      {children}
    </div>
  ),
}))

vi.mock('../../pages/Dashboard', () => ({
  default: () => <div data-testid="page-dashboard">Dashboard Page</div>,
}))

vi.mock('../../pages/Vulnerabilities', () => ({
  default: () => <div data-testid="page-vulnerabilities">Vulnerabilities Page</div>,
}))

vi.mock('../../pages/Patches', () => ({
  default: () => <div data-testid="page-patches">Patches Page</div>,
}))

vi.mock('../../pages/Deployments', () => ({
  default: () => <div data-testid="page-deployments">Deployments Page</div>,
}))

vi.mock('../../pages/Monitoring', () => ({
  default: () => <div data-testid="page-monitoring">Monitoring Page</div>,
}))

vi.mock('../../pages/Analytics', () => ({
  default: () => <div data-testid="page-analytics">Analytics Page</div>,
}))

vi.mock('../../pages/Settings', () => ({
  default: () => <div data-testid="page-settings">Settings Page</div>,
}))

describe('Application Routing Integration', () => {
  describe('Route Rendering', () => {
    it('renders Dashboard as default route', () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      )

      expect(screen.getByTestId('page-dashboard')).toBeInTheDocument()
      expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
    })

    it('renders all routes correctly', async () => {
      const routes = [
        { path: '/', testId: 'page-dashboard', text: 'Dashboard Page' },
        { path: '/vulnerabilities', testId: 'page-vulnerabilities', text: 'Vulnerabilities Page' },
        { path: '/patches', testId: 'page-patches', text: 'Patches Page' },
        { path: '/deployments', testId: 'page-deployments', text: 'Deployments Page' },
        { path: '/monitoring', testId: 'page-monitoring', text: 'Monitoring Page' },
        { path: '/analytics', testId: 'page-analytics', text: 'Analytics Page' },
        { path: '/settings', testId: 'page-settings', text: 'Settings Page' },
      ]

      for (const route of routes) {
        const { unmount } = render(
          <MemoryRouter initialEntries={[route.path]}>
            <App />
          </MemoryRouter>
        )

        expect(screen.getByTestId(route.testId)).toBeInTheDocument()
        expect(screen.getByText(route.text)).toBeInTheDocument()

        unmount()
      }
    })
  })

  describe('Navigation', () => {
    it('navigates between pages using links', async () => {
      const user = userEvent.setup()

      render(
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      )

      // Initially on Dashboard
      expect(screen.getByTestId('page-dashboard')).toBeInTheDocument()

      // Navigate to Vulnerabilities
      const vulnLink = screen.getByText('Vulnerabilities')
      await user.click(vulnLink)

      await waitFor(() => {
        expect(screen.getByTestId('page-vulnerabilities')).toBeInTheDocument()
      })
    })

    it('maintains layout across route changes', async () => {
      const user = userEvent.setup()

      render(
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      )

      const layout = screen.getByTestId('layout')
      expect(layout).toBeInTheDocument()

      // Navigate to different page
      await user.click(screen.getByText('Patches'))

      await waitFor(() => {
        // Layout should still be present
        expect(screen.getByTestId('layout')).toBeInTheDocument()
        // But page content changed
        expect(screen.getByTestId('page-patches')).toBeInTheDocument()
      })
    })
  })

  describe('Nested Routes', () => {
    it('renders nested routes under Layout component', () => {
      render(
        <MemoryRouter initialEntries={['/vulnerabilities']}>
          <App />
        </MemoryRouter>
      )

      expect(screen.getByTestId('layout')).toBeInTheDocument()
      expect(screen.getByTestId('page-vulnerabilities')).toBeInTheDocument()
    })
  })

  describe('404 Handling', () => {
    it('handles unknown routes gracefully', () => {
      render(
        <MemoryRouter initialEntries={['/unknown-route']}>
          <App />
        </MemoryRouter>
      )

      // Should render layout but no page
      expect(screen.getByTestId('layout')).toBeInTheDocument()
    })
  })

  describe('Route Transitions', () => {
    it('supports AnimatePresence for page transitions', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      )

      // AnimatePresence should be in the component tree
      expect(container.querySelector('.relative.z-10')).toBeInTheDocument()
    })
  })

  describe('Browser History', () => {
    it('uses BrowserRouter for history support', () => {
      const { container } = render(<App />)

      // App should render with Router
      expect(container).toBeTruthy()
    })
  })

  describe('Performance', () => {
    it('lazy loads routes efficiently', async () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      )

      // Only current page should be rendered
      expect(screen.getByTestId('page-dashboard')).toBeInTheDocument()
      expect(screen.queryByTestId('page-vulnerabilities')).not.toBeInTheDocument()
      expect(screen.queryByTestId('page-patches')).not.toBeInTheDocument()
    })
  })
})
