import { certificateStore } from './certificateStores'

export type LinkBookmark = {
  host: string
  name: string
  mark: string
  hint: string
  icon: string | null
}

function telegramBookmark(url: URL, host: string): LinkBookmark {
  const parts = url.pathname.split('/').filter(Boolean)
  const channel = parts[0] === 's' ? parts[1] : parts[0]
  if (channel && /^[A-Za-z][A-Za-z0-9_]{3,}$/.test(channel)) {
    return {
      host,
      name: `@${channel}`,
      mark: channel[0]!.toUpperCase(),
      hint: parts.length > 1 && parts.at(-1) !== channel ? 'Пост в Telegram' : 'Канал в Telegram',
      icon: null,
    }
  }
  return { host, name: 'Telegram', mark: 'T', hint: 'По ссылке', icon: null }
}

export function linkBookmark(url: string): LinkBookmark | null {
  try {
    const parsed = new URL(url)
    if (!['http:', 'https:'].includes(parsed.protocol) || !parsed.hostname) return null
    const host = parsed.hostname.toLowerCase().replace(/^www\./, '')
    const store = certificateStore(url)
    if (store) {
      return {
        host,
        name: store.name,
        mark: [...store.name][0]!.toUpperCase(),
        hint: 'По ссылке',
        icon: store.icon,
      }
    }
    if (
      host === 't.me' ||
      host === 'telegram.me' ||
      host.endsWith('.t.me') ||
      host.endsWith('.telegram.me')
    ) {
      return telegramBookmark(parsed, host)
    }
    if (host === 'pin.it' || /(^|\.)pinterest\.[a-z.]+$/.test(host)) {
      return { host, name: 'Pinterest', mark: 'P', hint: 'По ссылке', icon: null }
    }
    if (host === 'instagram.com' || host.endsWith('.instagram.com')) {
      return { host, name: 'Instagram', mark: 'I', hint: 'По ссылке', icon: null }
    }
    const label = host.split('.')[0] || host
    return {
      host,
      name: host,
      mark: [...label][0]!.toUpperCase(),
      hint: 'По ссылке',
      icon: null,
    }
  } catch {
    return null
  }
}
