import { expect, test, type Page } from '@playwright/test'

const user = { id: 'design-me', display_name: 'Тест', is_friend: false, can_surprise: false }
const base = {
  recipient_id: user.id, author_id: user.id, author_name: 'Тест', list_type: 'wishlist', item_type: 'gift',
  description: null, url: null, price: null, currency: null, image_is_icon: false,
  price_mode: 'approximate', archived_at: null, created_at: '2026-01-01', updated_at: '2026-01-01', can_manage: true,
}

async function mockApp(page: Page) {
  // Never create sessions, gifts or media in the running database.
  await page.route('**/api/v1/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/config') return route.fulfill({ json: { dev_login_enabled: false, telegram_enabled: true } })
    if (path === '/api/v1/auth/session') return route.fulfill({ json: { user, community_id: 'design-personal', csrf_token: 'mock-csrf' } })
    if (path === `/api/v1/users/${user.id}`) return route.fulfill({ json: user })
    if (path.endsWith('/items/wishlist')) return route.fulfill({ json: [
      { ...base, id: 'portrait', title: 'Вертикальное фото', image_id: 'portrait' },
      { ...base, id: 'landscape', title: 'Горизонтальное фото', image_id: 'landscape' },
      { ...base, id: 'empty', title: 'Только название', image_id: null },
      ...Array.from({ length: 5 }, (_, index) => ({ ...base, id: `shop-${index}`, title: `Магазин ${index + 1}`, item_type: 'certificate', image_id: null })),
    ] })
    if (path.startsWith('/api/v1/media/')) {
      const portrait = path.endsWith('/portrait')
      return route.fulfill({ contentType: 'image/svg+xml', body: `<svg xmlns="http://www.w3.org/2000/svg" width="${portrait ? 600 : 1600}" height="${portrait ? 1200 : 800}"><rect width="100%" height="100%" fill="#d8c2b2"/><circle cx="50%" cy="50%" r="140" fill="#887bb4"/></svg>` })
    }
    return route.fulfill({ status: 500, json: { detail: `Unexpected test request: ${path}` } })
  })
}

test.beforeEach(async ({ page, baseURL }) => {
  await mockApp(page)
  if (baseURL?.includes('.tuna.')) {
    await page.goto('/me', { waitUntil: 'domcontentloaded' })
    if (!await page.locator('#app').count()) {
      await page.getByRole('button', { name: /Посетить/ }).click({ timeout: 20000 })
      await page.locator('#app').waitFor()
    }
  }
})

test('device theme toggles in one click and persists without a selector', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.goto('/me')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('.theme-control select')).toHaveCount(0)
  await page.getByRole('button', { name: 'Включить светлую тему' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.emulateMedia({ colorScheme: 'light' })
  await page.getByRole('button', { name: 'Включить тёмную тему' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  expect(await page.evaluate(() => localStorage.getItem('teplo.theme'))).toBe('dark')
})

test('compact collapsible certificates sit above the gallery and keep menus usable', async ({ page }) => {
  await page.goto('/me')
  const section = page.locator('.certificates-section')
  await expect(section).not.toHaveAttribute('open')
  await expect(section.locator('.count')).toHaveText('5')
  await expect(page.locator('.cards-grid article')).toHaveCount(3)
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 844 })
    expect((await section.boundingBox())!.y).toBeLessThan((await page.locator('.cards-grid').boundingBox())!.y)
    await section.locator('summary.certificates-toggle').click()
    const card = section.locator('article').first()
    await expect(card).toBeVisible()
    expect((await card.boundingBox())!.width).toBeLessThanOrEqual(184)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await card.locator('.card-menu summary').click()
    await expect(card.getByRole('button', { name: 'Редактировать' })).toBeVisible()
    const menu = (await card.locator('.dropdown').boundingBox())!
    expect(menu.x).toBeGreaterThanOrEqual(0)
    expect(menu.x + menu.width).toBeLessThanOrEqual(width)
    await card.locator('.card-menu summary').click()
    if (width === 390) await page.screenshot({ path: 'test-results/design-compact-certificates.png' })
    await section.locator('summary.certificates-toggle').click()
    await expect(card).not.toBeVisible()
  }
})

