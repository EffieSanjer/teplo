import { expect, test } from '@playwright/test'

test.use({ colorScheme: 'light' })

test('Kstati branding and concept fit both themes and narrow screens', async ({ page }) => {
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await expect(page).toHaveTitle('Кстати — это тебе идеально подойдёт')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Кстати, это тебеидеально подойдёт.')
  await expect(page.locator('.login-brand')).toHaveText('кстати,')
  for (const theme of ['light', 'dark']) {
    await page.getByRole('combobox', { name: 'Тема оформления' }).selectOption(theme)
    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 844 })
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      if (width === 390) await page.screenshot({ path: `test-results/kstati-login-${theme}.png`, fullPage: true })
    }
  }
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  await expect(page.getByRole('heading', { name: 'Мой вишлист', exact: true })).toBeVisible()
  await expect(page.getByText('То, в чём друзья узнают вас.')).toBeVisible()
  await expect(page.locator('.topbar .brand')).toHaveText('кстати,')
  await expect(page.locator('.brand-description')).toHaveText('Желания и находки для друзей')
  await page.setViewportSize({ width: 1100, height: 844 })
  const brand = page.locator('.topbar .brand')
  await expect(brand).toHaveText('кстати,')
  expect(await brand.evaluate(el => el.getBoundingClientRect().right <= el.parentElement!.getBoundingClientRect().right)).toBe(true)
  await expect(page.locator('.main-nav')).toBeVisible()
})

test('theme follows device, remembers manual selection and styles dark forms and photos', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  const html = page.locator('html')
  const control = page.getByRole('combobox', { name: 'Тема оформления' })
  await expect(html).toHaveAttribute('data-theme', 'dark')
  await expect(control).toHaveValue('system')
  await expect(html).toHaveCSS('background-color', 'rgb(29, 27, 25)')
  await page.emulateMedia({ colorScheme: 'light' })
  await expect(html).toHaveAttribute('data-theme', 'light')
  await control.selectOption('dark')
  await page.reload({ waitUntil: 'domcontentloaded' })
  await expect(control).toHaveValue('dark')
  await expect(html).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  await expect(page.getByRole('heading', { name: 'Мой вишлист', exact: true })).toBeVisible()
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 844 })
    await expect(control).toBeVisible()
    await expect(page.locator('.gift-card').first()).toHaveCSS('background-color', 'rgb(41, 38, 35)')
    await expect(page.locator('.art-photo').first()).toHaveCSS('background-color', 'rgb(255, 255, 255)')
    await expect(page.locator('.art-photo img').first()).toHaveCSS('filter', 'none')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    if (width !== 320) await page.screenshot({ path: `test-results/dark-wishlist-${width}.png`, fullPage: true })
  }
  await page.getByRole('button', { name: 'Добавить желание', exact: true }).first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toHaveCSS('background-color', 'rgb(41, 38, 35)')
  await expect(dialog.getByLabel('Название')).toHaveCSS('color', 'rgb(243, 237, 229)')
  await expect(dialog.locator('.upload-button > svg')).toHaveCSS('background-color', 'rgb(255, 139, 77)')
  await dialog.getByLabel('Название').fill('Проверка тёмной темы без сохранения')
  await page.screenshot({ path: 'test-results/dark-form.png', fullPage: true })
  await dialog.getByRole('button', { name: 'Отмена', exact: true }).click()
  await control.selectOption('light')
  await page.emulateMedia({ colorScheme: 'dark' })
  await expect(html).toHaveAttribute('data-theme', 'light')
  await control.selectOption('system')
  await expect(html).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('navigation', { name: 'Навигация на телефоне' }).getByRole('link', { name: 'Друзья' }).click()
  await expect(page.locator('.friend-card').first()).toHaveCSS('background-color', 'rgb(41, 38, 35)')
})

