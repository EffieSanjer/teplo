import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import FriendsPage from './FriendsPage.vue'
import { api, send, session } from '../shared/api'
import { shareInvitation } from '../integrations/telegram'

vi.mock('../shared/api', async importOriginal => ({
  ...await importOriginal<typeof import('../shared/api')>(), api: vi.fn(), send: vi.fn(),
}))
vi.mock('../integrations/telegram', () => ({ shareInvitation: vi.fn() }))

const token = 'a'.repeat(43)
const friend = { id: 'friend', display_name: 'Аня', is_friend: true, can_surprise: false }
let wrapper: VueWrapper | undefined
beforeEach(() => {
  vi.resetAllMocks()
  session.value = { user: { id: 'me', display_name: 'Я', is_friend: false, can_surprise: false }, community_id: 'personal', csrf_token: 'csrf' }
  vi.mocked(api).mockResolvedValue([])
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; session.value = null })

async function open(path = '/friends') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/friends', component: FriendsPage }] })
  await router.push(path)
  await router.isReady()
  wrapper = mount(FriendsPage, { global: { plugins: [router], stubs: {
    Modal: { props: ['title'], template: '<section role="dialog"><h2>{{ title }}</h2><slot /></section>' },
  } } })
  await flushPromises()
  return router
}

async function click(text: string) {
  const button = wrapper!.findAll('button').find(b => b.text() === text)
  expect(button, `Button: ${text}`).toBeDefined()
  await button!.trigger('click')
  await flushPromises()
}

describe('friend invitations', () => {
  it('creates a private link, shares it explicitly, and can revoke it', async () => {
    const url = `https://t.me/test_bot?start=friend_${token}`
    vi.mocked(send).mockResolvedValue({ url, expires_at: '2026-11-20T12:00:00' })
    await open()
    await click('Пригласить друга')
    expect(send).toHaveBeenCalledWith('/friends/invitations')
    expect(wrapper!.get('input[readonly]').element).toHaveProperty('value', url)
    expect(shareInvitation).not.toHaveBeenCalled()
    await click('Отправить другу')
    expect(shareInvitation).toHaveBeenCalledWith(url)
    await click('Отозвать ссылку')
    expect(send).toHaveBeenLastCalledWith('/friends/invitations', undefined, 'DELETE')
    expect(wrapper!.find('[role="dialog"]').exists()).toBe(false)
  })

  it('previews without granting friendship and requires a confirmation', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/users' ? [] : { inviter: friend, own: false })
    const router = await open(`/friends?invite=${token}`)
    expect(wrapper!.text()).toContain('Аня')
    expect(send).not.toHaveBeenCalled()
    vi.mocked(send).mockResolvedValue(friend)
    vi.mocked(api).mockResolvedValue([friend])
    await click('Добавить в друзья')
    expect(send).toHaveBeenCalledWith('/friends/accept', { token })
    expect(router.currentRoute.value.query.invite).toBeUndefined()
    expect(wrapper!.get('.friend-card').text()).toContain('Аня')
  })

  it('declines without a mutation', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/users' ? [] : { inviter: friend, own: false })
    const router = await open(`/friends?invite=${token}`)
    await click('Не сейчас')
    expect(send).not.toHaveBeenCalled()
    expect(router.currentRoute.value.query.invite).toBeUndefined()
  })

  it('does not allow accepting your own invitation', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/users' ? [] : { inviter: friend, own: true })
    await open(`/friends?invite=${token}`)
    expect(wrapper!.text()).toContain('Это ваше приглашение')
    expect(wrapper!.findAll('button').some(b => b.text() === 'Добавить в друзья')).toBe(false)
  })

  it('shows invalid and expired invitation errors without automatic acceptance', async () => {
    vi.mocked(api).mockImplementation(async path => {
      if (path === '/users') return []
      throw new Error('Приглашение недействительно или уже использовано')
    })
    await open(`/friends?invite=${token}`)
    expect(wrapper!.get('[role="alert"]').text()).toContain('Приглашение недействительно')
    expect(send).not.toHaveBeenCalled()
  })

  it('removes an explicit friend only after confirmation', async () => {
    vi.mocked(api).mockResolvedValue([friend])
    await open()
    await click('Удалить из друзей')
    expect(send).not.toHaveBeenCalled()
    vi.mocked(send).mockResolvedValue(undefined)
    vi.mocked(api).mockResolvedValue([])
    const confirm = wrapper!.get('[role="dialog"]').findAll('button').find(b => b.text() === 'Удалить из друзей')!
    await confirm.trigger('click'); await flushPromises()
    expect(send).toHaveBeenCalledWith('/friends/friend', undefined, 'DELETE')
    expect(wrapper!.find('.friend-card').exists()).toBe(false)
  })
})
