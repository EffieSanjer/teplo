import { expect, test } from '@playwright/test'

test('friends directory supports search, card navigation and separate removal controls', async ({ page }) => {
  const user = { id: 'me', display_name: 'Анна', is_friend: false, can_surprise: false }
  const friends = ['Аня', 'Борис', 'Очень длинное имя друга для проверки переноса'].map((display_name, index) => ({
    id: `friend-${index}`, display_name, is_friend: true, can_surprise: true,
  }))
  await page.route('**/api/v1/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/config') return route.fulfill({ json: { dev_login_enabled: false, telegram_enabled: true } })
    if (path === '/api/v1/auth/session') return route.fulfill({ json: { user, community_id: 'preview', csrf_token: 'mock' } })
    if (path === '/api/v1/users') return route.fulfill({ json: friends })
    if (path === '/api/v1/friends/invitations') return route.fulfill({ json: { url: 'https://t.me/test_bot?start=friend_preview', expires_at: '2026-12-01' } })
    if (path === '/api/v1/users/friend-0') return route.fulfill({ json: friends[0] })
    if (path.endsWith('/items/wishlist') || path.endsWith('/items/surprise')) return route.fulfill({ json: [] })
    return route.fulfill({ status: 404, json: { detail: 'Not found' } })
  })
  await page.goto('/friends')
  const cards = page.locator('.friends-grid .friend-profile')
  await expect(cards).toHaveCount(3)
  await expect(page.locator('.topbar .theme-control')).toHaveCount(0)
  for (const theme of ['light', 'dark']) {
    await page.evaluate(value => document.documentElement.dataset.theme = value, theme)
    for (const width of [320, 390, 1440]) {
      await page.setViewportSize({ width, height: 900 })
      await expect(page.getByRole('button', { name: 'Пригласить друга', exact: true })).toBeVisible()
      await expect(cards.first()).toHaveCSS('backdrop-filter', 'blur(18px)')
      await expect(cards.locator('.friend-visit')).toHaveCount(0)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      for (const card of await cards.all()) expect(await card.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
      await page.screenshot({ path: `test-results/friends-directory-${theme}-${width}.png`, fullPage: true })
    }
  }
  await page.setViewportSize({ width: 320, height: 900 })
  await page.getByRole('button', { name: 'Пригласить друга', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(dialog).toHaveCSS('border-radius', '26px')
  expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
  await expect(dialog.getByRole('button', { name: 'Отправить другу' })).toBeVisible()
  await page.screenshot({ path: 'test-results/friends-invite-notebook.png' })
  await dialog.getByRole('button', { name: 'Закрыть' }).click()
  await page.getByRole('searchbox', { name: 'Найти друга' }).fill('  АНЯ ')
  await expect(cards).toHaveCount(1)
  await page.getByRole('button', { name: 'Очистить поиск' }).click()
  await expect(cards).toHaveCount(3)
  await page.getByRole('button', { name: 'Удалить из друзей: Аня', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page).toHaveURL(/\/friends$/)
  await page.getByRole('button', { name: 'Оставить', exact: true }).click()
  await page.getByRole('link', { name: 'Вишлист: Аня', exact: true }).click()
  await expect(page).toHaveURL(/\/users\/friend-0\/wishlist$/)
  await page.getByRole('link', { name: 'Сюрпризы', exact: true }).click()
  const privacyNote = page.locator('.list-note')
  await expect(privacyNote).toHaveText('Получатель не видит этот список.')
  await expect(page.locator('.friend-profile-actions a').filter({ hasText: 'Сюрпризы' }).locator('.lucide-lock-keyhole-icon')).toHaveCount(0)
  for (const theme of ['light', 'dark']) {
    await page.evaluate(value => document.documentElement.dataset.theme = value, theme)
    const colors = await privacyNote.evaluate(el => ({
      actual: getComputedStyle(el).color,
      expected: (() => {
        const probe = document.createElement('span')
        probe.style.color = 'var(--page-contrast-ink)'
        document.body.append(probe)
        const color = getComputedStyle(probe).color
        probe.remove()
        return color
      })(),
    }))
    expect(colors.actual).toBe(colors.expected)
  }
})