test('masonry cards follow original photo proportions without cropping or zooming', async ({ page }) => {
  await page.route('**/api/v1/users/*/items/wishlist', route => route.fulfill({ json: [
    { id: 'landscape', image_id: 'landscape', title: 'Горизонтальное фото' },
    { id: 'portrait', image_id: 'portrait', title: 'Вертикальное фото' },
    { id: 'square', image_id: 'square', title: 'Квадратное фото' },
    { id: 'idea', image_id: null, title: 'Очень длинное название желания для проверки компактной галереи на узком экране' },
    { id: 'extra-1', image_id: null, title: 'Ещё одна идея' },
    { id: 'extra-2', image_id: null, title: 'Ещё один подарок' },
    { id: 'extra-3', image_id: null, title: 'Новая находка' },
    { id: 'extra-4', image_id: null, title: 'Что-то для хобби' },
  ].map(item => ({ ...item, recipient_id: '11111111-1111-4111-8111-111111111111', author_id: 'author', author_name: 'Автор',
    list_type: 'wishlist', item_type: 'gift', description: 'Личные подробности остаются внутри желания', url: 'https://example.com', price: null,
    currency: null, price_mode: 'approximate', archived_at: null, created_at: '2026-01-01', updated_at: '2026-01-01', can_manage: true,
  })) }))
  await page.route('**/api/v1/media/*', route => {
    const landscape = route.request().url().endsWith('/landscape')
    const square = route.request().url().endsWith('/square')
    return route.fulfill({ contentType: 'image/svg+xml', body: `<svg xmlns="http://www.w3.org/2000/svg" width="${landscape ? 600 : 300}" height="${landscape || square ? 300 : 600}"><rect width="100%" height="100%" fill="#6246c5"/></svg>` })
  })
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  for (const [width, columns] of [[1440, 4], [1280, 4], [1100, 3], [768, 2], [390, 2], [360, 2], [320, 2]]) {
    await page.setViewportSize({ width, height: 844 })
    const grid = page.locator('.cards-grid').first()
    expect(await grid.evaluate(el => getComputedStyle(el).gridTemplateColumns.split(' ').length)).toBe(columns)
    const landscape = grid.locator('.photo-landscape')
    const portrait = grid.locator('.photo-portrait')
    await expect(landscape).toHaveCSS('object-fit', 'contain')
    await expect(portrait).toHaveCSS('object-fit', 'contain')
    await expect(portrait).toHaveCSS('transform', 'none')
    await expect(portrait).toHaveCSS('object-position', '50% 50%')
    await expect(page.locator('.photo-square')).toHaveCSS('object-fit', 'contain')
    for (const image of [landscape, portrait, grid.locator('.photo-square')]) {
      await expect.poll(() => image.evaluate(el => {
        const img = el as HTMLImageElement
        const frame = img.parentElement!.getBoundingClientRect()
        return Math.abs(frame.width / frame.height - img.naturalWidth / img.naturalHeight)
      })).toBeLessThan(0.02)
    }
    await expect.poll(async () => grid.locator('article').evaluateAll(elements => {
      const cards = elements.map(el => el.getBoundingClientRect())
      const gap = parseFloat(getComputedStyle(elements[0].parentElement!).columnGap)
      return cards.every((card, index) => {
        const above = cards.filter((other, otherIndex) => otherIndex !== index && Math.abs(other.x - card.x) < 1 && other.y < card.y)
        const previousBottom = above.length ? Math.max(...above.map(other => other.bottom)) : cards[0].top - gap
        return Math.abs(card.top - previousBottom - gap) <= 2
      })
    })).toBe(true)
    await expect(page.locator('.card-body p')).toHaveCount(0)
    for (const card of await grid.locator('article').all()) {
      expect(await card.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
    }
    for (const menu of [grid.locator('summary').first(), grid.locator('summary').last()]) {
      await menu.click()
      const dropdown = menu.locator('..').locator('.dropdown')
      const bounds = await dropdown.boundingBox()
      expect(bounds).not.toBeNull()
      expect(bounds!.x).toBeGreaterThanOrEqual(0)
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width)
      await menu.click()
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    if (width === 1440 || width === 390) {
      await page.screenshot({ path: `test-results/masonry-${width}.png`, fullPage: true })
    }
  }
  await page.getByRole('button', { name: 'Открыть: Вертикальное фото', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText('Личные подробности остаются внутри желания')
  await expect(page.getByRole('dialog').getByAltText('Вертикальное фото')).toHaveCSS('object-fit', 'contain')
  await expect(page.getByRole('dialog').getByAltText('Вертикальное фото')).toHaveCSS('transform', 'none')
})

test('site icons stay small in cards, certificates, archive, details and editing', async ({ page }) => {
  await page.route('**/api/v1/users/*/items/wishlist', route => route.fulfill({ json: [
    { id: 'icon', image_id: 'tiny', image_is_icon: true, item_type: 'gift', title: 'Значок сайта' },
    { id: 'logo', image_id: 'large-logo', image_is_icon: true, item_type: 'certificate', title: 'Магазин' },
    { id: 'old', image_id: 'tiny', image_is_icon: false, item_type: 'gift', title: 'Старый значок', archived_at: '2026-02-01' },
    { id: 'photo', image_id: 'photo', image_is_icon: false, item_type: 'gift', title: 'Обычное фото' },
  ].map(item => ({ recipient_id: '11111111-1111-4111-8111-111111111111', author_id: 'author', author_name: 'Автор',
    list_type: 'wishlist', description: null, url: 'https://example.com', price: null, currency: null,
    price_mode: 'approximate', archived_at: null, created_at: '2026-01-01', updated_at: '2026-01-01', can_manage: true,
    ...item,
  })) }))
  await page.route('**/api/v1/media/*', route => {
    const size = route.request().url().endsWith('/tiny') ? 32 : 800
    return route.fulfill({ contentType: 'image/svg+xml',
      body: `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect width="100%" height="100%" fill="#ff7838"/></svg>` })
  })
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  for (const theme of ['light', 'dark']) {
    await page.getByRole('combobox', { name: 'Тема оформления' }).selectOption(theme)
    for (const width of [1440, 320]) {
      await page.setViewportSize({ width, height: 844 })
      for (const [title, size] of [['Значок сайта', 32], ['Магазин', 64], ['Старый значок', 32]] as const) {
        const image = page.locator('article').filter({ hasText: title }).locator('img')
        await expect(image).toHaveCSS('width', `${size}px`)
        await expect(image).toHaveCSS('height', `${size}px`)
        await expect(image).toHaveCSS('object-fit', 'contain')
        expect(await image.evaluate(el => {
          const image = el.getBoundingClientRect(), frame = el.parentElement!.getBoundingClientRect()
          return Math.abs(image.x + image.width / 2 - frame.x - frame.width / 2) < 1
        })).toBe(true)
      }
      const photo = page.locator('article').filter({ hasText: 'Обычное фото' }).locator('img')
      expect((await photo.boundingBox())!.width).toBeGreaterThan(100)
    }
  }
  await page.getByRole('button', { name: 'Открыть: Значок сайта', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByAltText('Значок сайта')).toHaveCSS('width', '32px')
  await expect(dialog.locator('.detail-art')).toHaveCSS('height', '128px')
  await dialog.getByRole('button', { name: 'Редактировать', exact: true }).click()
  await expect(dialog.getByAltText('Фотография подарка')).toHaveCSS('width', '32px')
  await dialog.getByRole('button', { name: 'Отмена', exact: true }).click()
})

test('local login, CRUD, archive and friend surprise', async ({ page }) => {
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  await expect(page.getByRole('heading', { name: 'Мой вишлист', exact: true })).toBeVisible()
  await expect(page.locator('.page-heading .count')).toBeVisible()
  await expect(page.locator('.add-button')).toHaveCSS('background-color', 'rgb(185, 74, 40)')
  await expect(page.locator('html')).toHaveCSS('background-color', 'rgb(246, 244, 239)')
  const title = `Проверка ${Date.now()}`
  await page.getByRole('button', { name: 'Добавить желание', exact: true }).first().click()
  await page.getByLabel('Название').fill(title)
  await page.getByLabel('Заметка').fill('Проверка создания и архивирования')
  await page.getByRole('dialog').getByRole('button', { name: 'Добавить желание' }).click()
  await expect(page.getByRole('heading', { name: title })).toBeVisible()
  await page.getByLabel(`Управление: ${title}`).click()
  await page.locator('article').filter({ hasText: title }).getByRole('button', { name: 'В архив', exact: true }).click()
  const card = page.locator('article').filter({ hasText: title })
  await expect(card).toHaveClass(/archived/)
  await expect(page.locator('.cards-grid').first().locator('article').filter({ hasText: title })).toHaveCount(1)
  await expect(page.locator('.archive-heading')).toHaveCount(0)
  await expect(card.getByRole('button', { name: `Открыть: ${title}` })).toHaveCount(0)
  await page.getByLabel(`Управление: ${title}`).click()
  await card.getByRole('button', { name: 'Восстановить' }).click()
  await expect(card).not.toHaveClass(/archived/)
  await page.getByLabel(`Управление: ${title}`).click()
  await card.getByRole('button', { name: 'Удалить', exact: true }).click()
  await page.getByRole('button', { name: 'Удалить навсегда' }).click()
  await expect(page.getByRole('heading', { name: title })).toHaveCount(0)
  await page.getByRole('navigation', { name: 'Основная навигация' }).getByRole('link', { name: 'Друзья' }).click()
  await page.getByRole('link', { name: /Аня Смирнова/ }).click()
  await page.getByRole('link', { name: 'Сюрпризы' }).click()
  await expect(page.getByText('Тсс… здесь живут сюрпризы для того самого «это точно твоё».', { exact: true })).toBeVisible()
  await expect(page.getByText('Видят друзья, но не получатель.')).toBeVisible()
  await page.getByRole('button', { name: 'Добавить сюрприз' }).click()
  await expect(page.getByRole('dialog').getByLabel('Заметка')).toHaveAttribute('placeholder', 'Почему это точно в его или её вкусе?')
  await page.getByLabel('Название').fill(title)
  await page.getByRole('dialog').getByRole('button', { name: 'Добавить желание' }).click()
  await expect(page.getByRole('status')).toHaveText('Сохранено для того самого «это точно твоё»')
  await expect(page.getByRole('heading', { name: title })).toBeVisible()
  await page.getByLabel(`Управление: ${title}`).click()
  await page.locator('article').filter({ hasText: title }).getByRole('button', { name: 'Удалить', exact: true }).click()
  await page.getByRole('button', { name: 'Удалить навсегда' }).click()
  await expect(page.getByRole('heading', { name: title })).toHaveCount(0)
  await page.screenshot({ path: 'test-results/friends-surprises.png', fullPage: true })
})

test('mobile layout and own-surprises redirect', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  await expect(page.getByRole('heading', { name: 'Мой вишлист', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Сюрпризы', exact: true })).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/mobile-wishlist.png', fullPage: true })
  await page.goto('/users/11111111-1111-4111-8111-111111111111/surprises', { waitUntil: 'domcontentloaded' })
  await expect(page).toHaveURL(/\/me$/)
})

test('compact mobile frame leaves the first screen for cards and keeps actions accessible', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 700 })
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  const control = page.getByRole('combobox', { name: 'Тема оформления' })
  const nav = page.getByRole('navigation', { name: 'Навигация на телефоне' })
  for (const theme of ['light', 'dark']) {
    await control.selectOption(theme)
    for (const width of [390, 360, 320]) {
      await page.setViewportSize({ width, height: 700 })
      await page.evaluate(() => scrollTo(0, 0))
      const grid = page.locator('.cards-grid').first()
      await expect(grid.locator('article').first()).toBeVisible()
      expect((await grid.boundingBox())!.y).toBeLessThanOrEqual(176)
      await expect(page.locator('.brand-description')).toBeVisible()
      await expect(page.locator('.page-caption')).toHaveText('То, в чём друзья узнают вас.')
      expect((await nav.boundingBox())!.height).toBeLessThanOrEqual(60)
      await expect(nav.getByRole('link')).toHaveCount(2)
      for (const action of [control, page.getByRole('button', { name: 'Выйти', exact: true }), page.getByRole('button', { name: 'Добавить желание', exact: true })]) {
        await expect(action).toBeVisible()
        const box = (await action.boundingBox())!
        expect(box.width).toBeGreaterThanOrEqual(44)
        expect(box.height).toBeGreaterThanOrEqual(44)
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      if (width === 390) await page.screenshot({ path: `test-results/compact-${theme}-390.png` })
    }
  }
  await page.getByRole('button', { name: 'Добавить желание', exact: true }).click()
  await expect(page.getByRole('dialog').getByLabel('Заметка')).toHaveAttribute('placeholder', 'Что друзьям стоит о вас знать?')
  await expect(page.getByRole('dialog').getByRole('button', { name: 'Добавить фото', exact: false })).toBeVisible()
  await page.getByRole('dialog').getByRole('button', { name: 'Отмена', exact: true }).click()
  await nav.getByRole('link', { name: 'Друзья' }).click()
  await expect(page.getByRole('heading', { name: 'Друзья', exact: true })).toBeVisible()
  await expect(page.getByText('Находки, в которых узнаёшь человека.')).toBeVisible()
  await page.getByRole('textbox', { name: 'Найти друга' }).fill('Аня')
  await expect(page.locator('.friend-card')).toHaveCount(1)
  await page.screenshot({ path: 'test-results/compact-friends-320.png' })
  await page.getByRole('link', { name: /Аня Смирнова/ }).click()
  await expect(page.getByRole('heading', { name: 'Аня Смирнова', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Сюрпризы' }).click()
  await expect(page.getByRole('heading', { name: 'Аня Смирнова', exact: true })).toBeVisible()
  await expect(page.getByText('Тсс… здесь живут сюрпризы для того самого «это точно твоё».', { exact: true })).toBeVisible()
  await expect(page.locator('.surprise-caption')).toHaveCount(0)
  await expect(page.getByText('Видят друзья, но не получатель.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Добавить сюрприз' })).toBeVisible()
  await nav.getByRole('link', { name: 'Вишлист', exact: true }).click()
  await expect(page).toHaveURL(/\/me$/)
  await page.getByRole('button', { name: 'Выйти', exact: true }).click()
  await expect(page.getByRole('button', { name: /Войти в локальную/ })).toBeVisible()
})

test('pasting shared text extracts a URL and fills only empty fields without a blur', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  let unavailable = false
  await page.route('**/api/v1/metadata', async route => {
    expect(route.request().postDataJSON()).toEqual({ url: 'https://www.instagram.com/reel/Abc/?igsh=share' })
    await route.fulfill({ json: unavailable
      ? { warning: 'Сайт не предоставил фото. Ссылку можно сохранить — добавьте фото вручную.' }
      : { title: 'Находка по ссылке', price: '1200', currency: 'RUB', image_id: 'shared-preview' } })
  })
  await page.route('**/api/v1/media/shared-preview', route => route.fulfill({
    contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="150"><rect width="100%" height="100%" fill="#b94a28"/></svg>',
  }))
  await page.route('**/api/v1/items', async route => {
    expect(route.request().postDataJSON()).toMatchObject({ url: 'https://www.instagram.com/reel/Abc/?igsh=share', description: 'Мой комментарий', title: 'Моя находка' })
    await route.fulfill({ status: 201, json: {} })
  })
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 })
    await page.getByRole('button', { name: 'Добавить желание', exact: true }).first().click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('Заметка').fill('Мой комментарий')
    const url = dialog.locator('input[type="url"]')
    await url.evaluate(el => {
      const clipboardData = new DataTransfer()
      clipboardData.setData('text/plain', 'Смотри, что нашёл!\nhttps://www.instagram.com/reel/Abc/?igsh=share\nПоделиться')
      el.dispatchEvent(new ClipboardEvent('paste', { clipboardData, bubbles: true, cancelable: true }))
    })
    await expect(url).toHaveValue('https://www.instagram.com/reel/Abc/?igsh=share')
    if (!unavailable) {
      await expect(dialog.getByLabel('Название')).toHaveValue('Находка по ссылке')
      await expect(dialog.getByAltText('Фотография подарка')).toBeVisible()
    } else {
      await expect(dialog.getByRole('status')).toContainText('Сайт не предоставил фото')
    }
    await expect(dialog.getByLabel('Заметка')).toHaveValue('Мой комментарий')
    await dialog.getByLabel('Название').fill('Моя находка')
    await dialog.getByRole('button', { name: 'Добавить желание', exact: true }).click()
    await expect(dialog).toHaveCount(0)
    unavailable = true
  }
})

