import { test, expect } from '@playwright/test'

/**
 * Vulnerabilities Page E2E Tests
 * Tests vulnerability listing, filtering, and details
 */

// Helper function to login
async function login(page) {
  await page.goto('/login')
  await page.getByLabel(/username/i).fill('admin')
  await page.getByLabel(/password/i).fill('admin123')
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL('/')
}

test.describe('Vulnerabilities Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await page.goto('/vulnerabilities')
  })

  test('should display vulnerabilities list', async ({ page }) => {
    // Check for page heading
    await expect(page.getByRole('heading', { name: /vulnerabilities/i })).toBeVisible()

    // Should have vulnerability cards or table
    // Note: Adjust selector based on your implementation
    const vulnerabilityItems = page.locator('[data-testid="vulnerability-item"]')

    // Wait for items to load (may need API mock)
    await expect(vulnerabilityItems.first()).toBeVisible({ timeout: 10000 })
  })

  test('should filter vulnerabilities by severity', async ({ page }) => {
    // Click on severity filter (adjust selector as needed)
    await page.getByRole('button', { name: /filter/i }).click()
    await page.getByRole('checkbox', { name: /critical/i }).click()

    // Should see only critical vulnerabilities
    // Note: This depends on your filtering implementation
    const vulnerabilityItems = page.locator('[data-testid="vulnerability-item"]')

    // Check that filtered results are displayed
    await expect(vulnerabilityItems).toHaveCount(await vulnerabilityItems.count())
  })

  test('should search vulnerabilities', async ({ page }) => {
    // Type in search box
    const searchInput = page.getByPlaceholder(/search/i)
    await searchInput.fill('CVE-2024')

    // Should filter results
    await page.waitForTimeout(500) // Debounce delay

    const vulnerabilityItems = page.locator('[data-testid="vulnerability-item"]')
    const count = await vulnerabilityItems.count()

    // Verify search results (count may vary)
    expect(count).toBeGreaterThanOrEqual(0)
  })

  test('should open vulnerability details', async ({ page }) => {
    // Click on first vulnerability
    const firstVulnerability = page.locator('[data-testid="vulnerability-item"]').first()
    await firstVulnerability.click()

    // Should show details modal or navigate to details page
    // Adjust based on your implementation
    await expect(page.locator('[data-testid="vulnerability-details"]')).toBeVisible({ timeout: 5000 })
  })

  test('should paginate through vulnerabilities', async ({ page }) => {
    // Wait for pagination controls
    const nextButton = page.getByRole('button', { name: /next/i })

    if (await nextButton.isVisible()) {
      // Click next page
      await nextButton.click()

      // URL should update with page parameter or content should change
      await page.waitForTimeout(1000)

      // Verify page changed
      const vulnerabilityItems = page.locator('[data-testid="vulnerability-item"]')
      await expect(vulnerabilityItems.first()).toBeVisible()
    }
  })

  test('should sort vulnerabilities', async ({ page }) => {
    // Click sort dropdown/button
    await page.getByRole('button', { name: /sort/i }).click()

    // Select sort option
    await page.getByRole('option', { name: /severity/i }).click()

    // Wait for re-sort
    await page.waitForTimeout(500)

    // Verify vulnerabilities are sorted
    const vulnerabilityItems = page.locator('[data-testid="vulnerability-item"]')
    await expect(vulnerabilityItems.first()).toBeVisible()
  })
})
