import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import WishlistPage from '../../../src/pages/WishlistPage.vue'
import { api, send, session } from '../../../src/shared/api'

vi.mock('../../../src/shared/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../../src/shared/api')>()),
  api: vi.fn(),
  send: vi.fn(),
}))

const friend = { id: 'friend', display_name: 'Аня', is_friend: true, can_surprise: true }
const wish = {
  id: 'wish',
  recipient_id: 'friend',
  author_id: 'friend',
  author_name: 'Аня',
  list_type: 'wishlist',
  item_type: 'idea',
  title: 'Подсказка',
  image_id: null,
  description: null,
  url: null,
  price: null,
  currency: null,
  price_mode: 'approximate',
  archived_at: null,
  created_at: '2026-11-13T12:00:00',
  can_manage: false,
  image_is_icon: false,
}
let wrapper: VueWrapper | undefined
beforeEach(() => {
  vi.resetAllMocks()
  session.value = {
    user: { id: 'me', display_name: 'Я', is_friend: false, can_surprise: false },
    community_id: 'personal',
    csrf_token: 'csrf',
  }
  vi.mocked(api).mockImplementation(async (path) => (path === '/users/friend' ? friend : []))
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
  wrapper?.unmount()
  wrapper = undefined
  session.value = null
  vi.unstubAllGlobals()
})

async function open(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/me', component: WishlistPage },
      { path: '/users/:id/wishlist', component: WishlistPage },
      { path: '/users/:id/surprises', component: WishlistPage },
    ],
  })
  await router.push(path)
  await router.isReady()
  wrapper = mount(WishlistPage, {
    global: {
      plugins: [router],
      stubs: {
        ItemCard: {
          props: ['item'],
          template:
            '<button class="test-item" @click="$emit(\'open\', item)">{{ item.title }}</button>',
        },
        ItemForm: {
          props: ['recipientId', 'listType', 'seed', 'initialType'],
          template:
            '<div class="test-form" :data-url="seed?.url" :data-title="seed?.title" :data-price="seed?.price" :data-image="seed?.image_id" :data-type="initialType">{{ recipientId }}:{{ listType }}</div>',
        },
        MasonryGrid: { template: '<div><slot /></div>' },
        Modal: {
          props: ['title'],
          template: '<section role="dialog"><h2>{{ title }}</h2><slot /></section>',
        },
      },
    },
  })
  await flushPromises()
  return router
}