test('compact add form keeps source warnings and errors visible in both themes', async ({ page }) => {
  let warning = false
  let finish: (() => void) | undefined
  await page.route('**/api/v1/metadata', async route => {
    await new Promise<void>(resolve => { finish = resolve })
    await route.fulfill(warning
      ? { json: { warning: 'Сайт не предоставил фото. Добавьте фото вручную.' } }
      : { status: 422, json: { detail: 'Не удалось загрузить публикацию' } })
  })
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  for (const theme of ['light', 'dark']) {
    await page.getByRole('combobox', { name: 'Тема оформления' }).selectOption(theme)
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 740 })
      await page.getByRole('button', { name: 'Добавить желание', exact: true }).first().click()
      const dialog = page.getByRole('dialog')
      const source = dialog.locator('input[type="url"]')
      const photo = dialog.locator('.upload-area')
      const name = dialog.getByLabel('Название')
      await expect(dialog.getByRole('heading')).toHaveCount(1)
      await expect(dialog.locator('.type-switch .selected')).toHaveCSS('background-color', theme === 'light' ? 'rgb(255, 120, 56)' : 'rgb(255, 139, 77)')
      await expect(dialog.locator('.form-actions .primary')).toHaveCSS('color', 'rgb(52, 23, 12)')
      for (const field of [source, name, dialog.getByLabel('Заметка')]) {
        await field.focus()
        await expect(field === source ? dialog.locator('.input-with-icon') : field).toHaveCSS('border-top-color', theme === 'light' ? 'rgb(188, 66, 13)' : 'rgb(255, 156, 104)')
      }
      await expect(dialog.locator('.identity-section')).toHaveCSS('border-top-width', '0px')
      await source.focus()
      await dialog.evaluate(el => el.scrollTop = 0)
      await page.screenshot({ path: `test-results/modern-add-${theme}-${width}.png` })
      expect((await source.boundingBox())!.y).toBeLessThan((await name.boundingBox())!.y)
      expect((await photo.boundingBox())!.y).toBeLessThan((await source.boundingBox())!.y)
      expect((await photo.boundingBox())!.height).toBeLessThan(90)
      await expect(name).toBeInViewport()
      const minimum = dialog.getByRole('button', { name: 'Цена от указанной суммы' })
      await minimum.click()
      await expect(minimum).toHaveAttribute('aria-pressed', 'true')
      await dialog.getByRole('spinbutton').fill('1200')
      const priceBounds = (await dialog.locator('.price-input-row').boundingBox())!
      expect(priceBounds.width).toBeLessThan(width)
      expect(await dialog.locator('.price-input-row').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
      await page.screenshot({ path: `test-results/inline-price-${theme}-${width}.png` })
      await source.fill('https://example.com/product')
      await dialog.locator('.metadata-button').click()
      // The response arrives after the user has moved to the bottom of the form.
      await dialog.getByRole('spinbutton').scrollIntoViewIfNeeded()
      await expect.poll(() => !!finish).toBe(true)
      finish!()
      finish = undefined
      const feedback = dialog.locator('.source-section').getByRole(warning ? 'status' : 'alert')
      await expect(feedback).toBeInViewport({ ratio: 1 })
      await expect(dialog.getByRole('heading', { name: 'Новое желание', exact: true })).toBeInViewport({ ratio: 1 })
      await expect(dialog.getByRole('button', { name: 'Закрыть', exact: true })).toBeInViewport({ ratio: 1 })
      await expect(source).toBeInViewport({ ratio: 1 })
      await expect.poll(() => dialog.evaluate(el => el.scrollTop)).toBe(0)
      expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
      await page.screenshot({ path: `test-results/compact-add-${theme}-${width}.png` })
      await dialog.getByRole('button', { name: 'Отмена', exact: true }).click()
      warning = !warning
    }
  }
})

