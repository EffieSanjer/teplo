interface TelegramApp {
  initData: string
  ready(): void
  expand(): void
  openLink(url: string): void
  BackButton: { show(): void; hide(): void; onClick(fn: () => void): void; offClick(fn: () => void): void }
  onEvent(name: string, fn: () => void): void
  offEvent(name: string, fn: () => void): void
  colorScheme?: 'light' | 'dark'
}

declare global { interface Window { Telegram?: { WebApp?: TelegramApp } } }

function app() {
  const sdk = window.Telegram?.WebApp
  return sdk?.initData ? sdk : undefined
}

export async function initTelegram() {
  // Ordinary localhost/browser usage must not wait for an external Telegram script.
  const hasTelegramLaunch = /tgWebAppData=/.test(window.location.hash + window.location.search)
  if (!window.Telegram?.WebApp && hasTelegramLaunch) {
    await new Promise<void>(resolve => {
      const script = document.createElement('script')
      script.src = 'https://telegram.org/js/telegram-web-app.js'
      script.async = true
      const timer = setTimeout(resolve, 8000)
      const finish = () => { clearTimeout(timer); resolve() }
      script.onload = finish; script.onerror = finish
      document.head.appendChild(script)
    })
  }
  app()?.ready(); app()?.expand()
}
export function initData() { return app()?.initData || '' }
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
