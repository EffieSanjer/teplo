import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import WishlistPage from './WishlistPage.vue'
import { api, send, session } from '../shared/api'

vi.mock('../shared/api', async importOriginal => ({
  ...await importOriginal<typeof import('../shared/api')>(), api: vi.fn(), send: vi.fn(),
}))

const friend = { id: 'friend', display_name: 'Аня', is_friend: true, can_surprise: true }
const wish = {
  id: 'wish', recipient_id: 'friend', author_id: 'friend', author_name: 'Аня', list_type: 'wishlist',
  item_type: 'idea', title: 'Подсказка', image_id: null, description: null, url: null,
  price: null, currency: null, price_mode: 'approximate', archived_at: null,
  created_at: '2026-11-13T12:00:00', can_manage: false, image_is_icon: false,
}
let wrapper: VueWrapper | undefined
beforeEach(() => {
  vi.resetAllMocks()
  session.value = { user: { id: 'me', display_name: 'Я', is_friend: false, can_surprise: false }, community_id: 'personal', csrf_token: 'csrf' }
  vi.mocked(api).mockImplementation(async path => path === '/users/friend' ? friend : [])
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; session.value = null })

async function open(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/me', component: WishlistPage },
    { path: '/users/:id/wishlist', component: WishlistPage },
    { path: '/users/:id/surprises', component: WishlistPage },
  ] })
  await router.push(path); await router.isReady()
  wrapper = mount(WishlistPage, { global: { plugins: [router], stubs: {
    ItemCard: { props: ['item'], template: '<button class="test-item" @click="$emit(\'open\', item)">{{ item.title }}</button>' },
    ItemForm: { props: ['recipientId', 'listType'], template: '<div class="test-form">{{ recipientId }}:{{ listType }}</div>' },
    MasonryGrid: { template: '<div><slot /></div>' },
    Modal: { props: ['title'], template: '<section role="dialog"><h2>{{ title }}</h2><slot /></section>' },
  } } })
  await flushPromises()
  return router
}

describe('friend surprise lists', () => {
  it('makes the own wishlist a personal corner with an avatar fallback and an add action', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/users/me' ? session.value!.user : [])
    await open('/me')
    expect(wrapper!.get('.personal-intro h1').text()).toBe('Вишлист')
    expect(wrapper!.text()).not.toContain('Мой маленький мир')
    expect(wrapper!.get('.personal-name').text()).toContain('Я')
    expect(wrapper!.get('.personal-avatar img').attributes('src')).toBe('/api/v1/users/me/avatar')
    await wrapper!.get('.personal-avatar img').trigger('error')
    expect(wrapper!.get('.personal-avatar').text()).toBe('Я')
    await wrapper!.get('[aria-label="Добавить желание"]').trigger('click')
    expect(wrapper!.get('.test-form').text()).toBe('me:wishlist')
  })
  it('places certificates in a collapsed section above the wishlist without duplicating cards', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/users/friend' ? friend : [wish, { ...wish, id: 'shop', item_type: 'certificate', title: 'Магазин' }])
    await open('/users/friend/wishlist')
    expect(wrapper!.find('.page-heading .count').exists()).toBe(false)
    const section = wrapper!.get('details.certificates-section')
    expect(section.attributes('open')).toBeUndefined()
    expect(section.get('summary').text()).toContain('Сертификаты1')
    expect(section.findAll('.test-item')).toHaveLength(1)
    expect(wrapper!.findAll('.test-item')).toHaveLength(2)
    expect(section.element.compareDocumentPosition(wrapper!.get('.test-item:not(.certificate-rail .test-item)').element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    ;(section.element as HTMLDetailsElement).open = true
    expect((section.element as HTMLDetailsElement).open).toBe(true)
  })
  it('shows the surprise tab and opens the form without group membership', async () => {
    await open('/users/friend/surprises')
    expect(wrapper!.find('a[href="/users/friend/surprises"]').exists()).toBe(true)
    expect(wrapper!.text()).toContain('подтверждённые друзья получателя')
    await wrapper!.get('[aria-label="Добавить сюрприз"]').trigger('click')
    expect(wrapper!.get('.test-form').text()).toBe('friend:surprise')
  })

  it('copies a friend wish into surprises and navigates to the shared list', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/users/friend' ? friend : [wish])
    vi.mocked(send).mockResolvedValue({ ...wish, id: 'surprise', list_type: 'surprise' })
    const router = await open('/users/friend/wishlist')
    await wrapper!.get('.test-item').trigger('click'); await flushPromises()
    const copy = wrapper!.get('[aria-label="Создать сюрприз"]')
    expect(copy).toBeDefined()
    await copy.trigger('click'); await flushPromises()
    expect(send).toHaveBeenCalledWith('/items/wish/surprise')
    expect(router.currentRoute.value.path).toBe('/users/friend/surprises')
  })

  it('does not request or display a list of surprises for yourself', async () => {
    const router = await open('/users/me/surprises')
    expect(router.currentRoute.value.path).toBe('/me')
    expect(vi.mocked(api).mock.calls.some(([path]) => path.endsWith('/items/surprise'))).toBe(false)
    expect(wrapper!.find('.profile-tabs').exists()).toBe(false)
  })

  it('keeps the same friend heading and tabs while loading the next list', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/users/friend' ? friend : [wish])
    const router = await open('/users/friend/wishlist')
    let finish!: (value: unknown) => void
    vi.mocked(api).mockImplementation(path => path === '/users/friend/items/surprise'
      ? new Promise(resolve => { finish = resolve }) : Promise.resolve(friend))
    await router.push('/users/friend/surprises'); await flushPromises()
    expect(wrapper!.get('h1').text()).toBe('Аня')
    expect(wrapper!.find('a[href="/users/friend/surprises"]').exists()).toBe(true)
    expect(wrapper!.get('[role="status"]').attributes('aria-label')).toBe('Загрузка списка')
    expect(wrapper!.findAll('.test-item')).toHaveLength(0)
    finish([]); await flushPromises()
    expect(wrapper!.get('h1').text()).toBe('Аня')
    expect(wrapper!.find('[role="status"]').exists()).toBe(false)
  })

  it('clears retained profile and records if access is revoked during a tab change', async () => {
    const router = await open('/users/friend/wishlist')
    vi.mocked(api).mockRejectedValue(new Error('Нет доступа'))
    await router.push('/users/friend/surprises'); await flushPromises()
    expect(wrapper!.get('h1').text()).not.toBe('Аня')
    expect(wrapper!.get('[role="alert"]').text()).toBe('Нет доступа')
    expect(wrapper!.find('a[href="/users/friend/surprises"]').exists()).toBe(false)
  })
})
