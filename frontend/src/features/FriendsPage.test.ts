import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import FriendsPage from './FriendsPage.vue'
import { api, send, session } from '../shared/api'
import { shareInvitation } from '../integrations/telegram'

vi.mock('../shared/api', async importOriginal => ({
  ...await importOriginal<typeof import('../shared/api')>(), api: vi.fn(), send: vi.fn(),
}))
vi.mock('../integrations/telegram', () => ({ shareInvitation: vi.fn(), launchDiagnostics: () => 'Запуск v2' }))

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
  it('previews a pasted direct link without automatically accepting it', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/users' ? [] : { inviter: friend, own: false })
    const router = await open()
    await click('У меня есть приглашение')
    await wrapper!.get('input[aria-label="Полученная ссылка приглашения"]').setValue(`https://t.me/test_bot?startapp=friend_${token}`)
    await wrapper!.get('form').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.query.invite).toBe(token)
    expect(api).toHaveBeenCalledWith(`/friends/invitations/${token}`)
    expect(wrapper!.text()).toContain('Аня')
    expect(send).not.toHaveBeenCalled()
  })
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
    expect(wrapper!.get('.friend-profile').text()).toContain('Аня')
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
    await wrapper!.get('button[aria-label="Удалить из друзей: Аня"]').trigger('click')
    await flushPromises()
    expect(send).not.toHaveBeenCalled()
    vi.mocked(send).mockResolvedValue(undefined)
    vi.mocked(api).mockResolvedValue([])
    const confirm = wrapper!.get('[role="dialog"]').findAll('button').find(b => b.text() === 'Удалить из друзей')!
    await confirm.trigger('click'); await flushPromises()
    expect(send).toHaveBeenCalledWith('/friends/friend', undefined, 'DELETE')
    expect(wrapper!.find('.friend-profile').exists()).toBe(false)
  })
  it('searches ignoring case and surrounding whitespace, and clears the query', async () => {
    vi.mocked(api).mockResolvedValue([friend, { ...friend, id: 'other', display_name: 'Борис' }])
    await open()
    await wrapper!.get('input[aria-label="Найти друга"]').setValue('  АНЯ  ')
    expect(wrapper!.findAll('.friend-profile')).toHaveLength(1)
    expect(wrapper!.get('.friend-profile h3').text()).toBe('Аня')
    await wrapper!.get('button[aria-label="Очистить поиск"]').trigger('click')
    expect(wrapper!.findAll('.friend-profile')).toHaveLength(2)
  })
  it('retains friends when a background refresh fails', async () => {
    vi.mocked(api).mockResolvedValue([friend])
    await open()
    vi.mocked(api).mockRejectedValue(new Error('Нет сети'))
    const now = vi.spyOn(Date, 'now').mockReturnValue(Date.now() + 20000)
    const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
    window.dispatchEvent(new Event('focus'))
    await flushPromises()
    expect(wrapper!.get('.friend-profile h3').text()).toBe('Аня')
    expect(wrapper!.get('[role="alert"]').text()).toContain('Нет сети')
    now.mockRestore(); visibility.mockRestore()
  })
  it('can retry creating an invitation after a network error', async () => {
    vi.mocked(send).mockRejectedValueOnce(new Error('Нет сети'))
    await open()
    await click('Пригласить друга')
    expect(wrapper!.get('[role="alert"]').text()).toBe('Нет сети')
    vi.mocked(send).mockResolvedValue({ url: 'https://example.com/invite', expires_at: '2026-11-20' })
    await click('Попробовать ещё раз')
    expect(wrapper!.get('input[readonly]').element).toHaveProperty('value', 'https://example.com/invite')
    expect(wrapper!.find('[role="alert"]').exists()).toBe(false)
  })
  it('shows a recoverable error when sharing is unavailable', async () => {
    vi.mocked(send).mockResolvedValue({ url: 'https://example.com/invite', expires_at: '2026-11-20' })
    vi.mocked(shareInvitation).mockImplementation(() => { throw new Error('Unavailable') })
    await open()
    await click('Пригласить друга')
    await click('Отправить другу')
    expect(wrapper!.get('[role="alert"]').text()).toContain('Скопируйте ссылку')
    expect(wrapper!.find('input[readonly]').exists()).toBe(true)
  })
})