test('share caption supplies missing title and price without a site icon fallback', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 })
  await page.route('**/api/v1/metadata', route => route.fulfill({ json: {
    image_id: null, warning: 'Не удалось загрузить фото. Ссылку можно сохранить, а фото добавить вручную.',
  } }))
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  await page.getByRole('button', { name: 'Добавить желание', exact: true }).first().click()
  const dialog = page.getByRole('dialog')
  await dialog.locator('input[type="url"]').evaluate(el => {
    const clipboardData = new DataTransfer()
    clipboardData.setData('text/plain', 'Керамическая чашка\nот 1 290,50 ₽\nhttps://shop.example/item')
    el.dispatchEvent(new ClipboardEvent('paste', { clipboardData, bubbles: true, cancelable: true }))
  })
  await expect(dialog.getByLabel('Название')).toHaveValue('Керамическая чашка')
  await expect(dialog.getByRole('spinbutton')).toHaveValue('1290.50')
  await expect(dialog.locator('.price-from')).toHaveAttribute('aria-pressed', 'true')
  await expect(dialog.getByLabel('Заметка')).toHaveValue('')
  await expect(dialog.getByAltText('Фотография подарка')).toHaveCount(0)
  await expect(dialog.getByRole('status')).toContainText('Не удалось загрузить фото')
  await dialog.getByRole('button', { name: 'Отмена', exact: true }).click()
})

