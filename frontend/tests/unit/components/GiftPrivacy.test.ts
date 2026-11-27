import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ItemForm from '../../../src/components/ItemForm.vue'
import ItemCard from '../../../src/components/ItemCard.vue'
import ItemDetail from '../../../src/components/ItemDetail.vue'
import { api, send, type Item } from '../../../src/shared/api'

vi.mock('../../../src/shared/api', async (original) => ({
  ...(await original<typeof import('../../../src/shared/api')>()),
  send: vi.fn(),
  api: vi.fn(async () => []),
}))

const item: Item = {
  most_wanted: false,
  id: 'wish',
  recipient_id: 'friend',
  author_id: 'friend',
  author_name: 'Друг',
  list_type: 'wishlist',
  item_type: 'gift',
  title: 'Подарок',
  description: null,
  url: 'https://example.com',
  image_id: null,
  image_is_icon: false,
  price: null,
  currency: null,
  price_mode: 'approximate',
  archived_at: null,
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
  can_manage: false,
  surprise_visibility: 'friends',
  can_reserve: true,
  reservation: null,
}
const wrappers: ReturnType<typeof mount>[] = []
const modal = { template: '<section><slot /></section>' }

beforeEach(() => {
  vi.mocked(send).mockReset()
  vi.mocked(send).mockResolvedValue({})
  vi.mocked(api).mockReset()
  vi.mocked(api).mockResolvedValue([])
  vi.stubGlobal('matchMedia', () => ({ matches: false }))
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    },
  )
  HTMLDialogElement.prototype.showModal = vi.fn()
})
afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.unstubAllGlobals()
})

describe('gift privacy and compact certificates', () => {
  it('opens certificates in a compact dialog with direct management actions', async () => {
    const wrapper = mount(ItemDetail, {
      props: {
        item: { ...item, item_type: 'certificate', can_manage: true, description: 'Любимые книги' },
        ownProfile: true,
        busy: false,
      },
      global: { stubs: { Modal: modal, Teleport: true } },
    })
    wrappers.push(wrapper)
    expect(wrapper.find('.certificate-mini').exists()).toBe(true)
    expect(wrapper.find('[data-sheet-handle]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Любимые книги')
    const button = (label: string) =>
      wrapper.findAll('button').find((entry) => entry.text().includes(label))!
    expect(button('Ссылка').exists()).toBe(true)
    await button('Редактировать').trigger('click')
    expect(wrapper.emitted('edit')).toHaveLength(1)
    await button('Удалить').trigger('click')
    expect(wrapper.emitted('delete')).toHaveLength(1)
  })

  it.each(['gift', 'certificate'] as const)('names the friend who reserved a %s', (item_type) => {
    const wrapper = mount(ItemCard, {
      props: {
        item: { ...item, item_type, reservation: { reserved_by_me: false, reserver_name: 'Анна' } },
        index: 0,
      },
    })
    wrappers.push(wrapper)
    expect(wrapper.text()).toContain('Уже забронировано')
    expect(wrapper.text()).not.toContain('Анна')
    expect(wrapper.text()).not.toContain('????')
  })

  it('labels your own reservation', () => {
    const wrapper = mount(ItemCard, {
      props: {
        item: { ...item, reservation: { reserved_by_me: true, reserver_name: 'Анна' } },
        index: 0,
      },
    })
    wrappers.push(wrapper)
    expect(wrapper.find('[aria-label="Вы забронировали"]').exists()).toBe(true)
  })

  it('selects a popular store and saves its identity while preserving the note', async () => {
    const wrapper = mount(ItemForm, {
      props: { recipientId: 'friend', listType: 'wishlist', initialType: 'certificate' },
      global: { stubs: { Modal: modal } },
    })
    wrappers.push(wrapper)
    await wrapper.get('textarea').setValue('Любимые книги')
    await wrapper.get('.certificate-store-tile').trigger('click')
    expect((wrapper.get('.source-section input[type="url"]').element as HTMLInputElement).value).toBe(
      'https://ozon.ru/',
    )
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({
        title: 'Ozon',
        url: 'https://ozon.ru/',
        description: 'Любимые книги',
      }),
    )
  })

  it('defaults surprises to friends and saves a private choice', async () => {
    const wrapper = mount(ItemForm, {
      props: { recipientId: 'friend', listType: 'surprise' },
      global: { stubs: { Modal: modal } },
    })
    wrappers.push(wrapper)
    expect(
      wrapper.findAll('button').find((button) => button.text() === 'Всем друзьям')!.attributes('aria-pressed'),
    ).toBe('true')
    await wrapper.findAll('button').find((button) => button.text() === 'Только мне')!.trigger('click')
    await wrapper.get('input[maxlength="100"]').setValue('Секрет')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenCalledWith(
      '/items',
      expect.objectContaining({ surprise_visibility: 'private' }),
    )
  })

  it('automatically fills certificate identity, removes uploads and limits notes', async () => {
    vi.mocked(send).mockResolvedValueOnce({ title: 'Shop', image_id: 'logo', image_is_icon: true })
    const wrapper = mount(ItemForm, {
      props: { recipientId: 'me', listType: 'wishlist', initialType: 'certificate' },
      global: { stubs: { Modal: modal } },
    })
    wrappers.push(wrapper)
    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
    expect(wrapper.find('.identity-section').exists()).toBe(false)
    expect(wrapper.get('#personal-description-hint').text()).toContain('/ 100')
    await wrapper.get('.source-section input[type="url"]').setValue('https://example.com')
    await wrapper.get('.source-section input[type="url"]').trigger('blur')
    await flushPromises()
    expect(wrapper.text()).toContain('Shop')
    expect(wrapper.get('img.site-icon').attributes('src')).toContain('logo')
    await wrapper.get('textarea').setValue('Любимые книги')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(send).toHaveBeenLastCalledWith(
      '/items',
      expect.objectContaining({ title: 'Shop', image_id: 'logo', description: 'Любимые книги' }),
    )
  })

  it('keeps certificate cards compact by showing only the store identity', () => {
    const wrapper = mount(ItemCard, {
      props: {
        item: { ...item, item_type: 'certificate', description: 'Любимые книги' },
        index: 0,
      },
    })
    wrappers.push(wrapper)
    expect(wrapper.get('.certificate-face').text()).not.toContain('Любимые книги')
    expect(wrapper.get('h3').text()).toBe('Подарок')
    expect(wrapper.find('.certificate-subtitle').exists()).toBe(false)
  })

  it('offers reservation and cancellation, while hiding controls from the owner', async () => {
    const wrapper = mount(ItemDetail, {
      props: { item, ownProfile: false, busy: false },
      global: { stubs: { Teleport: true } },
    })
    wrappers.push(wrapper)
    await flushPromises()
    const reserve = () =>
      wrapper
        .findAll('button')
        .find((button) => /Забронировать подарок|Снять бронь/.test(button.text()))
    await reserve()!.trigger('click')
    expect(wrapper.emitted('reserve')?.[0]).toEqual([item])
    await wrapper.setProps({
      item: { ...item, reservation: { reserved_by_me: true, reserver_name: 'Я' } },
    })
    expect(reserve()!.text()).toBe('Снять бронь')
    await wrapper.setProps({ ownProfile: true })
    expect(reserve()).toBeUndefined()
    expect(wrapper.text()).not.toContain('Вы забронировали')
  })
})
