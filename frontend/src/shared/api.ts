import { ref } from 'vue'
import type { components } from './api-schema'

export type User = components['schemas']['UserOut']
export type Item = components['schemas']['ItemOut']
export type ItemInput = components['schemas']['ItemInput']
export type ItemCreate = components['schemas']['ItemCreate']
export type Metadata = components['schemas']['MetadataOut']
export type Session = components['schemas']['SessionOut']

export const session = ref<Session | null>(null)
export const authReady = ref(false)
export const invalidation = ref(0)

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

export function clearSession() {
  session.value = null
  invalidation.value++
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (session.value) headers.set('X-CSRF-Token', session.value.csrf_token)
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, { ...options, headers, credentials: 'same-origin', cache: 'no-store' })
  } catch {
    throw new ApiError(0, 'Не удалось связаться с сервером. Проверьте подключение и попробуйте ещё раз')
  }
  if (!response.ok) {
    if ([401, 403].includes(response.status)) clearSession()
    const body = await response.json().catch(() => ({}))
    const detail = body.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((e: { msg: string }) => e.msg.replace(/^Value error, /, '')).join('. ')
      : 'Не удалось выполнить запрос. Попробуйте ещё раз'
    throw new ApiError(response.status, message)
  }
  return response.status === 204 ? undefined as T : response.json()
}

export function send<T>(path: string, body?: unknown, method = 'POST') {
  return api<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) })
}

export function imageUrl(id: string) { return `/api/v1/media/${encodeURIComponent(id)}` }

export function itemTitle(item: Pick<Item, 'title' | 'url'>) {
  if (item.title) return item.title
  try { return new URL(item.url || '').hostname.replace(/^www\./, '') } catch { return 'Подарок' }
}

export function formatPrice(item: Pick<Item, 'price' | 'currency'> & { price_mode?: Item['price_mode'] }) {
  if (item.price === null || item.price === undefined || !item.currency) return 'Бесценно'
  const prefix = item.price_mode === 'from' ? 'От ' : ''
  try { return prefix + new Intl.NumberFormat('ru-RU', { style: 'currency', currency: item.currency, maximumFractionDigits: 2 }).format(Number(item.price)) }
  catch { return `${prefix}${item.price} ${item.currency}` }
}