test('image URL import shows a centered preview without changing the product URL', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route('**/api/v1/media/from-url', async route => {
    expect(route.request().postDataJSON()).toEqual({ url: 'https://example.com/photo.png' })
    await route.fulfill({ status: 201, json: { id: 'url-photo-preview' } })
  })
  await page.route('**/api/v1/media/url-photo-preview', route => route.fulfill({
    contentType: 'image/png',
    body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64'),
  }))
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  await page.getByRole('button', { name: 'Добавить желание', exact: true }).first().click()
  const dialog = page.getByRole('dialog')
  await dialog.locator('.photo-url-details summary').click()
  await dialog.getByLabel('Или загрузите фото по ссылке').fill('https://example.com/photo.png')
  await dialog.getByRole('button', { name: 'Загрузить фото', exact: true }).click()
  const preview = dialog.getByAltText('Фотография подарка')
  await expect(preview).toBeVisible()
  await expect(preview).toHaveCSS('object-fit', 'contain')
  await expect(preview).toHaveCSS('object-position', '50% 50%')
  expect((await dialog.locator('.upload-area').boundingBox())!.height).toBeLessThan(100)
  await expect(dialog.getByPlaceholder('https://магазин.ru/тот-самый-подарок')).toHaveValue('')
  await expect(dialog.getByLabel('Или загрузите фото по ссылке')).toHaveValue('')
  expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
  await dialog.getByRole('button', { name: 'Убрать фото' }).click()
  await expect(preview).toHaveCount(0)
  await dialog.getByRole('button', { name: 'Отмена', exact: true }).click()
})

