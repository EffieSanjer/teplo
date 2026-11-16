import { expect, test } from '@playwright/test'

test('reference palette is light-only and fits desktop and mobile', async ({ page }) => {
  const user = { id: 'reference-me', display_name: 'Александра', is_friend: false, can_surprise: false }
  await page.emulateMedia({ colorScheme: 'light' })
  await page.route('**/api/v1/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/auth/config')) return route.fulfill({ json: { dev_login_enabled: false, telegram_enabled: true } })
    if (path.endsWith('/auth/session')) return route.fulfill({ json: { user, community_id: 'reference', csrf_token: 'mock' } })
    if (path.endsWith('/items/wishlist')) return route.fulfill({ json: Array.from({ length: 8 }, (_, index) => ({
      id: `reference-${index}`, title: ['Керамическая ваза', 'Выходные у моря', 'Книга об искусстве', 'Маленькая кофейня'][index % 4],
      recipient_id: user.id, author_id: user.id, author_name: user.display_name,
      list_type: 'wishlist', item_type: 'idea', description: null, url: null, price: null,
      currency: null, image_id: null, image_is_icon: false, price_mode: 'approximate',
      archived_at: null, created_at: '2026-01-01', updated_at: '2026-01-01', can_manage: true,
    })) })
    if (path === `/api/v1/users/${user.id}`) return route.fulfill({ json: user })
    return route.fulfill({ status: 404, json: { detail: 'Not found' } })
  })
  await page.goto('/me')
  await expect(page.locator('.collection-tile')).toHaveCount(8)
  await expect(page.locator('html')).toHaveCSS('font-family', /Manrope/)
  await expect(page.locator('.personal-add')).toHaveCSS('background-color', 'rgb(183, 47, 39)')
  await expect(page.locator('.personal-intro')).toHaveCSS('backdrop-filter', 'blur(24px) saturate(1.1)')
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: `test-results/light-reference-${width}.png`, fullPage: true })
  }
  await page.locator('.personal-add').click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.screenshot({ path: 'test-results/light-reference-form.png', fullPage: true })
  await page.getByRole('button', { name: 'Закрыть', exact: true }).click()
  await page.getByRole('button', { name: 'Включить тёмную тему' }).click()
  await expect(page.locator('html')).not.toHaveCSS('font-family', /Manrope/)
  expect(await page.locator('html').evaluate(el => getComputedStyle(el).getPropertyValue('--paper').trim())).toBe('#151515')
})
