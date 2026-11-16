import { expect, test } from '@playwright/test'

test('personal moodboard cards stay readable and interactive without catalogue controls', async ({ page }) => {
  const user = { id: 'card-preview', display_name: 'Анна', is_friend: false, can_surprise: false }
  const base = {
    recipient_id: user.id, author_id: user.id, author_name: 'Анна', list_type: 'wishlist',
    item_type: 'gift', description: null, url: null, price: null, currency: null,
    image_is_icon: false, price_mode: 'approximate', archived_at: null,
    created_at: '2026-01-01', updated_at: '2026-01-01', can_manage: true,
  }
  await page.route('**/api/v1/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/config') return route.fulfill({ json: { dev_login_enabled: false, telegram_enabled: true } })
    if (path === '/api/v1/auth/session') return route.fulfill({ json: { user, community_id: 'preview', csrf_token: 'mock' } })
    if (path === `/api/v1/users/${user.id}`) return route.fulfill({ json: user })
    if (path.endsWith('/items/wishlist')) return route.fulfill({ json: [
      { ...base, id: 'photo', title: 'Керамическая ваза ручной работы', image_id: 'photo', price: '3200', currency: 'RUB' },
      { ...base, id: 'idea', item_type: 'idea', title: 'Выходные у моря', image_id: null },
      { ...base, id: 'broken', title: 'Любимая книга', image_id: 'missing' },
    ] })
    if (path === '/api/v1/media/photo') return route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000"><rect width="800" height="1000" fill="#c5b8a5"/><ellipse cx="400" cy="550" rx="210" ry="280" fill="#e9dfd0"/></svg>' })
    return route.fulfill({ status: 404, json: { detail: 'Not found' } })
  })
  await page.goto('/me')
  const cards = page.locator('.collection-grid .tile-open')
  await expect(cards).toHaveCount(3)
  for (const theme of ['light', 'dark']) {
    await page.evaluate(value => document.documentElement.dataset.theme = value, theme)
    for (const width of [320, 390, 1440]) {
      await page.setViewportSize({ width, height: 900 })
      await expect(cards.first()).toHaveCSS('border-top-width', '1px')
      await expect(cards.first().locator('.tile-content')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
      await expect(cards.locator('.tile-footer, .tile-price, .tile-arrow, .tile-kind')).toHaveCount(0)
      await expect(cards.nth(1).locator('.wish-note-mark')).toHaveText('На заметку')
      await expect(cards.nth(2)).toHaveClass(/tile-note/)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      for (const card of await cards.all()) {
        expect(await card.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
      }
      await page.screenshot({ path: `test-results/wish-cards-${theme}-${width}.png`, fullPage: true })
    }
  }
  await cards.first().click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByRole('dialog').locator('.detail-card-title')).toHaveText('Керамическая ваза ручной работы')
  await page.getByRole('dialog').getByRole('button', { name: 'Закрыть' }).click()
  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({ width, height: 800 })
    await page.getByRole('button', { name: 'Добавить желание', exact: true }).first().click()
    const formDialog = page.getByRole('dialog')
    await expect(formDialog.locator('.item-form')).toBeVisible()
    await expect(formDialog).toHaveCSS('scrollbar-width', 'none')
    expect(await formDialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
    await formDialog.getByRole('button', { name: 'Добавить желание', exact: true }).scrollIntoViewIfNeeded()
    await expect(formDialog.getByRole('button', { name: 'Добавить желание', exact: true })).toBeVisible()
    await formDialog.evaluate(el => el.scrollTop = 0)
    await page.screenshot({ path: `test-results/add-wish-compact-${width}.png` })
    await formDialog.getByRole('button', { name: 'Закрыть' }).click()
  }
})
