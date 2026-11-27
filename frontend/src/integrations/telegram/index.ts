interface TelegramApp {
  initData: string
  ready(): void
  expand(): void
  openLink(url: string): void
  openTelegramLink?(url: string): void
  disableVerticalSwipes?(): void
  enableVerticalSwipes?(): void
  BackButton: {
    show(): void
    hide(): void
    onClick(fn: () => void): void
    offClick(fn: () => void): void
  }
  onEvent(name: string, fn: () => void): void
  offEvent(name: string, fn: () => void): void
  colorScheme?: 'light' | 'dark'
  platform?: string
  version?: string
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramApp }
  }
}

function parameters(url: string) {
  const parsed = new URL(url, window.location.href)
  return { query: parsed.searchParams, hash: new URLSearchParams(parsed.hash.slice(1)) }
}

function launchValue(name: string, url = window.location.href) {
  const { query, hash } = parameters(url)
  return hash.get(name) || query.get(name) || ''
}
// WebView/history redirects can remove the launch fragment before Vue loads.
// Only use this document's navigation entry, never credentials from storage.
function navigationUrl() {
  const name = performance.getEntriesByType?.('navigation')[0]?.name
  try {
    if (name && new URL(name).origin === window.location.origin) return name
  } catch {
    /* No navigation entry. */
  }
  return window.location.href
}
const originalUrl = navigationUrl()
function launchData() {
  return launchValue('tgWebAppData')
}
const initialLaunchData = launchData()
const originalLaunchData = launchValue('tgWebAppData', originalUrl)
const initialInvite =
  new URLSearchParams(window.location.search).get('invite') ||
  parameters(originalUrl).query.get('invite') ||
  ''
function readStartParam(url = window.location.href) {
  return (
    launchValue('tgWebAppStartParam', url) ||
    new URLSearchParams(launchValue('tgWebAppData', url)).get('start_param') ||
    ''
  )
}
// Telegram can supply the navigation target separately from signed initData.
// Capture it before Vue Router replaces the launch fragment on / -> /me.
const initialStartParam = readStartParam()
const originalStartParam = readStartParam(originalUrl)

function app() {
  const sdk = window.Telegram?.WebApp
  return sdk?.initData ? sdk : undefined
}

export async function initTelegram() {
  // Ordinary localhost/browser usage must not wait for an external Telegram script.
  const hasTelegramLaunch = Boolean(initialLaunchData || launchData() || originalLaunchData)
  if (!window.Telegram?.WebApp && hasTelegramLaunch) {
    await new Promise<void>((resolve) => {
      const script = document.createElement('script')
      script.src = 'https://telegram.org/js/telegram-web-app.js'
      script.async = true
      const timer = setTimeout(resolve, 8000)
      const finish = () => {
        clearTimeout(timer)
        resolve()
      }
      script.onload = finish
      script.onerror = finish
      document.head.appendChild(script)
    })
  }
  app()?.ready()
  app()?.expand()
}
// These are untrusted credentials until the backend checks Telegram's signature
// and auth_date. Never use parsed user fields as a client-side login substitute.
export function initData() {
  return app()?.initData || launchData() || initialLaunchData || originalLaunchData
}
// Navigation only: the backend still validates the invitation and the session.
// A start parameter never grants access or accepts an invitation on its own.
export function launchStartParam() {
  return (
    readStartParam() ||
    new URLSearchParams(app()?.initData).get('start_param') ||
    initialStartParam ||
    originalStartParam ||
    ''
  )
}
export function launchInvitation() {
  return initialInvite
}
export function onLaunchChange(callback: () => void) {
  const visible = () => {
    if (document.visibilityState === 'visible') callback()
  }
  const events = ['hashchange', 'popstate', 'pageshow', 'focus'] as const
  events.forEach((event) => window.addEventListener(event, callback))
  document.addEventListener('visibilitychange', visible)
  const sdk = app()
  sdk?.onEvent('activated', callback)
  return () => {
    events.forEach((event) => window.removeEventListener(event, callback))
    document.removeEventListener('visibilitychange', visible)
    sdk?.offEvent('activated', callback)
  }
}
// Deliberately expose presence/shape only, never URLs, credentials or tokens.
export function launchDiagnostics() {
  const describe = (value: string) =>
    !value ? 'нет' : /^friend_[A-Za-z0-9_-]{43}$/.test(value) ? 'приглашение' : 'другой параметр'
  const sdk = app()
  const platform =
    launchValue('tgWebAppPlatform') ||
    launchValue('tgWebAppPlatform', originalUrl) ||
    sdk?.platform ||
    ''
  const knownPlatform = ['tdesktop', 'web', 'weba', 'webk', 'android', 'ios', 'macos'].includes(
    platform,
  )
    ? platform
    : 'не определена'
  return `Запуск v2 · платформа: ${knownPlatform} · URL: ${describe(readStartParam())} · исходный адрес: ${describe(originalStartParam)} · SDK: ${describe(new URLSearchParams(sdk?.initData).get('start_param') || '')} · сохранено при загрузке: ${describe(initialStartParam)} · явное приглашение: ${initialInvite ? 'есть' : 'нет'}`
}
export function openExternal(url: string) {
  if (app()) app()!.openLink(url)
  else window.open(url, '_blank', 'noopener,noreferrer')
}
export function backButton(visible: boolean, callback: () => void) {
  const sdk = app()
  if (!sdk) return () => {}
  if (visible) sdk.BackButton.show()
  else sdk.BackButton.hide()
  sdk.BackButton.onClick(callback)
  return () => sdk.BackButton.offClick(callback)
}
// A downward swipe closes/minimizes the Mini App. Suspended while dialogs are open so
// scrolling inside them cannot accidentally close it; nested dialogs share one lock.
let swipeLocks = 0
export function lockVerticalSwipes() {
  const sdk = app()
  swipeLocks += 1
  if (swipeLocks === 1) sdk?.disableVerticalSwipes?.()
  return () => {
    swipeLocks = Math.max(0, swipeLocks - 1)
    if (swipeLocks === 0) sdk?.enableVerticalSwipes?.()
  }
}
export function shareInvitation(url: string) {
  const target = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent('Давай делиться желаниями в «Кстати»')}`
  const sdk = app()
  if (sdk?.openTelegramLink) sdk.openTelegramLink(target)
  else window.open(target, '_blank', 'noopener,noreferrer')
}
