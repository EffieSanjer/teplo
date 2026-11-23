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
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

export function clearSession() {
  session.value = null
  invalidation.value++
}

const temporaryStatuses = new Set([502, 503, 504, 530])

async function fetchResponse(url: string, options: RequestInit) {
  const reading = (options.method || 'GET').toUpperCase() === 'GET'
  const attempts = reading ? 3 : 1
  for (let attempt = 0; attempt < attempts; attempt++) {
    if (options.signal?.aborted) throw options.signal.reason || new Error('Request cancelled')
    const controller = new AbortController()
    const abort = () => controller.abort(options.signal?.reason)
    options.signal?.addEventListener('abort', abort, { once: true })
    const timer = setTimeout(() => controller.abort(), 12000)
    try {
      const response = await fetch(url, { ...options, signal: controller.signal })
      if (!reading || !temporaryStatuses.has(response.status) || attempt === attempts - 1) {
        // Read the body within the timeout too: a tunnel can stall after headers.
        const body = await response.text()
        return { ok: response.ok, status: response.status, body }
      }
      await response.body?.cancel()
    } catch (error) {
      if (options.signal?.aborted || attempt === attempts - 1) throw error
    } finally {
      clearTimeout(timer)
      options.signal?.removeEventListener('abort', abort)
    }
    await new Promise((resolve) => setTimeout(resolve, 1000 * (attempt + 1)))
  }
  throw new Error('Server unavailable')
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('X-Wishlist-Request', 'same-origin')
  if (options.body && !(options.body instanceof FormData))
    headers.set('Content-Type', 'application/json')
  if (session.value) headers.set('X-CSRF-Token', session.value.csrf_token)
  let response: Awaited<ReturnType<typeof fetchResponse>>
  try {
    response = await fetchResponse(`/api/v1${path}`, {
      ...options,
      headers,
      credentials: 'same-origin',
      cache: 'no-store',
    })
  } catch {
    throw new ApiError(
      0,
      'Не удалось связаться с сервером. Проверьте подключение и попробуйте ещё раз',
    )
  }
  if (!response.ok) {
    if ([401, 403].includes(response.status)) clearSession()
    let body
    try {
      body = JSON.parse(response.body)
    } catch {
      body = {}
    }
    const detail = body.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((e: { msg: string }) => e.msg.replace(/^Value error, /, '')).join('. ')
          : 'Не удалось выполнить запрос. Попробуйте ещё раз'
    throw new ApiError(response.status, message)
  }
  return response.status === 204 ? (undefined as T) : JSON.parse(response.body)
}

export function send<T>(path: string, body?: unknown, method = 'POST') {
  return api<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) })
}

export function imageUrl(id: string) {
  return `/api/v1/media/${encodeURIComponent(id)}`
}

export function itemTitle(item: Pick<Item, 'title' | 'url'>) {
  if (item.title) return item.title
  try {
    return new URL(item.url || '').hostname.replace(/^www\./, '')
  } catch {
    return 'Подарок'
  }
}

export function hasPrice(item: Pick<Item, 'price' | 'currency'>) {
  return (
    item.price !== null &&
    item.price !== undefined &&
    String(item.price).trim() !== '' &&
    Boolean(item.currency?.trim())
  )
}

export function formatPrice(
  item: Pick<Item, 'price' | 'currency'> & { price_mode?: Item['price_mode'] },
) {
  if (item.price === null || item.price === undefined || !item.currency) return 'Бесценно'
  const prefix = item.price_mode === 'from' ? 'От ' : ''
  try {
    return (
      prefix +
      new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: item.currency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(Number(item.price))
    )
  } catch {
    return `${prefix}${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(Number(item.price))} ${item.currency}`
  }
}