test('details use a mobile photo background and retain uncropped desktop photos', async ({ page }) => {
  await page.goto('/me')
  await expect(page.locator('.card-bottom')).toHaveCount(0)
  await expect(page.getByText('Бесценно', { exact: true })).toHaveCount(0)
  const dialog = page.getByRole('dialog')
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 844 })
    await page.getByRole('button', { name: 'Открыть: Вертикальное фото', exact: true }).click()
    const image = dialog.locator('.detail-art img')
    await expect(image).toBeVisible()
    await expect.poll(() => image.evaluate(el => (el as HTMLImageElement).naturalWidth)).toBe(600)
    const photo = (await image.boundingBox())!
    expect(photo.height).toBeGreaterThan(500)
    if (width > 640) expect(Math.abs(photo.width / photo.height - .5)).toBeLessThan(.01)
    else {
      await expect(dialog).toHaveCSS('border-radius', '0px')
      const bounds = (await dialog.boundingBox())!
      expect(bounds.width).toBe(width)
      expect(bounds.height).toBeCloseTo(844, 1)
      await expect(dialog).toHaveClass(/detail-portrait/)
      await expect(dialog.locator('.detail-body')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
      await expect(dialog.locator('.detail-body')).toHaveCSS('backdrop-filter', 'none')
      const panel = (await dialog.locator('.detail-body').boundingBox())!
      expect(panel.y).toBeCloseTo(photo.height, 0)
    }
    await expect(image).toHaveCSS('object-fit', 'contain')
    await expect(dialog.locator('.detail-price, .detail-description, .eyebrow, .privacy-note')).toHaveCount(0)
    expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
    await expect(dialog.getByRole('button', { name: 'Редактировать' })).toBeVisible()
    const action = (await dialog.getByRole('button', { name: 'Редактировать' }).boundingBox())!
    if (width > 640) expect(action.y + action.height).toBeLessThanOrEqual(844)
    await dialog.evaluate(el => { el.scrollTop = 0 })
    if (width === 390) {
      await dialog.locator('.detail-body').scrollIntoViewIfNeeded()
      await dialog.evaluate(async el => { await Promise.allSettled(el.getAnimations({ subtree: true }).map(animation => animation.finished)) })
      await page.screenshot({ path: 'test-results/design-portrait-detail.png' })
    }
    await dialog.getByRole('button', { name: 'Закрыть' }).click()
    await page.getByRole('button', { name: 'Открыть: Горизонтальное фото', exact: true }).click()
    await expect.poll(() => dialog.locator('img').evaluate(el => (el as HTMLImageElement).naturalWidth)).toBe(1600)
    if (width === 1440) expect((await dialog.boundingBox())!.width).toBeGreaterThan(590)
    await dialog.getByRole('button', { name: 'Закрыть' }).click()
  }
})

test('clicked and selected buttons have no outline but keyboard focus remains visible', async ({ page }) => {
  await page.goto('/me')
  const theme = page.locator('.theme-control')
  await theme.click()
  await expect(theme).toHaveCSS('outline-style', 'none')
  await expect(theme).toHaveCSS('box-shadow', 'none')
  await page.getByRole('button', { name: 'Добавить желание', exact: true }).click()
  const dialog = page.getByRole('dialog')
  const gift = dialog.locator('.type-switch button').nth(1)
  await gift.click()
  await expect(gift).toHaveClass('selected')
  await expect(gift).toHaveCSS('border-top-width', '0px')
  await expect(gift).toHaveCSS('box-shadow', 'none')
  await expect(gift).toHaveCSS('outline-style', 'none')
  await dialog.getByRole('button', { name: 'Закрыть' }).click()
  await theme.click()
  await page.keyboard.press('Tab')
  const logout = page.getByRole('button', { name: 'Выйти', exact: true })
  await expect(logout).toBeFocused()
  await expect(logout).not.toHaveCSS('box-shadow', 'none')
})

test('friend heading stays fixed through delayed tab loads, rapid switches and revoked access', async ({ page }) => {
  const friend = { id: 'design-friend', display_name: 'Аня', is_friend: true, can_surprise: true }
  let finish: (() => Promise<void>) | undefined
  let denied = false
  await page.route('**/api/v1/users/design-friend', route => denied
    ? route.fulfill({ status: 404, json: { detail: 'Нет доступа' } }) : route.fulfill({ json: friend }))
  await page.route('**/api/v1/users/design-friend/items/surprise', async route => {
    await new Promise<void>(resolve => { finish = async () => { await route.fulfill({ json: [] }); resolve() } })
  })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/users/design-friend/wishlist')
  const heading = page.getByRole('heading', { name: 'Аня', exact: true })
  await expect(heading).toBeVisible()
  const before = (await heading.boundingBox())!
  const tabs = page.locator('.profile-tabs')
  await tabs.getByRole('link', { name: 'Сюрпризы' }).click()
  await expect(page.getByRole('status', { name: 'Загрузка списка' })).toBeVisible()
  await expect(heading).toBeVisible()
  await expect(tabs.getByRole('link', { name: 'Вишлист' })).toBeVisible()
  const during = (await heading.boundingBox())!
  expect(during.x).toBe(before.x)
  expect(during.y).toBe(before.y)
  await expect(page.locator('.page-heading .count')).toHaveCount(0)
  // A late reply must not replace the newly selected wishlist.
  await tabs.getByRole('link', { name: 'Вишлист' }).click()
  await expect(page.locator('.cards-grid article')).toHaveCount(3)
  await finish!()
  await expect(page.locator('.cards-grid article')).toHaveCount(3)
  await expect(heading).toBeVisible()
  await tabs.getByRole('link', { name: 'Сюрпризы' }).click()
  await expect(page.getByRole('status', { name: 'Загрузка списка' })).toBeVisible()
  await finish!()
  await expect(page.getByRole('status', { name: 'Загрузка списка' })).toHaveCount(0)
  await expect(heading).toBeVisible()
  denied = true
  await tabs.getByRole('link', { name: 'Вишлист' }).click()
  await expect(page.getByRole('alert')).toHaveText('Нет доступа')
  await expect(heading).toHaveCount(0)
})

