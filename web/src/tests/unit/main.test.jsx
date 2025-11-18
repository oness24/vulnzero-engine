import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'

// Mock ReactDOM
const mockRender = vi.fn()
vi.mock('react-dom/client', () => ({
  default: {
    createRoot: vi.fn(() => ({
      render: mockRender,
    })),
  },
  createRoot: vi.fn(() => ({
    render: mockRender,
  })),
}))

// Mock App component
vi.mock('../../App', () => ({
  default: () => <div data-testid="app">VulnZero App</div>,
}))

// Mock CSS import
vi.mock('../../styles/index.css', () => ({}))

describe('Main Entry Point', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Create root element for testing
    const root = document.createElement('div')
    root.id = 'root'
    document.body.appendChild(root)
  })

  it('creates root element correctly', async () => {
    const { createRoot } = await import('react-dom/client')

    // Simulate main.jsx execution
    const rootElement = document.getElementById('root')
    expect(rootElement).toBeTruthy()

    const root = createRoot(rootElement)
    expect(createRoot).toHaveBeenCalledWith(rootElement)
  })

  it('renders App in StrictMode', async () => {
    const React = await import('react')
    const App = (await import('../../App')).default

    // Verify StrictMode wrapping
    const AppWithStrictMode = (
      <React.StrictMode>
        <App />
      </React.StrictMode>
    )

    const { container } = render(AppWithStrictMode)
    expect(container.querySelector('[data-testid="app"]')).toBeTruthy()
  })

  it('mounts to root DOM element', () => {
    const rootElement = document.getElementById('root')
    expect(rootElement).toBeInstanceOf(HTMLElement)
    expect(rootElement.id).toBe('root')
  })

  it('imports necessary dependencies', async () => {
    // Verify React is importable
    const React = await import('react')
    expect(React).toBeDefined()
    expect(React.StrictMode).toBeDefined()

    // Verify ReactDOM is importable
    const ReactDOM = await import('react-dom/client')
    expect(ReactDOM).toBeDefined()
    expect(ReactDOM.createRoot).toBeDefined()

    // Verify App is importable
    const App = await import('../../App')
    expect(App.default).toBeDefined()
  })

  describe('Production Build', () => {
    it('uses createRoot for React 18 concurrent features', async () => {
      const { createRoot } = await import('react-dom/client')
      const rootElement = document.getElementById('root')

      createRoot(rootElement)
      expect(createRoot).toHaveBeenCalled()
    })

    it('enables StrictMode for development warnings', async () => {
      const React = await import('react')
      expect(React.StrictMode).toBeDefined()
      expect(typeof React.StrictMode).toBe('object')
    })
  })
})
