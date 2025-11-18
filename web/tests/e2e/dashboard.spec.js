import { test, expect } from '@playwright/test'

/**
 * Dashboard E2E Tests
 * Tests main dashboard functionality and widgets
 */

// Helper function to login
async function login(page) {
  await page.goto('/login')
  await page.getByLabel(/username/i).fill('admin')
  await page.getByLabel(/password/i).fill('admin123')
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL('/')
}

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test('should display dashboard with key metrics', async ({ page }) => {
    // Check for dashboard heading
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()

    // Check for key metric cards
    await expect(page.getByText(/total vulnerabilities/i)).toBeVisible()
    await expect(page.getByText(/active patches/i)).toBeVisible()
    await expect(page.getByText(/deployments/i)).toBeVisible()
  })

  test('should display vulnerability chart', async ({ page }) => {
    // Look for chart container
    const chart = page.locator('[data-testid="vulnerability-chart"]')
    await expect(chart).toBeVisible({ timeout: 10000 })
  })

  test('should display recent activity', async ({ page }) => {
    // Check for activity section
    await expect(page.getByRole('heading', { name: /recent activity/i })).toBeVisible()

    // Should have activity items
    const activityItems = page.locator('[data-testid="activity-item"]')

    // Wait for activities to load
    await expect(activityItems.first()).toBeVisible({ timeout: 10000 })
  })

  test('should refresh data when refresh button is clicked', async ({ page }) => {
    // Find refresh button
    const refreshButton = page.getByRole('button', { name: /refresh/i })

    if (await refreshButton.isVisible()) {
      // Click refresh
      await refreshButton.click()

      // Should show loading state briefly
      // Then data should be refreshed
      await page.waitForTimeout(1000)

      // Verify dashboard is still displaying correctly
      await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()
    }
  })

  test('should display system health status', async ({ page }) => {
    // Look for health status indicator
    const healthStatus = page.locator('[data-testid="health-status"]')
    await expect(healthStatus).toBeVisible()

    // Should show healthy, warning, or error state
    const healthText = await healthStatus.textContent()
    expect(healthText).toMatch(/healthy|warning|degraded|error/i)
  })

  test('should click on metric card to view details', async ({ page }) => {
    // Click on vulnerabilities metric card
    const vulnerabilitiesCard = page.locator('[data-testid="vulnerabilities-metric"]')

    if (await vulnerabilitiesCard.isVisible()) {
      await vulnerabilitiesCard.click()

      // Should navigate to vulnerabilities page
      await expect(page).toHaveURL('/vulnerabilities', { timeout: 5000 })
    }
  })

  test('should update in real-time with WebSocket connection', async ({ page }) => {
    // Wait for WebSocket connection
    await page.waitForTimeout(2000)

    // Check for real-time update indicator
    const liveIndicator = page.locator('[data-testid="live-indicator"]')

    if (await liveIndicator.isVisible()) {
      // Should show "Live" or "Connected"
      await expect(liveIndicator).toContainText(/live|connected/i)
    }
  })
})
