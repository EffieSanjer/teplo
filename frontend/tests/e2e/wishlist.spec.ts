import { expect, test } from '@playwright/test'
import { e2eUser, noOverflow, openApp, wish } from './support'

test.use({ colorScheme: 'light' })

const session = { user: e2eUser, community_id: 'e2e', csrf_token: 'mock' }

test('local login opens the personal board and remembers the theme', async ({ page }) => {
  let loggedIn = false
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/config')
      return route.fulfill({ json: { dev_login_enabled: true, telegram_enabled: false } })
    if (path === '/api/v1/auth/session')
      return loggedIn
        ? route.fulfill({ json: session })
        : route.fulfill({ status: 401, json: { detail: 'Нет сессии' } })
    if (path === '/api/v1/auth/dev') {
      loggedIn = true
      return route.fulfill({ json: session })
    }
    if (path === `/api/v1/users/${e2eUser.id}`) return route.fulfill({ json: e2eUser })
    if (path.endsWith('/items/wishlist'))
      return route.fulfill({
        json: [
          wish({ id: 'gift', title: 'Керамическая ваза' }),
          wish({ id: 'idea', item_type: 'idea', title: 'Выходные у моря' }),
          wish({ id: 'shop', item_type: 'certificate', title: 'Любимый книжный' }),
        ],
      })
    return route.fulfill({ status: 404, json: { detail: 'Not found' } })
  })

  await openApp(page, '/me')
  await page.getByRole('button', { name: 'Войти в локальную версию' }).click()
  await expect(page.locator('header.board-journal h1')).toContainText('Моя доска')
  await expect(page.locator('.collection-grid article')).toHaveCount(2)
  await expect(page.locator('.certificate-carousel article')).toHaveCount(1)

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('navigation', { name: 'Навигация на телефоне' })).toBeVisible()
  expect(await noOverflow(page)).toBe(true)

  await page.locator('.theme-control').click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.reload({ waitUntil: 'domcontentloaded' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('header.board-journal h1')).toContainText('Моя доска')
  expect(await page.evaluate(() => localStorage.getItem('teplo.theme'))).toBe('dark')
})

test('wish detail shows content, toggles priority and opens editing', async ({ page }) => {
  const item = wish({
    id: 'detail-wish',
    title: 'Керамическая ваза',
    description: 'Для цветов по воскресеньям',
    price: '3500',
    currency: 'RUB',
    url: 'https://example.com',
  })
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/config')
      return route.fulfill({ json: { dev_login_enabled: false, telegram_enabled: true } })
    if (path === '/api/v1/auth/session') return route.fulfill({ json: session })
    if (path === `/api/v1/users/${e2eUser.id}`) return route.fulfill({ json: e2eUser })
    if (path.endsWith('/items/wishlist')) return route.fulfill({ json: [item] })
    if (path === '/api/v1/items/detail-wish/priority')
      return route.fulfill({
        json: { ...item, most_wanted: route.request().postDataJSON().most_wanted },
      })
    return route.fulfill({ status: 404, json: { detail: 'Not found' } })
  })

  await openApp(page, '/me')
  await page.getByRole('button', { name: 'Открыть: Керамическая ваза', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.locator('#wish-viewer-title')).toHaveText('Керамическая ваза')
  await expect(dialog).toContainText('Для цветов по воскресеньям')
  await expect(dialog).toContainText('₽')

  await dialog.getByRole('button', { name: 'Очень хочу', exact: true }).click()
  await expect(dialog.getByRole('button', { name: 'Очень хочу', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.locator('article [aria-label="Очень хочу"]')).toBeVisible()

  await dialog.locator('summary[aria-label="Управление желанием"]').click()
  await dialog.getByRole('button', { name: 'Редактировать', exact: true }).click()
  const form = page.getByRole('dialog')
  await expect(form.getByRole('heading', { name: 'Редактировать желание' })).toBeVisible()
  await form.getByRole('button', { name: 'Закрыть' }).click()
  await expect(form).toBeHidden()
})

test('certificate rail stays separate and adds a store without the type switch', async ({
  page,
}) => {
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/config')
      return route.fulfill({ json: { dev_login_enabled: false, telegram_enabled: true } })
    if (path === '/api/v1/auth/session') return route.fulfill({ json: session })
    if (path === `/api/v1/users/${e2eUser.id}`) return route.fulfill({ json: e2eUser })
    if (path.endsWith('/items/wishlist'))
      return route.fulfill({
        json: [wish({ id: 'shop', item_type: 'certificate', title: 'Любимый книжный' })],
      })
    return route.fulfill({ status: 404, json: { detail: 'Not found' } })
  })

  await openApp(page, '/me')
  const rail = page.locator('.certificate-carousel')
  await expect(rail).toBeVisible()
  await expect(rail.locator('article')).toHaveCount(1)
  await expect(page.locator('.collection-grid')).toHaveCount(0)
  await expect(rail.locator('.certificate-carousel-track')).toHaveAttribute('tabindex', '0')

  await rail.locator('.certificate-carousel-add').click()
  const form = page.getByRole('dialog')
  await expect(form.getByRole('heading', { name: 'Магазин для сертификата' })).toBeVisible()
  await expect(form.locator('.type-switch')).toHaveCount(0)
  await form.getByRole('button', { name: 'Закрыть' }).click()
  await expect(form).toBeHidden()
})