test('all item actions fit one row on narrow screens and reduced motion disables animations', async ({ page }) => {
  await page.route('**/api/v1/users/*/items/wishlist', route => route.fulfill({ json: [
    { ...base, id: 'all-actions', title: 'Проверка действий', image_id: 'portrait', url: 'https://example.com' },
  ] }))
  const friend = { id: 'design-friend', display_name: 'Аня', is_friend: true, can_surprise: true }
  await page.route('**/api/v1/users/design-friend', route => route.fulfill({ json: friend }))
  await page.goto('/users/design-friend/wishlist')
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 844 })
    await page.getByRole('button', { name: 'Открыть: Проверка действий' }).click()
    const dialog = page.getByRole('dialog')
    const buttons = dialog.locator('.detail-actions button')
    await expect(buttons).toHaveCount(3)
    const boxes = await buttons.evaluateAll(elements => elements.map(el => {
      const { x, y, width, height } = el.getBoundingClientRect()
      return { x, y, width, height, fits: el.scrollWidth <= el.clientWidth }
    }))
    expect(new Set(boxes.map(box => Math.round(box.y))).size).toBe(1)
    expect(boxes.every(box => box.fits && box.x >= 0 && box.x + box.width <= width)).toBe(true)
    expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
    await dialog.getByRole('button', { name: 'Закрыть' }).click()
  }
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.getByRole('button', { name: 'Открыть: Проверка действий' }).click()
  await expect(page.getByRole('dialog')).toHaveCSS('animation-name', 'none')
})

