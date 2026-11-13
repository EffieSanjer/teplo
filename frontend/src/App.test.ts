import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from './App.vue'
import { api, ApiError, authReady, send, session } from './shared/api'

vi.mock('./shared/api', async importOriginal => ({
  ...await importOriginal<typeof import('./shared/api')>(),
  api: vi.fn(), send: vi.fn(),
}))
vi.mock('./integrations/telegram', () => ({
  initTelegram: () => new Promise(() => {}),
  initData: () => 'untrusted-launch-credentials',
  backButton: () => () => {},
}))

let wrapper: VueWrapper | undefined
beforeEach(() => {
  vi.clearAllMocks()
  session.value = null
  authReady.value = false
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined })

async function open(path = '/me') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: ['/me', '/friends'].map(path => ({ path, component: { template: '<div />' } })),
  })
  await router.push(path)
  await router.isReady()
  wrapper = mount(App, { global: { plugins: [router], stubs: { ThemeControl: true } } })
  await flushPromises()
  return wrapper
}

describe('startup on an unreliable mobile connection', () => {
  it('preserves an invitation through login and never automatically accepts it', async () => {
    vi.mocked(api).mockResolvedValueOnce({ dev_login_enabled: false, telegram_enabled: true })
      .mockRejectedValueOnce(new ApiError(401, 'Нет сессии'))
    vi.mocked(send).mockResolvedValueOnce({ user: { id: 'me', display_name: 'Я' }, community_id: 'personal', csrf_token: 'csrf' })
    const path = '/friends?invite=' + 'a'.repeat(43)
    const view = await open(path)
    expect(view.vm.$route.fullPath).toBe(path)
    expect(send).toHaveBeenCalledTimes(1)
    expect(send).toHaveBeenCalledWith('/auth/telegram', { init_data: 'untrusted-launch-credentials' })
  })
  it('does not wait for the optional SDK before attempting authentication', async () => {
    vi.mocked(api).mockResolvedValueOnce({ dev_login_enabled: false, telegram_enabled: true })
      .mockRejectedValueOnce(new ApiError(401, 'Нет сессии'))
    vi.mocked(send).mockRejectedValueOnce(new ApiError(401, 'Недействительные данные входа'))
    const view = await open()
    expect(send).toHaveBeenCalledWith('/auth/telegram', { init_data: 'untrusted-launch-credentials' })
    expect(view.get('[role="alert"]').text()).toBe('Недействительные данные входа')
    expect(authReady.value).toBe(true)
  })

  it.each([0, 403, 503, 530])('does not discard a session by reauthenticating on error %s', async status => {
    vi.mocked(api).mockResolvedValueOnce({ dev_login_enabled: false, telegram_enabled: true })
      .mockRejectedValueOnce(new ApiError(status, 'Соединение недоступно'))
    const view = await open()
    expect(send).not.toHaveBeenCalled()
    expect(view.get('[role="alert"]').text()).toBe('Соединение недоступно')
    expect(view.get('button.text-button').text()).toBe('Повторить подключение')
  })
})
