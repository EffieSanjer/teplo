import { expect, test } from '@playwright/test'
import { e2eUser, noOverflow, openApp } from './support'

test('friends directory supports search, invitations, removal and private surprises', async ({
  page,
}) => {
  const friends = ['Аня', 'Борис', 'Очень длинное имя друга для проверки переноса'].map(
    (display_name, index) => ({
      id: `friend-${index}`,
      display_name,
      is_friend: true,
      can_surprise: true,
    }),
  )
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/config')
      return route.fulfill({ json: { dev_login_enabled: false, telegram_enabled: true } })
    if (path === '/api/v1/auth/session')
      return route.fulfill({
        json: { user: e2eUser, community_id: 'e2e', csrf_token: 'mock' },
      })
    if (path === '/api/v1/users') return route.fulfill({ json: friends })
    if (path === '/api/v1/friends/invitations')
      return route.fulfill({
        json: { url: 'https://t.me/test_bot?start=friend_preview', expires_at: '2026-12-01' },
      })
    if (path === '/api/v1/users/friend-0') return route.fulfill({ json: friends[0] })
    if (path.endsWith('/items/wishlist') || path.endsWith('/items/surprise'))
      return route.fulfill({ json: [] })
    return route.fulfill({ status: 404, json: { detail: 'Not found' } })
  })

  await openApp(page, '/friends')
  const cards = page.locator('.friends-grid article')
  await expect(cards).toHaveCount(3)
  await expect(page.locator('.theme-control')).toHaveCount(0)

  for (const width of [320, 390, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await expect(page.getByRole('button', { name: 'Пригласить друга', exact: true })).toBeVisible()
    expect(await noOverflow(page)).toBe(true)
    for (const card of await cards.all())
      expect(await card.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(true)
  }

  await page.setViewportSize({ width: 390, height: 900 })
  await page.getByRole('button', { name: 'Пригласить друга', exact: true }).click()
  const invite = page.getByRole('dialog')
  await expect(invite).toBeVisible()
  await expect(invite.getByRole('button', { name: 'Отправить другу' })).toBeVisible()
  await invite.getByRole('button', { name: 'Закрыть' }).click()
  await expect(invite).toBeHidden()

  await page.getByRole('searchbox', { name: 'Найти друга' }).fill('  АНЯ ')
  await expect(cards).toHaveCount(1)
  await page.getByRole('button', { name: 'Очистить поиск' }).click()
  await expect(cards).toHaveCount(3)

  await page.getByRole('button', { name: 'Удалить из друзей: Аня', exact: true }).click()
  const removal = page.getByRole('dialog')
  await expect(removal).toBeVisible()
  await expect(page).toHaveURL(/\/friends$/)
  await removal.getByRole('button', { name: 'Оставить', exact: true }).click()
  await expect(removal).toBeHidden()

  await page.getByRole('link', { name: 'Вишлист: Аня', exact: true }).click()
  await expect(page).toHaveURL(/\/users\/friend-0\/wishlist$/)
  await page.getByRole('link', { name: 'Сюрпризы', exact: true }).click()
  await expect(page).toHaveURL(/\/users\/friend-0\/surprises$/)
  await expect(page.locator('.list-note')).toHaveText('Получатель не видит этот список.')

  await page.locator('.collection-add').click()
  const surpriseForm = page.getByRole('dialog')
  await expect(surpriseForm.getByRole('heading', { name: 'Маленький сюрприз' })).toBeVisible()
  await surpriseForm.getByRole('button', { name: 'Закрыть' }).click()
})
