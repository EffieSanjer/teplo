import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../../src/App.vue'
import { api, ApiError, authReady, send, session } from '../../src/shared/api'
import { launchInvitation, launchStartParam, onLaunchChange } from '../../src/integrations/telegram'

vi.mock('../../src/shared/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../src/shared/api')>()),
  api: vi.fn(),
  send: vi.fn(),
}))
vi.mock('../../src/integrations/telegram', () => ({
  initTelegram: () => new Promise(() => {}),
  initData: () => 'untrusted-launch-credentials',
  backButton: () => () => {},
  launchInvitation: vi.fn(() => ''),
  launchStartParam: vi.fn(() => ''),
  onLaunchChange: vi.fn(() => () => {}),
}))

let wrapper: VueWrapper | undefined
beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(launchInvitation).mockReturnValue('')
  vi.mocked(launchStartParam).mockReturnValue('')
  session.value = null
  authReady.value = false
})
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
})

async function open(path = '/me') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: ['/me', '/friends'].map((path) => ({ path, component: { template: '<div />' } })),
  })
  await router.push(path)
  await router.isReady()
  wrapper = mount(App, { global: { plugins: [router], stubs: { SettingsControl: true } } })
  await flushPromises()
  return wrapper
}

describe('startup on an unreliable mobile connection', () => {
  it('opens a direct invitation with an existing session and handles a new target on resume', async () => {
    vi.mocked(api)
      .mockResolvedValueOnce({ dev_login_enabled: false, telegram_enabled: true })
      .mockResolvedValueOnce({
        user: { id: 'me', display_name: 'Я' },
        community_id: 'personal',
        csrf_token: 'csrf',
      })
    vi.mocked(launchStartParam).mockReturnValue('friend_' + 'a'.repeat(43))
    const view = await open()
    expect(view.find('.topbar-actions').exists()).toBe(false)
    expect(view.find('.brand-description').exists()).toBe(false)
    expect(view.vm.$route.query.invite).toBe('a'.repeat(43))
    await view.vm.$router.replace('/me')
    const resume = vi.mocked(onLaunchChange).mock.calls[0]![0]
    resume()
    await flushPromises()
    expect(view.vm.$route.path).toBe('/me')
    vi.mocked(launchStartParam).mockReturnValue('friend_' + 'b'.repeat(43))
    resume()
    await flushPromises()
    expect(view.vm.$route.query.invite).toBe('b'.repeat(43))
    expect(send).not.toHaveBeenCalled()
  })

  it('prioritizes an explicit invitation without blocking later Telegram launches', async () => {
    vi.mocked(api)
      .mockResolvedValueOnce({ dev_login_enabled: false, telegram_enabled: true })
      .mockResolvedValueOnce({
        user: { id: 'me', display_name: 'Я' },
        community_id: 'personal',
        csrf_token: 'csrf',
      })
    vi.mocked(launchInvitation).mockReturnValue('a'.repeat(43))
    vi.mocked(launchStartParam).mockReturnValue('friend_' + 'b'.repeat(43))
    const view = await open('/friends?invite=' + 'a'.repeat(43))
    expect(view.vm.$route.query.invite).toBe('a'.repeat(43))
    await view.vm.$router.replace('/friends')
    vi.mocked(launchStartParam).mockReturnValue('friend_' + 'c'.repeat(43))
    vi.mocked(onLaunchChange).mock.calls[0]![0]()
    await flushPromises()
    expect(view.vm.$route.query.invite).toBe('c'.repeat(43))
    expect(send).not.toHaveBeenCalled()
  })
  it('preserves an invitation through login and never automatically accepts it', async () => {
    vi.mocked(api)
      .mockResolvedValueOnce({ dev_login_enabled: false, telegram_enabled: true })
      .mockRejectedValueOnce(new ApiError(401, 'Нет сессии'))
    vi.mocked(send).mockResolvedValueOnce({
      user: { id: 'me', display_name: 'Я' },
      community_id: 'personal',
      csrf_token: 'csrf',
    })
    const path = '/friends?invite=' + 'a'.repeat(43)
    const view = await open(path)
    expect(view.vm.$route.fullPath).toBe(path)
    expect(send).toHaveBeenCalledTimes(1)
    expect(send).toHaveBeenCalledWith('/auth/telegram', {
      init_data: 'untrusted-launch-credentials',
    })
  })
  it('enters immediately as the configured dev user when dev login is enabled', async () => {
    vi.mocked(api)
      .mockResolvedValueOnce({ dev_login_enabled: true, telegram_enabled: false })
      .mockRejectedValueOnce(new ApiError(401, 'Нет сессии'))
    vi.mocked(send).mockResolvedValueOnce({
      user: { id: 'dev-user', display_name: 'Тестовый пользователь' },
      community_id: 'personal',
      csrf_token: 'csrf',
    })
    const view = await open()
    expect(send).toHaveBeenCalledWith('/auth/dev', undefined)
    expect(session.value?.user.id).toBe('dev-user')
    expect(view.find('.login-page').exists()).toBe(false)
  })

  it('does not wait for the optional SDK before attempting authentication', async () => {
    vi.mocked(api)
      .mockResolvedValueOnce({ dev_login_enabled: false, telegram_enabled: true })
      .mockRejectedValueOnce(new ApiError(401, 'Нет сессии'))
    vi.mocked(send).mockRejectedValueOnce(new ApiError(401, 'Недействительные данные входа'))
    const view = await open()
    expect(send).toHaveBeenCalledWith('/auth/telegram', {
      init_data: 'untrusted-launch-credentials',
    })
    expect(view.get('[role="alert"]').text()).toBe('Недействительные данные входа')
    expect(authReady.value).toBe(true)
  })

  it.each([0, 403, 503, 530])(
    'does not discard a session by reauthenticating on error %s',
    async (status) => {
      vi.mocked(api)
        .mockResolvedValueOnce({ dev_login_enabled: false, telegram_enabled: true })
        .mockRejectedValueOnce(new ApiError(status, 'Соединение недоступно'))
      const view = await open()
      expect(send).not.toHaveBeenCalled()
      expect(view.get('[role="alert"]').text()).toBe('Соединение недоступно')
      expect(view.get('button.text-button').text()).toBe('Повторить подключение')
    },
  )
})