describe('friend surprise lists', () => {
  it('makes the own wishlist a personal corner with an avatar fallback and an add action', async () => {
    vi.mocked(api).mockImplementation(async (path) =>
      path === '/users/me' ? session.value!.user : [],
    )
    await open('/me')
    expect(wrapper!.get('header.board-journal h1').text()).toContain('Моя доска')
    expect(wrapper!.get('header.board-journal h1 em').text()).toBe('желаний.')
    expect(wrapper!.text()).not.toContain('Мой маленький мир')
    expect(wrapper!.get('header.board-journal p.hidden').text()).toBe('Я')
    expect(wrapper!.get('header.board-journal img').attributes('src')).toBe(
      '/api/v1/users/me/avatar',
    )
    await wrapper!.get('header.board-journal img').trigger('error')
    expect(wrapper!.find('header.board-journal img').exists()).toBe(false)
    expect(wrapper!.get('header.board-journal .size-14 span').text()).toBe('Я')
    await wrapper!.get('[aria-label="Добавить желание"]').trigger('click')
    expect(wrapper!.get('.test-form').text()).toBe('me:wishlist')
  })
  it('opens a prefilled wish from a bot link and removes the launch query', async () => {
    vi.mocked(api).mockImplementation(async (path) =>
      path === '/users/me' ? session.value!.user : [],
    )
    const router = await open(
      '/me?url=' +
        encodeURIComponent('https://shop.example/item') +
        '&title=Lamp&price=1200&currency=RUB&image_id=11111111-1111-4111-8111-111111111111',
    )
    const form = wrapper!.get('.test-form')
    expect(form.attributes('data-url')).toBe('https://shop.example/item')
    expect(form.attributes('data-title')).toBe('Lamp')
    expect(form.attributes('data-price')).toBe('1200')
    expect(form.attributes('data-image')).toBe('11111111-1111-4111-8111-111111111111')
    expect(form.attributes('data-type')).toBe('gift')
    expect(router.currentRoute.value.query.url).toBeUndefined()
    expect(router.currentRoute.value.query.title).toBeUndefined()
    expect(router.currentRoute.value.query.image_id).toBeUndefined()
  })
  it('places certificates in a dedicated carousel without duplicating cards', async () => {
    vi.mocked(api).mockImplementation(async (path) =>
      path === '/users/friend'
        ? friend
        : [wish, { ...wish, id: 'shop', item_type: 'certificate', title: 'Магазин' }],
    )
    await open('/users/friend/wishlist')
    expect(wrapper!.find('.page-heading .count').exists()).toBe(false)
    expect(wrapper!.find('details.certificates-section').exists()).toBe(false)
    const section = wrapper!.get('section.certificate-carousel')
    expect(section.attributes('aria-label')).toBe('Сертификаты')
    expect(section.find('.certificate-carousel-cover').exists()).toBe(true)
    expect(section.get('.certificate-carousel-track').attributes('tabindex')).toBe('0')
    expect(section.findAll('.certificate-shop')).toHaveLength(1)
    expect(wrapper!.findAll('.collection-grid .test-item')).toHaveLength(1)
    expect(section.find('.certificate-carousel-add').exists()).toBe(false)
    const wishCard = wrapper!.get('.collection-grid .test-item')
    expect(section.element.contains(wishCard.element)).toBe(false)
    expect(
      wishCard.element.compareDocumentPosition(section.element) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })
  it('shows the surprise tab and opens the form without group membership', async () => {
    await open('/users/friend/surprises')
    expect(wrapper!.find('a[href="/users/friend/surprises"]').exists()).toBe(true)
    expect(wrapper!.text()).toContain('Получатель не видит этот список.')
    await wrapper!.get('[aria-label="Добавить сюрприз"]').trigger('click')
    expect(wrapper!.get('.test-form').text()).toBe('friend:surprise')
  })

  it('opens a friend wish and adds a surprise for the friend from the shared list', async () => {
    vi.mocked(api).mockImplementation(async (path) => (path === '/users/friend' ? friend : [wish]))
    const router = await open('/users/friend/wishlist')
    await wrapper!.get('.test-item').trigger('click')
    await flushPromises()
    expect(send).not.toHaveBeenCalled()
    await wrapper!.get('a[href="/users/friend/surprises"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/users/friend/surprises')
    await wrapper!.get('[aria-label="Добавить сюрприз"]').trigger('click')
    expect(wrapper!.get('.test-form').text()).toBe('friend:surprise')
  })

  it('does not request or display a list of surprises for yourself', async () => {
    const router = await open('/users/me/surprises')
    expect(router.currentRoute.value.path).toBe('/me')
    expect(vi.mocked(api).mock.calls.some(([path]) => path.endsWith('/items/surprise'))).toBe(false)
    expect(wrapper!.find('.profile-tabs').exists()).toBe(false)
  })

  it('keeps the same friend heading and tabs while loading the next list', async () => {
    vi.mocked(api).mockImplementation(async (path) => (path === '/users/friend' ? friend : [wish]))
    const router = await open('/users/friend/wishlist')
    let finish!: (value: unknown) => void
    vi.mocked(api).mockImplementation((path) =>
      path === '/users/friend/items/surprise'
        ? new Promise((resolve) => {
            finish = resolve
          })
        : Promise.resolve(friend),
    )
    await router.push('/users/friend/surprises')
    await flushPromises()
    expect(wrapper!.get('h1').text()).toBe('Аня')
    expect(wrapper!.find('a[href="/users/friend/surprises"]').exists()).toBe(true)
    expect(wrapper!.get('[role="status"]').attributes('aria-label')).toBe('Загрузка списка')
    expect(wrapper!.findAll('.test-item')).toHaveLength(0)
    finish([])
    await flushPromises()
    expect(wrapper!.get('h1').text()).toBe('Аня')
    expect(wrapper!.find('[role="status"]').exists()).toBe(false)
  })

  it('clears retained profile and records if access is revoked during a tab change', async () => {
    const router = await open('/users/friend/wishlist')
    vi.mocked(api).mockRejectedValue(new Error('Нет доступа'))
    await router.push('/users/friend/surprises')
    await flushPromises()
    expect(wrapper!.get('h1').text()).not.toBe('Аня')
    expect(wrapper!.get('[role="alert"]').text()).toBe('Нет доступа')
    expect(wrapper!.find('a[href="/users/friend/surprises"]').exists()).toBe(false)
  })
})
