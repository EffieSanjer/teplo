import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ItemForm from '../../../src/components/ItemForm.vue'
import { api, send } from '../../../src/shared/api'

vi.mock('../../../src/shared/api', async (original) => ({
  ...(await original<typeof import('../../../src/shared/api')>()),
  send: vi.fn(),
  api: vi.fn(async () => []),
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

function sourceUrl(wrapper: ReturnType<typeof form>) {
  return wrapper.get('.source-section input[type="url"]')
}

function titleInput(wrapper: ReturnType<typeof form>) {
  return wrapper.get('.identity-section input')
}

function priceModeButtons(wrapper: ReturnType<typeof form>) {
  return wrapper.get('.price-value').findAll('button')
}

async function paste(wrapper: ReturnType<typeof form>, text: string) {
  await sourceUrl(wrapper).trigger('paste', {
    clipboardData: { getData: () => text },
  })
  await flushPromises()
}

async function pastePhoto(wrapper: ReturnType<typeof form>, text: string) {
  if (wrapper.get('.photo-url-toggle').attributes('aria-expanded') !== 'true') {
    await wrapper.get('.photo-url-toggle').trigger('click')
  }
  await wrapper.get('#photo-url').trigger('paste', {
    clipboardData: { getData: () => text },
  })
  await flushPromises()
}

describe('ItemForm', () => {
  beforeEach(() => {
    vi.mocked(send).mockReset()
    vi.mocked(api).mockReset()
    vi.mocked(api).mockResolvedValue([])
  })

  it('normalizes mobile input without a paste event when WB is blocked', async () => {
    vi.mocked(send).mockRejectedValueOnce(new Error('Сайт не предоставил данные'))
    const wrapper = form()
    await sourceUrl(wrapper).setValue(
      'https://www.wildberries.ru/catalog/1126771984/detail.aspx?targetUrl=SN, Свеча ароматическая Ta&Ko Home за 2\u00a0850\u00a0₽',
    )
    await flushPromises()
    expect((sourceUrl(wrapper).element as HTMLInputElement).value).toBe(
      'https://www.wildberries.ru/catalog/1126771984/detail.aspx?targetUrl=SN',
    )
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
      'Свеча ароматическая Ta&Ko Home',
    )
    expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe('2 850')
    wrapper.unmount()
  })

  it('keeps a bot preview and still requests page metadata', async () => {
    vi.mocked(send).mockResolvedValueOnce({
      title: 'From page',
      price: '99',
      currency: 'USD',
      image_id: 'photo',
      image_is_icon: false,
    })
    const wrapper = mount(ItemForm, {
      props: {
        recipientId: '11111111-1111-4111-8111-111111111111',
        listType: 'wishlist',
        initialType: 'gift',
        seed: {
          url: 'https://example.com/item',
          title: 'Lamp',
          price: '1200',
          currency: 'RUB',
          image_id: 'seed-photo',
        },
      },
      global: { stubs: { Modal: { template: '<div><slot /></div>' } } },
    })
    await flushPromises()
    expect((wrapper.get('.source-section input[type="url"]').element as HTMLInputElement).value).toBe(
      'https://example.com/item',
    )
    expect((wrapper.get('.identity-section input').element as HTMLInputElement).value).toBe('Lamp')
    expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe('1 200')
    // Keep the bot preview photo; metadata must not replace an already filled image.
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/seed-photo')
    expect(send).toHaveBeenCalledWith(
      '/metadata',
      expect.objectContaining({ url: 'https://example.com/item' }),
    )
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
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
      'Product',
    )
  })

  it('clears an imported certificate icon when the shop URL changes', async () => {
    vi.mocked(send).mockResolvedValueOnce({ title: 'Shop', image_id: 'icon', image_is_icon: true })
    const wrapper = form('certificate')
    await paste(wrapper, 'https://example.com/shop')
    expect(wrapper.get('img.site-icon').classes()).toContain('site-icon')
    await sourceUrl(wrapper).setValue('https://example.com/other')
    expect(wrapper.find('img.site-icon').exists()).toBe(false)
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
    expect((sourceUrl(wrapper).element as HTMLInputElement).value).toBe(url)
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('')
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/shared-photo')
    await sourceUrl(wrapper).trigger('blur')
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
    expect(wrapper.find('#item-price').exists()).toBe(false)
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
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
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
    await titleInput(wrapper).setValue('Моя находка')
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
    await titleInput(wrapper).setValue('Подарок с фото')
    await pastePhoto(wrapper, ' https://example.com/photo.jpg ')
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

  it('opens the file picker from photo icons and keeps only one file input', async () => {
    const wrapper = form()
    expect(wrapper.find('.photo-url-toggle').exists()).toBe(true)
    expect(wrapper.find('.photo-url-submit').exists()).toBe(false)
    const file = wrapper.get('input[type="file"]')
    expect(file.attributes('multiple')).toBeUndefined()
    const pick = vi.spyOn(HTMLInputElement.prototype, 'click').mockImplementation(() => {})
    await wrapper.get('.upload-button').trigger('click')
    expect(pick).toHaveBeenCalledTimes(1)
    vi.mocked(api).mockResolvedValueOnce({ id: 'chosen-photo' })
    Object.defineProperty(file.element, 'files', {
      value: [new File(['photo'], 'photo.png', { type: 'image/png' })],
    })
    await file.trigger('change')
    await flushPromises()
    await wrapper.get('.photo-edit').trigger('click')
    expect(pick).toHaveBeenCalledTimes(2)
    expect(wrapper.findAll('input[type="file"]')).toHaveLength(1)
    pick.mockRestore()
  })

  it('loads a manually entered photo URL through Enter without submitting the wish', async () => {
    vi.mocked(send).mockResolvedValueOnce({ id: 'manual-photo' })
    const wrapper = form()
    await wrapper.get('.photo-url-toggle').trigger('click')
    expect(wrapper.get('.photo-url-toggle').attributes('aria-expanded')).toBe('true')
    expect(wrapper.get('#photo-url').attributes('disabled')).toBeUndefined()
    await wrapper.get('#photo-url').setValue('https://example.com/manual.jpg')
    await wrapper.get('#photo-url').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(send).toHaveBeenCalledExactlyOnceWith('/media/from-url', {
      url: 'https://example.com/manual.jpg',
    })
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/manual-photo')
    expect(wrapper.get('.photo-url-toggle').attributes('aria-expanded')).toBe('false')
    expect(wrapper.emitted('saved')).toBeUndefined()
    wrapper.unmount()
  })

  it('rejects unsupported files before upload and keeps the existing photo', async () => {
    const wrapper = form()
    vi.mocked(send).mockResolvedValueOnce({ image_id: 'existing-photo' })
    await paste(wrapper, 'https://example.com/item')
    vi.mocked(api).mockClear()
    const file = wrapper.get('input[type="file"]')
    Object.defineProperty(file.element, 'files', {
      value: [new File(['document'], 'document.pdf', { type: 'application/pdf' })],
    })
    await file.trigger('change')
    await flushPromises()
    expect(api).not.toHaveBeenCalled()
    expect(wrapper.get('.photo-error').text()).toContain('JPEG, PNG или WebP')
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/existing-photo')
    wrapper.unmount()
  })

  it('reveals field clear buttons only after the field loses focus', async () => {
    const wrapper = form()
    const title = titleInput(wrapper)
    const note = wrapper.get('textarea')
    const clearTitle = () => wrapper.find('[aria-label="Очистить название"]')
    const clearNote = () => wrapper.find('[aria-label="Очистить заметку"]')
    await title.setValue('Название')
    await note.setValue('Заметка')
    expect(clearTitle().exists()).toBe(true)
    expect(clearNote().exists()).toBe(true)
    await title.trigger('focus')
    expect(clearTitle().exists()).toBe(false)
    await title.trigger('blur')
    expect(clearTitle().exists()).toBe(true)
    await note.trigger('focus')
    expect(clearNote().exists()).toBe(false)
    await note.trigger('blur')
    expect(clearNote().exists()).toBe(true)
    await clearTitle().trigger('click')
    expect((title.element as HTMLInputElement).value).toBe('')
    await clearNote().trigger('click')
    expect((note.element as HTMLTextAreaElement).value).toBe('')
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
    await pastePhoto(wrapper, 'https://example.com/photo.jpg')
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
    await sourceUrl(wrapper).setValue('https://example.com/product')
    await pastePhoto(wrapper, 'https://example.com/photo.jpg')
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
    await titleInput(wrapper).setValue('Бесплатная радость')
    await wrapper.get('#item-price').setValue('0')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ price: '0', currency: 'RUB' }),
    )
  })

  it('keeps fields when switching item types', async () => {
    const wrapper = form()
    await titleInput(wrapper).setValue('Ручное название')
    await wrapper.get('textarea').setValue('Ручное описание')
    await sourceUrl(wrapper).setValue('https://example.com')
    await wrapper.findAll('.type-switch button')[1].trigger('click')
    await wrapper.findAll('.type-switch button')[0].trigger('click')
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
      'Ручное название',
    )
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Ручное описание')
    expect((sourceUrl(wrapper).element as HTMLInputElement).value).toBe(
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
    await sourceUrl(wrapper).setValue('https://example.com')
    await titleInput(wrapper).setValue('Моё название')
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
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
      'Моё название',
    )
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(
      'Написано во время запроса',
    )
    expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe('12,50')
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
      await sourceUrl(wrapper).setValue('https://example.com')
      await wrapper.get('textarea').setValue(description)
      expect(wrapper.get('.personal-description label').text()).toContain('Заметка')
      expect(wrapper.get('textarea').attributes('aria-describedby')).toBe(
        'personal-description-hint',
      )
      expect(wrapper.get('#personal-description-hint').text()).toBe(
        `Ваши слова · ${[...description].length} / 500`,
      )
      await wrapper.get('.metadata-button').trigger('click')
      await flushPromises()
      expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(description)
      expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
        'Название магазина',
      )
      expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe(
        '1 200,00',
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
    await sourceUrl(wrapper).setValue('https://example.com')
    await wrapper.get('.metadata-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.source-section [role="alert"]').text()).toContain('Сайт недоступен')
    expect(wrapper.get('#source-link-hint').attributes('role')).toBe('alert')
    expect(wrapper.get('#source-link-hint').text()).not.toContain('Вставьте из')
    expect(sourceUrl(wrapper).attributes('aria-invalid')).toBe('true')
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
    await pastePhoto(wrapper, 'https://example.com/photo.jpg')
    await sourceUrl(wrapper).setValue('https://example.com/product')
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
    expect(wrapper.find('.photo-section [role="status"]').exists()).toBe(false)
    expect(wrapper.find('.source-section [role="status"]').exists()).toBe(false)
  })

  it('shows the file error on the upload area', async () => {
    const wrapper = form()
    const file = wrapper.get('input[type="file"]')
    Object.defineProperty(file.element, 'files', {
      value: [new File([new Uint8Array(5242881)], 'large.png', { type: 'image/png' })],
    })
    await file.trigger('change')
    expect(wrapper.get('.photo-error').attributes('role')).toBe('alert')
    expect(wrapper.get('.photo-error').text()).toBe('Фото должно быть не больше 5 МБ')
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
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
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
    await sourceUrl(wrapper).setValue('https://example.com/shop')
    await sourceUrl(wrapper).trigger('blur')
    await flushPromises()
    expect(send).toHaveBeenCalledWith('/metadata', {
      url: 'https://example.com/shop',
      prefer_logo: true,
    })
    expect(wrapper.find('#item-price').exists()).toBe(false)
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
  it('keeps the mode select inside one full-width price field', async () => {
    vi.mocked(send).mockResolvedValue({})
    const wrapper = form()
    await wrapper.get('#item-price').setValue('1500')
    await flushPromises()
    const field = wrapper.get('.price-value')
    const buttons = priceModeButtons(wrapper)
    expect(buttons.map((button) => button.text())).toEqual(['Примерно', 'От'])
    expect(buttons.every((button) => button.attributes('aria-pressed') === 'false')).toBe(true)
    expect(field.element.contains(wrapper.get('#item-price').element)).toBe(true)
    expect(wrapper.find('.price-clear').exists()).toBe(false)
    expect(wrapper.get('.price-currency').text()).toBe('₽')
    expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe('1 500')
    await buttons[1]!.trigger('click')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ price: '1500', price_mode: 'from' }),
    )
    await buttons[0]!.trigger('click')
    expect(buttons[0]!.attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('.price-currency').text()).toBe('₽')
  })
  it('automatically loads a certificate shop photo after typing without blur', async () => {
    vi.useFakeTimers()
    const wrapper = form('certificate')
    try {
      vi.mocked(send).mockResolvedValue({ title: 'Магазин', image_id: 'auto-shop' })
      await sourceUrl(wrapper).setValue('https://example.com/shop')
      await vi.advanceTimersByTimeAsync(700)
      await flushPromises()
      expect(send).toHaveBeenCalledWith('/metadata', {
        url: 'https://example.com/shop',
        prefer_logo: true,
      })
      expect(wrapper.get('img.site-icon').attributes('src')).toBe('/api/v1/media/auto-shop')
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
      expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
        'Керамическая чашка',
      )
      expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe(
        '1 290,50',
      )
      expect(priceModeButtons(wrapper)[1]!.attributes('aria-pressed')).toBe('true')
      expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('')
    },
  )
  it('prefers website metadata and never overwrites manual fields with the share caption', async () => {
    vi.mocked(send).mockResolvedValueOnce({ title: 'С сайта', price: '500', currency: 'EUR' })
    const wrapper = form()
    await paste(wrapper, 'Из подписи от 1200 ₽ https://example.com/item')
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
      'С сайта',
    )
    expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe('500')
    expect(priceModeButtons(wrapper).every((button) => button.attributes('aria-pressed') === 'false')).toBe(
      true,
    )
    vi.mocked(send).mockResolvedValueOnce({})
    await paste(wrapper, 'Другая подпись 2400 ₽ https://example.com/second')
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
      'С сайта',
    )
    expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe('500')
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
    await titleInput(wrapper).setValue('Моя находка')
    await wrapper.get('#item-price').setValue('2500')
    await wrapper.get('textarea').setValue('Моя заметка')
    resolve({})
    await flushPromises()
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
      'Моя находка',
    )
    expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe('2 500')
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
    await sourceUrl(wrapper).setValue(url)
    await sourceUrl(wrapper).trigger('blur')
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
      await sourceUrl(wrapper).setValue(url)
      await sourceUrl(wrapper).trigger('blur')
      await flushPromises()
      await sourceUrl(wrapper).trigger('blur')
      expect(send).toHaveBeenCalledTimes(1)
      expect(send).toHaveBeenCalledWith('/metadata', { url })
      expect((titleInput(wrapper).element as HTMLInputElement).value).toBe(
        'Чашка',
      )
      expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe('1 500')
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
      await sourceUrl(wrapper).setValue(url)
      await sourceUrl(wrapper).trigger('blur')
      expect(send).not.toHaveBeenCalled()
      wrapper.unmount()
    },
  )
  it.each(['www.wildberries.ru', 'wb.ru'])(
    'autofills a Wildberries listing on blur from %s',
    async (host) => {
      const url = `https://${host}/catalog/1126771984/detail.aspx`
      vi.mocked(send).mockResolvedValueOnce({
        title: 'Кардиган',
        price: '2500',
        currency: 'RUB',
        image_id: 'wb-photo',
      })
      const wrapper = form()
      await wrapper.findAll('.type-switch button')[1].trigger('click')
      const source = wrapper.get('.source-section input[type="url"]')
      await source.setValue(url)
      await source.trigger('blur')
      await flushPromises()
      expect(send).toHaveBeenCalledWith('/metadata', { url })
      expect((wrapper.get('.identity-section input').element as HTMLInputElement).value).toBe(
        'Кардиган',
      )
      expect((wrapper.get('#item-price').element as HTMLInputElement).value).toBe('2 500')
      expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/wb-photo')
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
    await sourceUrl(wrapper).setValue('https://example.com/first')
    await wrapper.get('.metadata-button').trigger('click')
    await sourceUrl(wrapper).setValue('https://example.com/second')
    resolve({ title: 'Старое', image_id: 'old-photo' })
    await flushPromises()
    expect((titleInput(wrapper).element as HTMLInputElement).value).toBe('')
    expect(wrapper.find('.upload-area img').exists()).toBe(false)
  })
})