test('certificate rail scrolls independently and archived cards stay in the main gallery', async ({ page }) => {
  const item = { recipient_id: '11111111-1111-4111-8111-111111111111', author_id: 'author', author_name: 'Автор', list_type: 'wishlist',
    description: '', url: 'https://example.com', price: null, currency: null, price_mode: 'approximate', image_id: null,
    archived_at: null as string | null, created_at: '2026-01-01', updated_at: '2026-01-01', can_manage: true }
  let data = [
    { ...item, id: 'wish', item_type: 'idea', title: 'Активное желание' },
    { ...item, id: 'archived', item_type: 'gift', title: 'Архивное желание', archived_at: '2026-01-02' },
    { ...item, id: 'archived-certificate', item_type: 'certificate', title: 'Архивный сертификат', archived_at: '2026-01-02' },
    ...Array.from({ length: 7 }, (_, index) => ({ ...item, id: `shop-${index}`, item_type: 'certificate', title: `Магазин ${index + 1}` })),
  ]
  await page.route('**/api/v1/users/*/items/wishlist', route => route.fulfill({ json: data }))
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  const gallery = page.locator('.cards-grid')
  const rail = page.getByRole('group', { name: /горизонтальная лента/ })
  await expect(gallery).toHaveCount(1)
  await expect(gallery.locator('article')).toHaveCount(3)
  await expect(gallery.locator('article.archived')).toHaveCount(2)
  await expect(rail.locator('article')).toHaveCount(7)
  await expect(page.getByRole('heading', { name: 'Архив', exact: true })).toHaveCount(0)
  for (const theme of ['light', 'dark']) {
    await page.getByRole('combobox', { name: 'Тема оформления' }).selectOption(theme)
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 844 })
      expect(await rail.evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await rail.locator('article').last().getByRole('heading').scrollIntoViewIfNeeded()
      expect(await rail.evaluate(el => el.scrollLeft)).toBeGreaterThan(0)
      const menu = rail.locator('summary').last()
      await menu.click()
      const dropdown = rail.locator('.dropdown').last()
      await expect(dropdown.getByRole('button', { name: 'Редактировать' })).toBeVisible()
      const bounds = (await dropdown.boundingBox())!
      expect(bounds.x).toBeGreaterThanOrEqual(0)
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(width)
      expect(bounds.y + bounds.height).toBeLessThanOrEqual(844)
      await menu.click()
      if (width === 390) await page.screenshot({ path: `test-results/certificate-rail-${theme}.png` })
    }
  }
  // No misleading empty state when only archived records remain.
  data = data.filter(item => item.archived_at !== null)
  await page.reload({ waitUntil: 'domcontentloaded' })
  await expect(gallery.locator('article.archived')).toHaveCount(2)
  await expect(page.getByText('Пока нет желаний', { exact: true })).toHaveCount(0)
  await expect(rail).toHaveCount(0)
})

