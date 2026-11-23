import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ItemForm from '../../../src/components/ItemForm.vue'
import { api, send } from '../../../src/shared/api'

vi.mock('../../../src/shared/api', async (original) => ({
  ...(await original<typeof import('../../../src/shared/api')>()),
  send: vi.fn(),
  api: vi.fn(),
  imageUrl: (id: string) => `/api/v1/media/${id}`,
}))

function form(initialType?: 'certificate') {
  return mount(ItemForm, {
    props: {
      recipientId: '11111111-1111-4111-8111-111111111111',
      listType: 'wishlist',
      ...(initialType ? { initialType } : {}),
    },
    global: { stubs: { Modal: { template: '<div><slot /></div>' } } },
  })
}

async function paste(wrapper: ReturnType<typeof form>, text: string) {
  await wrapper.get('input[type="url"]').trigger('paste', {
    clipboardData: { getData: () => text },
  })
  await flushPromises()
}

describe('ItemForm', () => {
  beforeEach(() => {
    vi.mocked(send).mockReset()
  })

  it('normalizes mobile input without a paste event when WB is blocked', async () => {
    vi.mocked(send).mockRejectedValueOnce(new Error('Сайт не предоставил данные'))
    const wrapper = form()
    await wrapper
      .get('input[type="url"]')
      .setValue(
        'https://www.wildberries.ru/catalog/1126771984/detail.aspx?targetUrl=SN, Свеча ароматическая Ta&Ko Home за 2\u00a0850\u00a0₽',
      )
    await flushPromises()
    expect((wrapper.get('input[type="url"]').element as HTMLInputElement).value).toBe(
      'https://www.wildberries.ru/catalog/1126771984/detail.aspx?targetUrl=SN',
    )
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
      'Свеча ароматическая Ta&Ko Home',
    )
    expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe('2850')
    wrapper.unmount()
  })

  it('does not insert an icon response into an ordinary item', async () => {
    vi.mocked(send).mockResolvedValueOnce({
      title: 'Product',
      image_id: 'icon',
      image_is_icon: true,
    })
    const wrapper = form()
    await paste(wrapper, 'https://example.com/item')
    expect(wrapper.find('.upload-area img').exists()).toBe(false)
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
      'Product',
    )
  })

  it('clears an imported certificate icon when the shop URL changes', async () => {
    vi.mocked(send).mockResolvedValueOnce({ title: 'Shop', image_id: 'icon', image_is_icon: true })
    const wrapper = form('certificate')
    await paste(wrapper, 'https://example.com/shop')
    expect(wrapper.get('img').classes()).toContain('site-icon')
    await wrapper.get('input[type="url"]').setValue('https://example.com/other')
    expect(wrapper.find('img').exists()).toBe(false)
    wrapper.unmount()
  })

  it.each([
    'https://example.com/product?ref=share',
    'https://www.instagram.com/reel/abc/?igsh=123',
    'https://pin.it/abc',
    'https://t.me/finds/123',
    'https://www.avito.ru/moskva/posuda/chashka_123456789?utm_source=soc_sharing',
  ])('extracts pasted share text and fetches %s without blur', async (url) => {
    vi.mocked(send)
      .mockResolvedValueOnce({
        title: 'Находка',
        image_id: 'shared-photo',
        price: '1200',
        currency: 'RUB',
      })
      .mockResolvedValueOnce({})
    const wrapper = form()
    await paste(wrapper, `Посмотри, что нашёл!\n${url}\nПоделиться с друзьями`)
    expect(send).toHaveBeenCalledWith('/metadata', { url })
    expect((wrapper.get('input[type="url"]').element as HTMLInputElement).value).toBe(url)
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('')
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/shared-photo')
    await wrapper.get('input[type="url"]').trigger('blur')
    expect(send).toHaveBeenCalledTimes(1)
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ url, title: 'Находка', description: null }),
    )
  })

  it('keeps the manual note and certificate nominal when pasting a shop share', async () => {
    vi.mocked(send)
      .mockResolvedValueOnce({ title: 'Из магазина', price: '25', currency: 'USD' })
      .mockResolvedValueOnce({})
    const wrapper = form('certificate')
    await wrapper.get('textarea').setValue('Мне нравится посуда')
    await paste(wrapper, 'Магазин: https://example.com/shop')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(
      'Мне нравится посуда',
    )
    expect(wrapper.find('input[type="number"]').exists()).toBe(false)
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({
        item_type: 'certificate',
        price: null,
        currency: null,
        description: 'Мне нравится посуда',
      }),
    )
  })

  it('fetches the latest pasted URL after a previous request finishes, ignoring its result', async () => {
    let resolve!: (value: unknown) => void
    vi.mocked(send)
      .mockImplementationOnce(
        () =>
          new Promise((r) => {
            resolve = r
          }),
      )
      .mockResolvedValueOnce({ title: 'Новая находка', image_id: 'new-photo' })
    const wrapper = form()
    await paste(wrapper, 'Первое https://example.com/first')
    await paste(wrapper, 'Второе https://example.com/second')
    expect(send).toHaveBeenCalledTimes(1)
    resolve({ title: 'Устаревшее', image_id: 'old-photo' })
    await flushPromises()
    expect(send).toHaveBeenNthCalledWith(2, '/metadata', { url: 'https://example.com/second' })
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
      'Новая находка',
    )
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/new-photo')
  })

  it('does not fetch unsupported pasted text and preserves save after preview failure', async () => {
    const wrapper = form()
    await paste(wrapper, 'Без ссылки javascript:alert(1)')
    expect(send).not.toHaveBeenCalled()
    vi.mocked(send).mockRejectedValueOnce(new Error('Сайт недоступен')).mockResolvedValueOnce({})
    await paste(wrapper, 'Пост https://www.instagram.com/p/abc/')
    await wrapper.get('input[maxlength="200"]').setValue('Моя находка')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ url: 'https://www.instagram.com/p/abc/', title: 'Моя находка' }),
    )
    expect(wrapper.emitted('saved')).toHaveLength(1)
  })

  it('loads an image URL and saves only its local media ID', async () => {
    vi.mocked(send).mockResolvedValueOnce({ id: 'imported-photo' }).mockResolvedValueOnce({})
    const wrapper = form()
    await wrapper.get('input[maxlength="200"]').setValue('Подарок с фото')
    await wrapper.get('#photo-url').setValue(' https://example.com/photo.jpg ')
    await wrapper.get('.photo-url-row button').trigger('click')
    await flushPromises()
    expect(send).toHaveBeenNthCalledWith(1, '/media/from-url', {
      url: 'https://example.com/photo.jpg',
    })
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/imported-photo')
    expect((wrapper.get('#photo-url').element as HTMLInputElement).value).toBe('')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ image_id: 'imported-photo', url: null }),
    )
  })

  it('keeps the current photo after a failed URL load', async () => {
    vi.mocked(api).mockResolvedValueOnce({ id: 'original-photo' })
    vi.mocked(send).mockRejectedValueOnce(new Error('Сайт недоступен'))
    const wrapper = form()
    const file = wrapper.get('input[type="file"]')
    Object.defineProperty(file.element, 'files', {
      value: [new File(['photo'], 'photo.png', { type: 'image/png' })],
    })
    await file.trigger('change')
    await flushPromises()
    await wrapper.get('#photo-url').setValue('https://example.com/photo.jpg')
    await wrapper.get('.photo-url-row button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/original-photo')
    expect(wrapper.get('[role="alert"]').text()).toContain('Сайт недоступен')
    expect(wrapper.get('#photo-url-hint').attributes('role')).toBe('alert')
    expect(wrapper.get('#photo-url').attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('#photo-url-hint').text()).not.toContain('JPEG')
    expect((wrapper.get('#photo-url').element as HTMLInputElement).value).toBe(
      'https://example.com/photo.jpg',
    )
  })

  it('prevents concurrent image changes and saving while a URL is loading', async () => {
    let resolve!: (value: unknown) => void
    vi.mocked(send).mockImplementationOnce(
      () =>
        new Promise((r) => {
          resolve = r
        }),
    )
    const wrapper = form()
    await wrapper.get('input[type="url"]').setValue('https://example.com/product')
    await wrapper.get('#photo-url').setValue('https://example.com/photo.jpg')
    await wrapper.get('.photo-url-row button').trigger('click')
    expect(wrapper.get('.upload-button').attributes('disabled')).toBeDefined()
    expect(wrapper.get('.metadata-button').attributes('disabled')).toBeDefined()
    expect(wrapper.get('.form-actions .primary').attributes('disabled')).toBeDefined()
    await wrapper.get('form').trigger('submit')
    expect(send).toHaveBeenCalledTimes(1)
    resolve({ id: 'photo' })
    await flushPromises()
    expect(wrapper.get('.form-actions .primary').attributes('disabled')).toBeUndefined()
  })

  it('preserves zero as a decimal string instead of null', async () => {
    vi.mocked(send).mockResolvedValue({})
    const wrapper = form()
    await wrapper.get('input[maxlength="200"]').setValue('Бесплатная радость')
    await wrapper.get('input[type="number"]').setValue('0')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ price: '0', currency: 'RUB' }),
    )
  })

  it('keeps fields when switching item types', async () => {
    const wrapper = form()
    await wrapper.get('input[maxlength="200"]').setValue('Ручное название')
    await wrapper.get('textarea').setValue('Ручное описание')
    await wrapper.get('input[type="url"]').setValue('https://example.com')
    await wrapper.findAll('.type-switch button')[1].trigger('click')
    await wrapper.findAll('.type-switch button')[0].trigger('click')
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
      'Ручное название',
    )
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Ручное описание')
    expect((wrapper.get('input[type="url"]').element as HTMLInputElement).value).toBe(
      'https://example.com',
    )
  })

  it('does not overwrite manual edits made before or during autofill', async () => {
    let resolve!: (draft: unknown) => void
    vi.mocked(send)
      .mockImplementationOnce(
        () =>
          new Promise((r) => {
            resolve = r
          }),
      )
      .mockResolvedValueOnce({})
    const wrapper = form()
    await wrapper.get('input[type="url"]').setValue('https://example.com')
    await wrapper.get('input[maxlength="200"]').setValue('Моё название')
    await wrapper.get('.metadata-button').trigger('click')
    await wrapper.get('textarea').setValue('Написано во время запроса')
    resolve({
      title: 'Название магазина',
      description: 'Описание магазина',
      price: '12.50',
      currency: 'USD',
      image_id: null,
    })
    await flushPromises()
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
      'Моё название',
    )
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(
      'Написано во время запроса',
    )
    expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe('12.50')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ price: '12.50', currency: 'USD' }),
    )
  })

  it.each(['', 'Хочу синий, размер M'])(
    'keeps personal description %j instead of importing store text',
    async (description) => {
      vi.mocked(send)
        .mockResolvedValueOnce({
          title: 'Название магазина',
          description: 'Рекламное описание товара',
          price: '1200.00',
          currency: 'RUB',
          image_id: 'product-photo',
        })
        .mockResolvedValueOnce({})
      const wrapper = form()
      await wrapper.get('input[type="url"]').setValue('https://example.com')
      await wrapper.get('textarea').setValue(description)
      expect(wrapper.get('.personal-description label').text()).toContain('Заметка')
      expect(wrapper.get('textarea').attributes('aria-describedby')).toBe(
        'personal-description-hint',
      )
      expect(wrapper.get('#personal-description-hint').text()).toBe(
        `${[...description].length} / 500 · Только ваши слова`,
      )
      await wrapper.get('.metadata-button').trigger('click')
      await flushPromises()
      expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(description)
      expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
        'Название магазина',
      )
      expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe(
        '1200.00',
      )
      expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/product-photo')
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(send).toHaveBeenLastCalledWith(
        '/items',
        expect.objectContaining({ description: description || null }),
      )
    },
  )

  it('allows saving a URL after optional metadata fails', async () => {
    vi.mocked(send).mockRejectedValueOnce(new Error('Сайт недоступен')).mockResolvedValueOnce({})
    const wrapper = form()
    await wrapper.findAll('.type-switch button')[1].trigger('click')
    await wrapper.get('input[type="url"]').setValue('https://example.com')
    await wrapper.get('.metadata-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.source-section [role="alert"]').text()).toContain('Сайт недоступен')
    expect(wrapper.get('#source-link-hint').attributes('role')).toBe('alert')
    expect(wrapper.get('#source-link-hint').text()).not.toContain('Вставьте из')
    expect(wrapper.get('input[type="url"]').attributes('aria-invalid')).toBe('true')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.emitted('saved')).toHaveLength(1)
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ item_type: 'gift', url: 'https://example.com', price: null }),
    )
  })

  it('keeps photo and source feedback next to their own actions', async () => {
    vi.mocked(send)
      .mockRejectedValueOnce(new Error('Ошибка загрузки фото'))
      .mockRejectedValueOnce(new Error('Ошибка автозаполнения'))
    const wrapper = form()
    await wrapper.get('#photo-url').setValue('https://example.com/photo.jpg')
    await wrapper.get('.photo-url-row button').trigger('click')
    await flushPromises()
    await wrapper.get('input[type="url"]').setValue('https://example.com/product')
    await wrapper.get('.metadata-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.photo-section [role="alert"]').text()).toContain('Ошибка загрузки фото')
    expect(wrapper.get('.source-section [role="alert"]').text()).toContain('Ошибка автозаполнения')
  })

  it('places save failures immediately before the form actions', async () => {
    vi.mocked(send).mockRejectedValueOnce(new Error('Не удалось сохранить'))
    const wrapper = form()
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('.form-actions').element.previousElementSibling?.textContent).toBe(
      'Не удалось сохранить',
    )
  })

  it.each([
    'Загружено первое фото публикации и имя автора.',
    'Вместо фото использован логотип или значок сайта.',
  ])('does not announce imported photo provenance: %s', async (warning) => {
    vi.mocked(send).mockResolvedValueOnce({ title: 'Находка', image_id: 'photo', warning })
    const wrapper = form()
    await paste(wrapper, 'https://example.com/item')
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/photo')
    expect(wrapper.text()).not.toContain(warning)
    expect(wrapper.find('[role="status"]').exists()).toBe(false)
  })

  it('replaces the upload hint with the file error', async () => {
    const wrapper = form()
    const file = wrapper.get('input[type="file"]')
    Object.defineProperty(file.element, 'files', {
      value: [new File([new Uint8Array(5242881)], 'large.png', { type: 'image/png' })],
    })
    await file.trigger('change')
    expect(wrapper.get('.upload-button small').attributes('role')).toBe('alert')
    expect(wrapper.get('.upload-button small').text()).toBe('Фото должно быть не больше 5 МБ')
    expect(wrapper.find('.photo-section .inline-error').exists()).toBe(false)
  })

  it('ignores stale metadata errors when a new URL is pasted', async () => {
    let reject!: (reason: Error) => void
    vi.mocked(send)
      .mockImplementationOnce(
        () =>
          new Promise((_, fail) => {
            reject = fail
          }),
      )
      .mockResolvedValueOnce({ title: 'Новая находка' })
    const wrapper = form()
    await paste(wrapper, 'https://example.com/first')
    await paste(wrapper, 'https://example.com/second')
    reject(new Error('Ошибка старой ссылки'))
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
      'Новая находка',
    )
  })
  it('autofills a certificate shop on leaving its URL without importing product price', async () => {
    vi.mocked(send)
      .mockResolvedValueOnce({
        title: 'Магазин книг',
        image_id: 'shop-photo',
        price: '25',
        currency: 'USD',
      })
      .mockResolvedValueOnce({})
    const wrapper = form('certificate')
    await wrapper.get('input[type="url"]').setValue('https://example.com/shop')
    await wrapper.get('input[type="url"]').trigger('blur')
    await flushPromises()
    expect(send).toHaveBeenCalledWith('/metadata', {
      url: 'https://example.com/shop',
      prefer_logo: true,
    })
    expect(wrapper.find('input[type="number"]').exists()).toBe(false)
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({
        item_type: 'certificate',
        price: null,
        currency: null,
        image_id: 'shop-photo',
      }),
    )
  })
  it('toggles the inline minimum price button and keeps its amount', async () => {
    vi.mocked(send).mockResolvedValue({})
    const wrapper = form()
    await wrapper.get('input[type="number"]').setValue('1500')
    await wrapper.get('.price-from').trigger('click')
    expect(wrapper.get('.price-from').attributes('aria-pressed')).toBe('true')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ price: '1500', price_mode: 'from' }),
    )
    await wrapper.get('.price-from').trigger('click')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ price: '1500', price_mode: 'approximate' }),
    )
    expect(wrapper.text()).not.toMatch(/Примерно|Примерная|Личное описание/)
  })
  it('automatically loads a certificate shop photo after typing without blur', async () => {
    vi.useFakeTimers()
    const wrapper = form('certificate')
    try {
      vi.mocked(send).mockResolvedValue({ title: 'Магазин', image_id: 'auto-shop' })
      await wrapper.get('input[type="url"]').setValue('https://example.com/shop')
      await vi.advanceTimersByTimeAsync(700)
      await flushPromises()
      expect(send).toHaveBeenCalledWith('/metadata', {
        url: 'https://example.com/shop',
        prefer_logo: true,
      })
      expect(wrapper.get('img').attributes('src')).toBe('/api/v1/media/auto-shop')
      expect(wrapper.find('.price-field').exists()).toBe(false)
    } finally {
      wrapper.unmount()
      vi.useRealTimers()
    }
  })
  it.each([false, true])(
    'uses share caption title and price when website metadata is missing (failure=%s)',
    async (failure) => {
      if (failure) vi.mocked(send).mockRejectedValueOnce(new Error('Сайт недоступен'))
      else vi.mocked(send).mockResolvedValueOnce({ warning: 'Нет данных' })
      const wrapper = form()
      await paste(wrapper, 'Керамическая чашка\nот 1 290,50 ₽\nhttps://example.com/item')
      expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
        'Керамическая чашка',
      )
      expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe(
        '1290.50',
      )
      expect(wrapper.get('.price-from').attributes('aria-pressed')).toBe('true')
      expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('')
    },
  )
  it('prefers website metadata and never overwrites manual fields with the share caption', async () => {
    vi.mocked(send).mockResolvedValueOnce({ title: 'С сайта', price: '500', currency: 'EUR' })
    const wrapper = form()
    await paste(wrapper, 'Из подписи от 1200 ₽ https://example.com/item')
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
      'С сайта',
    )
    expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe('500')
    expect(wrapper.get('.price-from').attributes('aria-pressed')).toBe('false')
    vi.mocked(send).mockResolvedValueOnce({})
    await paste(wrapper, 'Другая подпись 2400 ₽ https://example.com/second')
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
      'С сайта',
    )
    expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe('500')
  })
  it('does not import share prices into certificates', async () => {
    vi.mocked(send).mockResolvedValueOnce({})
    const wrapper = form('certificate')
    await paste(wrapper, 'Магазин\n1500 ₽\nhttps://example.com/shop')
    vi.mocked(send).mockResolvedValueOnce({})
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ title: 'Магазин', price: null, currency: null }),
    )
    wrapper.unmount()
  })
  it('preserves edits made while a share preview is loading', async () => {
    let resolve!: (value: unknown) => void
    vi.mocked(send).mockImplementationOnce(
      () =>
        new Promise((done) => {
          resolve = done
        }),
    )
    const wrapper = form()
    await paste(wrapper, 'Название из подписи\n1000 ₽\nhttps://example.com/item')
    await wrapper.get('input[maxlength="200"]').setValue('Моя находка')
    await wrapper.get('input[type="number"]').setValue('2500')
    await wrapper.get('textarea').setValue('Моя заметка')
    resolve({})
    await flushPromises()
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
      'Моя находка',
    )
    expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe('2500')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Моя заметка')
  })
  it.each([
    'https://t.me/finds/123',
    'https://www.instagram.com/p/abc/',
    'https://pin.it/abc',
    'https://www.pinterest.com/pin/123/',
  ])('autofills public social link %s and preserves it', async (url) => {
    vi.mocked(send)
      .mockResolvedValueOnce({ title: 'Находка', image_id: 'social-photo' })
      .mockResolvedValueOnce({})
    const wrapper = form()
    await wrapper.findAll('.type-switch button')[1].trigger('click')
    await wrapper.get('input[type="url"]').setValue(url)
    await wrapper.get('input[type="url"]').trigger('blur')
    await flushPromises()
    expect(send).toHaveBeenCalledWith('/metadata', { url })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ url, image_id: 'social-photo', description: null }),
    )
  })
  it.each(['avito.ru', 'www.avito.ru', 'm.avito.ru'])(
    'autofills an Avito listing on blur from %s only once',
    async (host) => {
      const url = `https://${host}/moskva/posuda/chashka_123456789?utm_source=soc_sharing`
      vi.mocked(send)
        .mockResolvedValueOnce({
          title: 'Чашка',
          price: '1500',
          currency: 'RUB',
          image_id: 'avito-photo',
        })
        .mockResolvedValueOnce({})
      const wrapper = form()
      await wrapper.findAll('.type-switch button')[1].trigger('click')
      await wrapper.get('input[type="url"]').setValue(url)
      await wrapper.get('input[type="url"]').trigger('blur')
      await flushPromises()
      await wrapper.get('input[type="url"]').trigger('blur')
      expect(send).toHaveBeenCalledTimes(1)
      expect(send).toHaveBeenCalledWith('/metadata', { url })
      expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe(
        'Чашка',
      )
      expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe('1500')
      expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/avito-photo')
      await wrapper.get('form').trigger('submit')
      await flushPromises()
      expect(send).toHaveBeenLastCalledWith(
        '/items',
        expect.objectContaining({ url, title: 'Чашка', price: '1500', image_id: 'avito-photo' }),
      )
      wrapper.unmount()
    },
  )
  it.each(['https://avito.ru.evil.test/item_123', 'https://user:pass@www.avito.ru/item_123'])(
    'does not autofill an untrusted Avito-like URL %s on blur',
    async (url) => {
      const wrapper = form()
      await wrapper.get('input[type="url"]').setValue(url)
      await wrapper.get('input[type="url"]').trigger('blur')
      expect(send).not.toHaveBeenCalled()
      wrapper.unmount()
    },
  )
  it('ignores metadata when the source URL changes during the request', async () => {
    let resolve!: (value: unknown) => void
    vi.mocked(send).mockImplementationOnce(
      () =>
        new Promise((r) => {
          resolve = r
        }),
    )
    const wrapper = form()
    await wrapper.get('input[type="url"]').setValue('https://example.com/first')
    await wrapper.get('.metadata-button').trigger('click')
    await wrapper.get('input[type="url"]').setValue('https://example.com/second')
    resolve({ title: 'Старое', image_id: 'old-photo' })
    await flushPromises()
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe('')
    expect(wrapper.find('.upload-area img').exists()).toBe(false)
  })
})
