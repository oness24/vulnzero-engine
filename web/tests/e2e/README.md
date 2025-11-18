# E2E Tests with Playwright

This directory contains end-to-end (E2E) tests for the VulnZero frontend using Playwright.

## Setup

1. Install Playwright browsers:
```bash
npm run playwright:install
```

## Running Tests

### Run all tests (headless)
```bash
npm run test:e2e
```

### Run tests with UI mode (interactive)
```bash
npm run test:e2e:ui
```

### Run tests in headed mode (see browser)
```bash
npm run test:e2e:headed
```

### Debug tests
```bash
npm run test:e2e:debug
```

### Run specific test file
```bash
npx playwright test tests/e2e/auth.spec.js
```

### Run tests in specific browser
```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## Test Structure

- `auth.spec.js` - Authentication flow tests (login, logout, protected routes)
- `navigation.spec.js` - Navigation between pages
- `dashboard.spec.js` - Dashboard functionality and widgets
- `vulnerabilities.spec.js` - Vulnerability listing, filtering, and details

## Test Data

Tests use the following default credentials:
- Username: `admin`
- Password: `admin123`

**Note:** Make sure test users exist in your database before running tests.

## CI/CD Integration

Tests are configured to run in CI with:
- Automatic retries on failure (2 retries)
- Parallel execution disabled for consistency
- GitHub Actions reporter for nice output

## Configuration

See `playwright.config.js` for:
- Browser configurations
- Viewport sizes (desktop and mobile)
- Timeouts and retries
- Base URLs
- Reporter settings

## Debugging Tips

1. **Use --debug flag**: Stops at first action and opens inspector
2. **Use --headed flag**: See the browser while tests run
3. **Use --ui flag**: Interactive mode with time travel debugging
4. **Screenshots**: Automatically captured on failure in `test-results/`
5. **Videos**: Automatically recorded on failure in `test-results/`
6. **Traces**: Captured on retry in `test-results/`

## Best Practices

1. Use `data-testid` attributes for stable selectors
2. Prefer user-facing selectors (roles, labels, text) over CSS/XPath
3. Wait for elements to be visible before interacting
4. Use helper functions for common actions (login, navigation)
5. Clean up test data after tests if needed
6. Mock API responses for faster, more reliable tests

## Writing New Tests

```javascript
import { test, expect } from '@playwright/test'

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup before each test
  })

  test('should do something', async ({ page }) => {
    // Test implementation
    await page.goto('/some-page')
    await expect(page.getByRole('heading')).toBeVisible()
  })
})
```

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Selectors Guide](https://playwright.dev/docs/selectors)
- [Debugging Guide](https://playwright.dev/docs/debug)
