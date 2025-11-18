import { test, expect } from '@playwright/test'

/**
 * Navigation E2E Tests
 * Tests navigation between different pages
 */

// Helper function to login
async function login(page) {
  await page.goto('/login')
  await page.getByLabel(/username/i).fill('admin')
  await page.getByLabel(/password/i).fill('admin123')
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL('/')
}

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await login(page)
  })

  test('should navigate to Vulnerabilities page', async ({ page }) => {
    // Click on Vulnerabilities link in navigation
    await page.getByRole('link', { name: /vulnerabilities/i }).click()

    // Should be on vulnerabilities page
    await expect(page).toHaveURL('/vulnerabilities')
    await expect(page.getByRole('heading', { name: /vulnerabilities/i })).toBeVisible()
  })

  test('should navigate to Patches page', async ({ page }) => {
    await page.getByRole('link', { name: /patches/i }).click()

    await expect(page).toHaveURL('/patches')
    await expect(page.getByRole('heading', { name: /patches/i })).toBeVisible()
  })

  test('should navigate to Deployments page', async ({ page }) => {
    await page.getByRole('link', { name: /deployments/i }).click()

    await expect(page).toHaveURL('/deployments')
    await expect(page.getByRole('heading', { name: /deployments/i })).toBeVisible()
  })

  test('should navigate to Analytics page', async ({ page }) => {
    await page.getByRole('link', { name: /analytics/i }).click()

    await expect(page).toHaveURL('/analytics')
    await expect(page.getByRole('heading', { name: /analytics/i })).toBeVisible()
  })

  test('should navigate to Settings page', async ({ page }) => {
    await page.getByRole('link', { name: /settings/i }).click()

    await expect(page).toHaveURL('/settings')
    await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible()
  })

  test('should navigate back to Dashboard from any page', async ({ page }) => {
    // Go to vulnerabilities
    await page.getByRole('link', { name: /vulnerabilities/i }).click()
    await expect(page).toHaveURL('/vulnerabilities')

    // Navigate back to dashboard
    await page.getByRole('link', { name: /dashboard/i }).click()
    await expect(page).toHaveURL('/')
  })

  test('should handle browser back button', async ({ page }) => {
    // Navigate to vulnerabilities
    await page.getByRole('link', { name: /vulnerabilities/i }).click()
    await expect(page).toHaveURL('/vulnerabilities')

    // Use browser back button
    await page.goBack()

    // Should be back on dashboard
    await expect(page).toHaveURL('/')
  })

  test('should handle browser forward button', async ({ page }) => {
    // Navigate to vulnerabilities
    await page.getByRole('link', { name: /vulnerabilities/i }).click()
    await expect(page).toHaveURL('/vulnerabilities')

    // Go back
    await page.goBack()
    await expect(page).toHaveURL('/')

    // Use browser forward button
    await page.goForward()

    // Should be back on vulnerabilities page
    await expect(page).toHaveURL('/vulnerabilities')
  })
})
