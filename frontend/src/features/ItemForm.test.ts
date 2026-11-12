import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ItemForm from './ItemForm.vue'
import { api, send } from '../shared/api'

vi.mock('../shared/api', () => ({
  send: vi.fn(), api: vi.fn(), imageUrl: (id: string) => `/api/v1/media/${id}`,
}))

function form() {
  return mount(ItemForm, {
    props: { recipientId: '11111111-1111-4111-8111-111111111111', listType: 'wishlist' },
    global: { stubs: { Modal: { template: '<div><slot /></div>' } } },
  })
}

describe('ItemForm', () => {
  beforeEach(() => { vi.mocked(send).mockReset() })

  it('loads an image URL and saves only its local media ID', async () => {
    vi.mocked(send).mockResolvedValueOnce({ id: 'imported-photo' }).mockResolvedValueOnce({})
    const wrapper = form()
    await wrapper.get('input[maxlength="200"]').setValue('Подарок с фото')
    await wrapper.get('#photo-url').setValue(' https://example.com/photo.jpg ')
    await wrapper.get('.photo-url-row button').trigger('click')
    await flushPromises()
    expect(send).toHaveBeenNthCalledWith(1, '/media/from-url', { url: 'https://example.com/photo.jpg' })
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/imported-photo')
    expect((wrapper.get('#photo-url').element as HTMLInputElement).value).toBe('')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith('/items', expect.objectContaining({ image_id: 'imported-photo', url: null }))
  })

  it('keeps the current photo after a failed URL load', async () => {
    vi.mocked(api).mockResolvedValueOnce({ id: 'original-photo' })
    vi.mocked(send).mockRejectedValueOnce(new Error('Сайт недоступен'))
    const wrapper = form()
    const file = wrapper.get('input[type="file"]')
    Object.defineProperty(file.element, 'files', { value: [new File(['photo'], 'photo.png', { type: 'image/png' })] })
    await file.trigger('change')
    await flushPromises()
    await wrapper.get('#photo-url').setValue('https://example.com/photo.jpg')
    await wrapper.get('.photo-url-row button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/original-photo')
    expect(wrapper.get('[role="alert"]').text()).toContain('Сайт недоступен')
    expect((wrapper.get('#photo-url').element as HTMLInputElement).value).toBe('https://example.com/photo.jpg')
  })

  it('prevents concurrent image changes and saving while a URL is loading', async () => {
    let resolve!: (value: unknown) => void
    vi.mocked(send).mockImplementationOnce(() => new Promise(r => { resolve = r }))
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
    expect(send).toHaveBeenLastCalledWith('/items', expect.objectContaining({ price: '0', currency: 'RUB' }))
  })

  it('keeps fields when switching item types', async () => {
    const wrapper = form()
    await wrapper.get('input[maxlength="200"]').setValue('Ручное название')
    await wrapper.get('textarea').setValue('Ручное описание')
    await wrapper.get('input[type="url"]').setValue('https://example.com')
    await wrapper.findAll('.type-switch button')[1].trigger('click')
    await wrapper.findAll('.type-switch button')[0].trigger('click')
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe('Ручное название')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Ручное описание')
    expect((wrapper.get('input[type="url"]').element as HTMLInputElement).value).toBe('https://example.com')
  })

  it('does not overwrite manual edits made before or during autofill', async () => {
    let resolve!: (draft: unknown) => void
    vi.mocked(send).mockImplementation(() => new Promise(r => { resolve = r }))
    const wrapper = form()
    await wrapper.get('input[type="url"]').setValue('https://example.com')
    await wrapper.get('input[maxlength="200"]').setValue('Моё название')
    await wrapper.get('.metadata-button').trigger('click')
    await wrapper.get('textarea').setValue('Написано во время запроса')
    resolve({ title: 'Название магазина', description: 'Описание магазина', price: '12.50', currency: 'USD', image_id: null })
    await flushPromises()
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe('Моё название')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('Написано во время запроса')
    expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe('12.50')
    expect((wrapper.get('select').element as HTMLSelectElement).value).toBe('USD')
  })

  it.each(['', 'Хочу синий, размер M'])('keeps personal description %j instead of importing store text', async (description) => {
    vi.mocked(send).mockResolvedValueOnce({
      title: 'Название магазина', description: 'Рекламное описание товара',
      price: '1200.00', currency: 'RUB', image_id: 'product-photo',
    }).mockResolvedValueOnce({})
    const wrapper = form()
    await wrapper.get('input[type="url"]').setValue('https://example.com')
    await wrapper.get('textarea').setValue(description)
    expect(wrapper.get('.personal-description label').text()).toContain('Личное описание')
    expect(wrapper.get('textarea').attributes('aria-describedby')).toBe('personal-description-hint')
    expect(wrapper.get('#personal-description-hint').text()).toContain('По ссылке это поле не заполняется')
    await wrapper.get('.metadata-button').trigger('click')
    await flushPromises()
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(description)
    expect((wrapper.get('input[maxlength="200"]').element as HTMLInputElement).value).toBe('Название магазина')
    expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe('1200.00')
    expect(wrapper.get('.upload-area img').attributes('src')).toBe('/api/v1/media/product-photo')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith('/items', expect.objectContaining({ description: description || null }))
  })

  it('allows saving a URL after optional metadata fails', async () => {
    vi.mocked(send).mockRejectedValueOnce(new Error('Сайт недоступен')).mockResolvedValueOnce({})
    const wrapper = form()
    await wrapper.findAll('.type-switch button')[1].trigger('click')
    await wrapper.get('input[type="url"]').setValue('https://example.com')
    await wrapper.get('.metadata-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Сайт недоступен')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.emitted('saved')).toHaveLength(1)
    expect(send).toHaveBeenLastCalledWith('/items', expect.objectContaining({ item_type: 'gift', url: 'https://example.com', price: null }))
  })
  it('autofills a certificate shop on leaving its URL without importing product price', async () => {
    vi.mocked(send).mockResolvedValueOnce({ title: 'Магазин книг', image_id: 'shop-photo', price: '25', currency: 'USD' }).mockResolvedValueOnce({})
    const wrapper = form()
    await wrapper.findAll('.type-switch button')[2].trigger('click')
    await wrapper.get('input[type="url"]').setValue('https://example.com/shop')
    await wrapper.get('input[type="url"]').trigger('blur')
    await flushPromises()
    expect(send).toHaveBeenCalledWith('/metadata', { url: 'https://example.com/shop' })
    expect((wrapper.get('input[type="number"]').element as HTMLInputElement).value).toBe('')
    await wrapper.get('input[type="number"]').setValue('1000')
    await wrapper.get('input[value="from"]').setValue()
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith('/items', expect.objectContaining({ item_type: 'certificate', price_mode: 'from', price: '1000', image_id: 'shop-photo' }))
  })
  it.each(['https://t.me/finds/123', 'https://www.instagram.com/p/abc/', 'https://pin.it/abc', 'https://www.pinterest.com/pin/123/'])('autofills public social link %s and preserves it', async url => {
    vi.mocked(send).mockResolvedValueOnce({ title: 'Находка', image_id: 'social-photo' }).mockResolvedValueOnce({})
    const wrapper = form()
    await wrapper.findAll('.type-switch button')[1].trigger('click')
    await wrapper.get('input[type="url"]').setValue(url)
    await wrapper.get('input[type="url"]').trigger('blur')
    await flushPromises()
    expect(send).toHaveBeenCalledWith('/metadata', { url })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith('/items', expect.objectContaining({ url, image_id: 'social-photo', description: null }))
  })
  it('ignores metadata when the source URL changes during the request', async () => {
    let resolve!: (value: unknown) => void
    vi.mocked(send).mockImplementationOnce(() => new Promise(r => { resolve = r }))
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
