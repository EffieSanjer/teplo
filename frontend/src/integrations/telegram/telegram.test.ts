import { afterEach, describe, expect, it, vi } from 'vitest'

afterEach(() => {
  delete window.Telegram
  window.history.replaceState(null, '', '/')
  document.querySelectorAll('script[src*="telegram-web-app.js"]').forEach(script => script.remove())
  vi.useRealTimers()
  vi.resetModules()
})

describe('Telegram launch credentials', () => {
  const raw = 'user=%7B%22id%22%3A123%7D&auth_date=123&hash=untrusted-test-hash'

  it('preserves the exact initData from a mobile launch without the SDK', async () => {
    window.history.replaceState(null, '', '/me#tgWebAppData=' + encodeURIComponent(raw))
    const telegram = await import('./index')
    expect(telegram.initData()).toBe(raw)
    // Vue Router can remove the fragment when redirecting the root URL.
    window.history.replaceState(null, '', '/me')
    expect(telegram.initData()).toBe(raw)
  })

  it('supports launch parameters in the query string', async () => {
    window.history.replaceState(null, '', '/me?tgWebAppData=' + encodeURIComponent(raw))
    const telegram = await import('./index')
    expect(telegram.initData()).toBe(raw)
  })

  it('prefers credentials supplied by the Telegram SDK', async () => {
    window.history.replaceState(null, '', '/me#tgWebAppData=' + encodeURIComponent(raw))
    window.Telegram = { WebApp: { initData: 'sdk-credentials' } as NonNullable<Window['Telegram']>['WebApp'] }
    const telegram = await import('./index')
    expect(telegram.initData()).toBe('sdk-credentials')
  })

  it('still makes launch credentials available if the SDK request fails', async () => {
    window.history.replaceState(null, '', '/me#tgWebAppData=' + encodeURIComponent(raw))
    const telegram = await import('./index')
    const initialized = telegram.initTelegram()
    document.querySelector<HTMLScriptElement>('script[src*="telegram-web-app.js"]')!
      .dispatchEvent(new Event('error'))
    await initialized
    expect(telegram.initData()).toBe(raw)
  })

  it('does not wait forever for a blocked SDK', async () => {
    vi.useFakeTimers()
    window.history.replaceState(null, '', '/me#tgWebAppData=' + encodeURIComponent(raw))
    const telegram = await import('./index')
    const initialized = telegram.initTelegram()
    await vi.advanceTimersByTimeAsync(8000)
    await initialized
    expect(telegram.initData()).toBe(raw)
  })

  it('does not authenticate an ordinary browser or trust tgWebAppData from storage', async () => {
    sessionStorage.setItem('tgWebAppData', raw)
    try {
      const telegram = await import('./index')
      await telegram.initTelegram()
      expect(telegram.initData()).toBe('')
      expect(document.querySelector('script[src*="telegram-web-app.js"]')).toBeNull()
    } finally {
      sessionStorage.removeItem('tgWebAppData')
    }
  })
})
