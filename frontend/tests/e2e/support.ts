import type { Page } from '@playwright/test'

// The public tunnel can show an interstitial before the app. API calls are
// mocked per test, so this never creates sessions or gifts in the real database.
export async function openApp(page: Page, path = '/me') {
  await page.goto(path, { waitUntil: 'domcontentloaded' })
  const visit = page.getByRole('button', { name: /Посетить/ })
  if (await visit.isVisible().catch(() => false)) {
    await visit.click({ timeout: 20000 })
    await page.locator('#app').waitFor({ timeout: 20000 })
  }
}

export function wish(overrides: Record<string, unknown> = {}) {
  return {
    id: 'wish',
    recipient_id: 'e2e-user',
    author_id: 'e2e-user',
    author_name: 'Анна',
    list_type: 'wishlist',
    item_type: 'gift',
    title: null,
    description: null,
    url: null,
    price: null,
    currency: null,
    image_id: null,
    image_is_icon: false,
    price_mode: 'approximate',
    archived_at: null,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
    can_manage: true,
    can_reserve: false,
    reservation: null,
    most_wanted: false,
    surprise_visibility: 'friends',
    ...overrides,
  }
}

export const e2eUser = {
  id: 'e2e-user',
  display_name: 'Анна',
  is_friend: false,
  can_surprise: false,
}

export function noOverflow(page: Page) {
  return page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
}