test('mobile continuous photo viewer handles square, wide, missing photos and long notes in both themes', async ({ page }) => {
  await page.route('**/api/v1/users/*/items/wishlist', route => route.fulfill({ json: [
    { ...base, id: 'square', title: 'Квадратное фото', image_id: 'square', description: 'Подробная заметка. '.repeat(180), url: 'https://example.com' },
    { ...base, id: 'wide', title: 'Широкое фото', image_id: 'landscape' },
    { ...base, id: 'missing', title: 'Без фотографии', image_id: null },
    { ...base, id: 'broken', title: 'Недоступное фото', image_id: 'broken' },
    { ...base, id: 'icon', title: 'Иконка магазина', image_id: 'square', image_is_icon: true },
  ] }))
  await page.route('**/api/v1/media/square', route => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800"><rect width="800" height="800" fill="#c4a080"/></svg>' }))
  await page.route('**/api/v1/media/broken', route => route.fulfill({ status: 404 }))
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/me')
  for (const theme of ['light', 'dark']) {
    if (await page.locator('html').getAttribute('data-theme') !== theme) await page.locator('.theme-control').click()
    for (const title of ['Квадратное фото', 'Широкое фото', 'Без фотографии', 'Недоступное фото', 'Иконка магазина']) {
      await page.getByRole('button', { name: `Открыть: ${title}`, exact: true }).click()
      const dialog = page.getByRole('dialog')
      await expect(dialog.locator('.detail-mobile-title')).toHaveText(title)
      await expect(dialog.getByRole('button', { name: 'Редактировать' })).toBeVisible()
      await expect(dialog.getByRole('button', { name: 'Закрыть' })).toHaveCSS('backdrop-filter', 'blur(12px)')
      await dialog.evaluate(async el => { await Promise.allSettled(el.getAnimations({ subtree: true }).map(animation => animation.finished)) })
      const panel = (await dialog.locator('.detail-body').boundingBox())!
      expect(panel.x).toBe(0)
      expect(panel.width).toBe(390)
      expect(panel.y + panel.height).toBeCloseTo(844, 0)
      expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
      if (title === 'Квадратное фото') {
        await expect.poll(() => dialog.evaluate(el => (el as HTMLElement).style.getPropertyValue('--photo-tone'))).toBe('rgb(196, 160, 128)')
        expect(await dialog.locator('.detail-copy').evaluate(el => el.scrollHeight > el.clientHeight)).toBe(true)
        await expect(dialog.locator('.detail-description')).toHaveCSS('color', /rgba\(255, 255, 255, 0\.88\)/)
        await page.screenshot({ path: `test-results/mobile-glass-square-${theme}.png` })
      }
      if (title === 'Широкое фото') {
        await expect(dialog.locator('.detail-body')).toHaveCSS('color', 'rgb(255, 255, 255)')
        await page.screenshot({ path: `test-results/mobile-glass-wide-${theme}.png` })
      }
      if (title === 'Недоступное фото') await expect(dialog.locator('.detail-art')).toHaveCount(0)
      if (['Без фотографии', 'Недоступное фото', 'Иконка магазина'].includes(title)) {
        const ink = await page.locator('html').evaluate(el => getComputedStyle(el).color)
        await expect(dialog.locator('.detail-body')).toHaveCSS('color', ink)
      }
      await dialog.getByRole('button', { name: 'Закрыть' }).click()
    }
  }
})

test('mobile reference design blends photo into text without a glass panel edge', async ({ page }) => {
  await page.route('**/api/v1/users/*/items/wishlist', route => route.fulfill({ json: [
    { ...base, id: 'colour', title: 'Контрастное фото', image_id: 'colour', description: 'Заметка о подарке — только то, что добавил владелец.', price: '680', currency: 'RUB', url: 'https://example.com' },
  ] }))
  await page.route('**/api/v1/media/colour', route => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600"><rect width="900" height="600" fill="#38838a"/><path d="M0 350L450 200 900 450V600H0Z" fill="#dca276"/><circle cx="600" cy="480" r="90" fill="#944c70"/></svg>' }))
  await page.goto('/me')
  for (const width of [320, 390]) {
    await page.setViewportSize({ width, height: 844 })
    await page.getByRole('button', { name: 'Открыть: Контрастное фото' }).click()
    const dialog = page.getByRole('dialog')
    const art = dialog.locator('.detail-art')
    await expect(art.locator('img')).toHaveCSS('object-fit', 'contain')
    await expect.poll(() => dialog.evaluate(el => (el as HTMLElement).style.getPropertyValue('--photo-ratio'))).toBe('1.5')
    await dialog.evaluate(async el => { await Promise.allSettled(el.getAnimations({ subtree: true }).map(animation => animation.finished)) })
    const panel = (await dialog.locator('.detail-body').boundingBox())!
    const photo = (await art.boundingBox())!
    expect(photo.width).toBe(width)
    expect(photo.height).toBeCloseTo(width / 1.5, 0)
    expect(panel.y).toBeCloseTo(photo.height, 0)
    expect(panel.y + panel.height).toBeCloseTo(844, 0)
    expect(panel.width).toBe(width)
    await expect(dialog.locator('.detail-body')).toHaveCSS('border-bottom-left-radius', '0px')
    await expect(dialog.locator('.detail-body')).toHaveCSS('border-top-left-radius', '0px')
    await expect(dialog.locator('.detail-body')).toHaveCSS('backdrop-filter', 'none')
    await expect(dialog.locator('.detail-body')).toHaveCSS('box-shadow', 'none')
    await expect(dialog.locator('.detail-body')).toHaveCSS('position', 'relative')
    await expect(dialog.locator('.detail-body')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
    const layers = await art.evaluate(el => ({
      blur: getComputedStyle(el, '::before').filter,
      mask: getComputedStyle(el, '::before').maskImage,
      shade: getComputedStyle(el, '::after').backgroundImage,
    }))
    expect(layers.blur).toBe('blur(12px)')
    expect(layers.mask).toContain('linear-gradient')
    expect(layers.shade).toContain('linear-gradient')
    const title = (await dialog.locator('.detail-mobile-title').boundingBox())!
    const price = (await dialog.locator('.detail-price').boundingBox())!
    expect(price.y).toBeGreaterThanOrEqual(title.y + title.height)
    expect(price.x).toBeCloseTo(title.x, 0)
    await expect(dialog.locator('.detail-price')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
    await dialog.evaluate(async el => { await Promise.allSettled(el.getAnimations({ subtree: true }).map(animation => animation.finished)) })
    await page.screenshot({ path: `test-results/mobile-glass-continuation-${width}.png` })
    await dialog.getByRole('button', { name: 'Закрыть' }).click()
  }
})