test('certificate shop autofills without blur, hides pricing and supports editing', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const title = `Сертификат ${Date.now()}`
  await page.route('**/api/v1/metadata', route => {
    expect(route.request().postDataJSON()).toEqual({ url: 'https://example.com/gift-card', prefer_logo: true })
    return route.fulfill({ json: { title, image_id: 'auto-shop-photo', price: '25', currency: 'USD', warning: null } })
  })
  await page.route('**/api/v1/media/auto-shop-photo', route => route.fulfill({
    contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="90"><rect width="160" height="90" fill="#b94a28"/></svg>',
  }))
  await page.goto('/me', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: /Войти в локальную/ }).click()
  await page.getByRole('button', { name: 'Добавить магазин', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Ссылка на магазин').fill('https://example.com/gift-card')
  await expect(dialog.getByLabel('Название')).toHaveValue(title)
  await expect(dialog.getByAltText('Фотография подарка')).toBeVisible()
  await expect(dialog.getByRole('spinbutton')).toHaveCount(0)
  await expect(dialog.getByRole('combobox', { name: 'Валюта' })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: 'Цена от указанной суммы' })).toHaveCount(0)
  // Preview uses a fixture image; do not send its synthetic ID to real storage.
  await dialog.getByRole('button', { name: 'Убрать фото' }).click()
  expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
  await dialog.getByRole('button', { name: 'Добавить магазин', exact: true }).click()
  const section = page.getByRole('region', { name: /Сертификаты/ })
  const card = section.locator('article').filter({ hasText: title })
  await expect(card.getByRole('heading', { name: title })).toBeVisible()
  await expect(card.locator('.card-bottom strong')).toHaveCount(0)
  for (const width of [1440, 1280, 768, 390, 360, 320]) {
    await page.setViewportSize({ width, height: 844 })
    await expect(card.locator('.card-open')).toHaveCSS('flex-direction', 'column')
    await expect(card.locator('.certificate-label')).toHaveText('Подарочная карта')
    await expect(card.locator('.card-body')).toHaveCSS('border-top-color', 'rgb(185, 74, 40)')
    await expect(card.locator('.card-body')).toHaveCSS('border-top-width', '3px')
    await expect(section.locator('.certificate-rail')).toHaveCSS('flex-wrap', 'nowrap')
    expect((await card.boundingBox())!.width).toBeLessThanOrEqual(261)
    expect(await card.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await card.getByLabel(`Управление: ${title}`).click()
  await card.getByRole('button', { name: 'Редактировать' }).click()
  await expect(dialog.getByRole('spinbutton')).toHaveCount(0)
  await expect(dialog.getByLabel('Заметка')).toBeVisible()
  await expect(dialog.locator('.upload-area')).toBeVisible()
  await page.screenshot({ path: 'test-results/mobile-certificate-form.png', fullPage: true })
  await dialog.getByRole('button', { name: 'Отмена', exact: true }).click()
  await page.screenshot({ path: 'test-results/mobile-certificates.png', fullPage: true })
  await card.getByLabel(`Управление: ${title}`).click()
  await card.getByRole('button', { name: 'Удалить', exact: true }).click()
  await page.getByRole('button', { name: 'Удалить навсегда' }).click()
  await expect(card).toHaveCount(0)
})
