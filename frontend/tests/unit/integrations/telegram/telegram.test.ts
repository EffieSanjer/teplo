import { afterEach, describe, expect, it, vi } from 'vitest'

afterEach(() => {
  delete window.Telegram
  window.history.replaceState(null, '', '/')
  document
    .querySelectorAll('script[src*="telegram-web-app.js"]')
    .forEach((script) => script.remove())
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.resetModules()
})

describe('Telegram launch credentials', () => {
  const raw = 'user=%7B%22id%22%3A123%7D&auth_date=123&hash=untrusted-test-hash'

  it('recovers the invitation and credentials from the original navigation after history replacement', async () => {
    const start = 'friend_' + 'n'.repeat(43)
    const url =
      `${window.location.origin}/#` +
      new URLSearchParams({
        tgWebAppData: raw + '&start_param=' + start,
        tgWebAppPlatform: 'tdesktop',
      })
    vi.stubGlobal('performance', { getEntriesByType: () => [{ name: url }] })
    window.history.replaceState(null, '', '/me')
    const telegram = await import('../../../../src/integrations/telegram/index')
    expect(telegram.initData()).toBe(raw + '&start_param=' + start)
    expect(telegram.launchStartParam()).toBe(start)
    expect(telegram.launchDiagnostics()).toContain('исходный адрес: приглашение')
    expect(telegram.launchDiagnostics()).not.toContain(start)
    expect(telegram.launchDiagnostics()).not.toContain(raw)
  })

  it('ignores a cross-origin navigation entry', async () => {
    vi.stubGlobal('performance', {
      getEntriesByType: () => [
        { name: 'https://other.test/#tgWebAppData=' + encodeURIComponent(raw) },
      ],
    })
    const telegram = await import('../../../../src/integrations/telegram/index')
    expect(telegram.initData()).toBe('')
    expect(telegram.launchStartParam()).toBe('')
  })

  it('prefers a new launch target over the initial one', async () => {
    const first = 'friend_' + 'a'.repeat(43),
      second = 'friend_' + 'b'.repeat(43)
    window.history.replaceState(null, '', '/#tgWebAppStartParam=' + first)
    const telegram = await import('../../../../src/integrations/telegram/index')
    window.history.replaceState(null, '', '/me#tgWebAppStartParam=' + second)
    expect(telegram.launchStartParam()).toBe(second)
    window.history.replaceState(null, '', '/me')
    window.Telegram = {
      WebApp: { initData: raw + '&start_param=' + second } as NonNullable<
        Window['Telegram']
      >['WebApp'],
    }
    expect(telegram.launchStartParam()).toBe(second)
  })

  it('observes resumed and changed launches and removes listeners on cleanup', async () => {
    const telegram = await import('../../../../src/integrations/telegram/index')
    const callback = vi.fn(),
      cleanup = telegram.onLaunchChange(callback)
    window.dispatchEvent(new Event('hashchange'))
    window.dispatchEvent(new Event('focus'))
    window.dispatchEvent(new Event('pageshow'))
    expect(callback).toHaveBeenCalledTimes(3)
    cleanup()
    window.dispatchEvent(new Event('hashchange'))
    window.dispatchEvent(new Event('focus'))
    expect(callback).toHaveBeenCalledTimes(3)
  })

  it('preserves an explicit bot-button invitation independently of an older start parameter', async () => {
    const token = 'c'.repeat(43)
    const oldStart = 'friend_' + 'd'.repeat(43)
    window.history.replaceState(
      null,
      '',
      `/friends?invite=${token}#tgWebAppData=` +
        encodeURIComponent(raw + '&start_param=' + oldStart),
    )
    const telegram = await import('../../../../src/integrations/telegram/index')
    window.history.replaceState(null, '', '/me')
    expect(telegram.launchInvitation()).toBe(token)
    expect(telegram.launchStartParam()).toBe(oldStart)
  })

  it.each(['hash', 'query'])(
    'preserves a separate start parameter from the launch %s before router redirects',
    async (source) => {
      const start = 'friend_' + 'a'.repeat(43)
      const params = new URLSearchParams({
        tgWebAppData: raw,
        tgWebAppStartParam: start,
      }).toString()
      window.history.replaceState(null, '', '/' + (source === 'hash' ? '#' : '?') + params)
      const telegram = await import('../../../../src/integrations/telegram/index')
      window.history.replaceState(null, '', '/me')
      expect(telegram.launchStartParam()).toBe(start)
      expect(telegram.initData()).toBe(raw)
    },
  )

  it('reads a start parameter from signed launch data when no separate parameter is supplied', async () => {
    const start = 'friend_' + 'b'.repeat(43)
    window.history.replaceState(
      null,
      '',
      '/#tgWebAppData=' + encodeURIComponent(raw + '&start_param=' + start),
    )
    const telegram = await import('../../../../src/integrations/telegram/index')
    window.history.replaceState(null, '', '/me')
    expect(telegram.launchStartParam()).toBe(start)
  })

  it('preserves the exact initData from a mobile launch without the SDK', async () => {
    window.history.replaceState(null, '', '/me#tgWebAppData=' + encodeURIComponent(raw))
    const telegram = await import('../../../../src/integrations/telegram/index')
    expect(telegram.initData()).toBe(raw)
    // Vue Router can remove the fragment when redirecting the root URL.
    window.history.replaceState(null, '', '/me')
    expect(telegram.initData()).toBe(raw)
  })

  it('supports launch parameters in the query string', async () => {
    window.history.replaceState(null, '', '/me?tgWebAppData=' + encodeURIComponent(raw))
    const telegram = await import('../../../../src/integrations/telegram/index')
    expect(telegram.initData()).toBe(raw)
  })

  it('prefers credentials supplied by the Telegram SDK', async () => {
    window.history.replaceState(null, '', '/me#tgWebAppData=' + encodeURIComponent(raw))
    window.Telegram = {
      WebApp: { initData: 'sdk-credentials' } as NonNullable<Window['Telegram']>['WebApp'],
    }
    const telegram = await import('../../../../src/integrations/telegram/index')
    expect(telegram.initData()).toBe('sdk-credentials')
  })

  it('still makes launch credentials available if the SDK request fails', async () => {
    window.history.replaceState(null, '', '/me#tgWebAppData=' + encodeURIComponent(raw))
    const telegram = await import('../../../../src/integrations/telegram/index')
    const initialized = telegram.initTelegram()
    document
      .querySelector<HTMLScriptElement>('script[src*="telegram-web-app.js"]')!
      .dispatchEvent(new Event('error'))
    await initialized
    expect(telegram.initData()).toBe(raw)
  })

  it('does not wait forever for a blocked SDK', async () => {
    vi.useFakeTimers()
    window.history.replaceState(null, '', '/me#tgWebAppData=' + encodeURIComponent(raw))
    const telegram = await import('../../../../src/integrations/telegram/index')
    const initialized = telegram.initTelegram()
    await vi.advanceTimersByTimeAsync(8000)
    await initialized
    expect(telegram.initData()).toBe(raw)
  })

  it('does not authenticate an ordinary browser or trust tgWebAppData from storage', async () => {
    sessionStorage.setItem('tgWebAppData', raw)
    try {
      const telegram = await import('../../../../src/integrations/telegram/index')
      await telegram.initTelegram()
      expect(telegram.initData()).toBe('')
      expect(document.querySelector('script[src*="telegram-web-app.js"]')).toBeNull()
    } finally {
      sessionStorage.removeItem('tgWebAppData')
    }
  })
})
