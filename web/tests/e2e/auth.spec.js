import { test, expect } from '@playwright/test'

/**
 * Authentication E2E Tests
 * Tests login, logout, and protected route access
 */

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page before each test
    await page.goto('/login')
  })

  test('should display login page correctly', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/VulnZero/)

    // Check for login form elements
    await expect(page.getByRole('heading', { name: /Welcome to VulnZero/i })).toBeVisible()
    await expect(page.getByLabel(/username/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  })

  test('should show validation errors for empty form', async ({ page }) => {
    // Click sign in without filling form
    await page.getByRole('button', { name: /sign in/i }).click()

    // HTML5 validation should prevent submission
    const usernameInput = page.getByLabel(/username/i)
    await expect(usernameInput).toHaveAttribute('required', '')
  })

  test('should show error for invalid credentials', async ({ page }) => {
    // Fill in invalid credentials
    await page.getByLabel(/username/i).fill('wronguser')
    await page.getByLabel(/password/i).fill('wrongpassword')
    await page.getByRole('button', { name: /sign in/i }).click()

    // Wait for error toast/message
    // Note: Adjust selector based on your toast implementation
    await expect(page.locator('text=/login failed/i')).toBeVisible({ timeout: 5000 })
  })

  test('should successfully login with valid credentials', async ({ page }) => {
    // Fill in valid credentials
    // Note: You'll need to set up test user credentials
    await page.getByLabel(/username/i).fill('admin')
    await page.getByLabel(/password/i).fill('admin123')
    await page.getByRole('button', { name: /sign in/i }).click()

    // Should redirect to dashboard
    await expect(page).toHaveURL('/', { timeout: 10000 })

    // Should see dashboard elements
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()
  })

  test('should logout successfully', async ({ page }) => {
    // First login
    await page.getByLabel(/username/i).fill('admin')
    await page.getByLabel(/password/i).fill('admin123')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page).toHaveURL('/')

    // Click logout button (adjust selector as needed)
    await page.getByRole('button', { name: /logout/i }).click()

    // Should redirect to login page
    await expect(page).toHaveURL('/login')
  })

  test('should redirect to login when accessing protected route while logged out', async ({ page }) => {
    // Try to access dashboard directly
    await page.goto('/')

    // Should redirect to login
    await expect(page).toHaveURL('/login')
  })

  test('should persist authentication after page reload', async ({ page }) => {
    // Login
    await page.getByLabel(/username/i).fill('admin')
    await page.getByLabel(/password/i).fill('admin123')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page).toHaveURL('/')

    // Reload page
    await page.reload()

    // Should still be on dashboard (not redirected to login)
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()
  })
})
