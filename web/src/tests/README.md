# VulnZero Frontend Test Suite

## Overview

Comprehensive test suite for the VulnZero frontend application using Vitest, Testing Library, and modern testing best practices.

## Test Structure

```
tests/
├── unit/              # Unit tests for individual components
│   ├── App.test.jsx
│   ├── main.test.jsx
│   └── design-system.test.js
├── integration/       # Integration tests for feature workflows
│   └── routing.test.jsx
├── e2e/              # End-to-end tests (future)
├── mocks/            # Mock data and API responses
└── setup.js          # Test environment configuration
```

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with UI
npm run test:ui

# Generate coverage report
npm run test:coverage

# Run specific test file
npm test App.test.jsx

# Run tests matching pattern
npm test -- -t "routing"
```

## Test Categories

### Unit Tests

Test individual components, functions, and utilities in isolation.

**Examples:**
- Component rendering
- Props validation
- Event handlers
- Utility functions
- Design system configuration

**Location:** `tests/unit/`

### Integration Tests

Test feature workflows and component interactions.

**Examples:**
- Route navigation
- Form submissions
- API integration
- State management
- WebSocket connections

**Location:** `tests/integration/`

### E2E Tests (Future)

End-to-end tests using Playwright for full user workflows.

**Examples:**
- Complete vulnerability discovery workflow
- Patch generation and deployment
- Multi-page workflows
- Authentication flows

**Location:** `tests/e2e/`

## Writing Tests

### Basic Component Test

```jsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MyComponent from '../MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Test" />)
    expect(screen.getByText('Test')).toBeInTheDocument()
  })
})
```

### Testing User Interactions

```jsx
import userEvent from '@testing-library/user-event'

it('handles click events', async () => {
  const user = userEvent.setup()
  const handleClick = vi.fn()

  render(<button onClick={handleClick}>Click me</button>)

  await user.click(screen.getByRole('button'))
  expect(handleClick).toHaveBeenCalledTimes(1)
})
```

### Testing Async Operations

```jsx
import { waitFor } from '@testing-library/react'

it('loads data asynchronously', async () => {
  render(<DataComponent />)

  await waitFor(() => {
    expect(screen.getByText('Loaded')).toBeInTheDocument()
  })
})
```

### Mocking API Calls

```jsx
import { vi } from 'vitest'

vi.mock('../api/client', () => ({
  fetchVulnerabilities: vi.fn(() =>
    Promise.resolve([
      { id: 1, title: 'CVE-2024-1234', severity: 'critical' }
    ])
  )
}))
```

## Testing Best Practices

### DO ✅

- **Test user behavior, not implementation**
  ```jsx
  // Good - tests what user sees
  expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument()

  // Bad - tests implementation
  expect(wrapper.find('Button').prop('onClick')).toBeDefined()
  ```

- **Use accessibility queries**
  ```jsx
  screen.getByRole('button')
  screen.getByLabelText('Email')
  screen.getByPlaceholderText('Search...')
  ```

- **Test edge cases**
  - Empty states
  - Loading states
  - Error states
  - Large datasets
  - Slow networks

- **Keep tests focused and independent**
  - One assertion per test (when possible)
  - No shared state between tests
  - Clean up after each test

- **Use descriptive test names**
  ```jsx
  it('displays error message when API call fails', () => {})
  it('disables submit button while form is submitting', () => {})
  ```

### DON'T ❌

- **Don't test implementation details**
  ```jsx
  // Bad
  expect(component.state.isLoading).toBe(true)

  // Good
  expect(screen.getByText('Loading...')).toBeInTheDocument()
  ```

- **Don't use shallow rendering**
  ```jsx
  // Bad - shallow doesn't reflect real usage
  const wrapper = shallow(<MyComponent />)

  // Good - render fully
  render(<MyComponent />)
  ```

- **Don't rely on internal state**
  - Test outputs, not internals
  - Test what user sees and does

## Coverage Goals

- **Statements:** >80%
- **Branches:** >75%
- **Functions:** >80%
- **Lines:** >80%

### Coverage Report

```bash
npm run test:coverage
```

View HTML report: `coverage/index.html`

## Mocking Strategy

### Component Mocks

Mock child components to isolate parent component tests:

```jsx
vi.mock('./ChildComponent', () => ({
  default: () => <div data-testid="child">Mocked Child</div>
}))
```

### API Mocks

Mock API calls using Vitest:

```jsx
vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  }
}))
```

### Browser API Mocks

Mocked in `setup.js`:
- `window.matchMedia`
- `IntersectionObserver`
- `ResizeObserver`
- `localStorage`
- `sessionStorage`

## Accessibility Testing

All components should be tested for accessibility:

```jsx
import { axe, toHaveNoViolations } from 'jest-axe'

expect.extend(toHaveNoViolations)

it('has no accessibility violations', async () => {
  const { container } = render(<MyComponent />)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})
```

## Performance Testing

Test rendering performance for critical components:

```jsx
import { render, waitFor } from '@testing-library/react'

it('renders large lists efficiently', async () => {
  const startTime = performance.now()

  render(<VulnerabilityList items={Array(1000).fill({})} />)

  const endTime = performance.now()
  expect(endTime - startTime).toBeLessThan(100) // Should render in <100ms
})
```

## Debugging Tests

### Run single test
```bash
npm test -- -t "test name"
```

### Debug in VS Code
```json
{
  "type": "node",
  "request": "launch",
  "name": "Debug Tests",
  "runtimeExecutable": "npm",
  "runtimeArgs": ["test", "--", "--run"],
  "console": "integratedTerminal"
}
```

### View test output
```bash
npm test -- --reporter=verbose
```

### Debug failing tests
```jsx
import { screen, debug } from '@testing-library/react'

// Print current DOM
debug()

// Print specific element
debug(screen.getByRole('button'))
```

## CI/CD Integration

Tests run automatically on:
- Push to any branch
- Pull request creation
- Pre-commit hook (optional)

### GitHub Actions

```yaml
- name: Run tests
  run: npm test -- --run --coverage

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

**"Cannot find module"**
- Check import paths
- Verify mock paths match actual paths
- Clear Vitest cache: `npx vitest --clearCache`

**"Element not found"**
- Use `screen.debug()` to see current DOM
- Check if element is rendered conditionally
- Wait for async operations with `waitFor`

**"Test timeout"**
- Increase timeout: `it('test', async () => {}, 10000)`
- Check for unresolved promises
- Verify mock functions are called

**"React warnings in tests"**
- Wrap state updates in `act()`
- Use `waitFor` for async updates
- Check for missing cleanup

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [React Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [Accessibility Testing](https://web.dev/accessibility/)

## Contributing

When adding new tests:
1. Follow existing test structure
2. Use descriptive test names
3. Add JSDoc comments for complex tests
4. Update this README if adding new patterns
5. Ensure all tests pass: `npm test`
6. Maintain >80% coverage

---

**Last Updated:** 2025-11-18
**Maintainer:** VulnZero Team
