import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, session } from './api'

beforeEach(() => { vi.useFakeTimers(); session.value = null })
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

function reply(status: number, body = '{}') {
  return new Response(body, { status })
}

describe('API resilience during tunnel interruptions', () => {
  it('retries a GET after temporary connection failures', async () => {
    const fetch = vi.fn().mockRejectedValueOnce(new TypeError('offline'))
      .mockResolvedValueOnce(reply(530, 'cloudflare error'))
      .mockResolvedValueOnce(reply(200, '{"status":"ok"}'))
    vi.stubGlobal('fetch', fetch)
    const result = api('/health')
    await vi.runAllTimersAsync()
    expect(await result).toEqual({ status: 'ok' })
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: 'same-origin', cache: 'no-store' })
    expect(fetch.mock.calls[0][1].headers.get('X-Wishlist-Request')).toBe('same-origin')
  })

  it('bounds a stalled GET and retries it', async () => {
    const fetch = vi.fn().mockImplementationOnce((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('Timeout', 'AbortError')))
    })).mockResolvedValueOnce(reply(200, '[]'))
    vi.stubGlobal('fetch', fetch)
    const result = api('/users')
    await vi.runAllTimersAsync()
    expect(await result).toEqual([])
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('also bounds a body that stalls after receiving headers', async () => {
    const fetch = vi.fn().mockImplementationOnce((_url, options) => Promise.resolve({
      ok: true, status: 200,
      text: () => new Promise((_resolve, reject) => {
        options.signal.addEventListener('abort', () => reject(new DOMException('Timeout', 'AbortError')))
      }),
    })).mockResolvedValueOnce(reply(200, '[]'))
    vi.stubGlobal('fetch', fetch)
    const result = api('/users')
    await vi.runAllTimersAsync()
    expect(await result).toEqual([])
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it.each([401, 403, 404, 422, 429])('does not retry a definitive HTTP %s', async status => {
    const fetch = vi.fn().mockResolvedValue(reply(status, '{"detail":"Отказ"}'))
    vi.stubGlobal('fetch', fetch)
    await expect(api('/users')).rejects.toMatchObject({ status, message: 'Отказ' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it.each(['POST', 'PUT', 'PATCH', 'DELETE'])('never replays a %s mutation', async method => {
    const fetch = vi.fn().mockResolvedValue(reply(503, '{"detail":"Недоступно"}'))
    vi.stubGlobal('fetch', fetch)
    await expect(api('/items', { method })).rejects.toMatchObject({ status: 503 })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('does not replay a mutation on a lost connection', async () => {
    const fetch = vi.fn().mockRejectedValue(new TypeError('offline'))
    vi.stubGlobal('fetch', fetch)
    await expect(api('/items', { method: 'POST' })).rejects.toBeInstanceOf(ApiError)
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('reports failure after a finite number of read attempts', async () => {
    const fetch = vi.fn().mockRejectedValue(new TypeError('offline'))
    vi.stubGlobal('fetch', fetch)
    const result = expect(api('/users')).rejects.toMatchObject({ status: 0 })
    await vi.runAllTimersAsync()
    await result
    expect(fetch).toHaveBeenCalledTimes(3)
  })

  it('respects caller cancellation without retries', async () => {
    const controller = new AbortController()
    const fetch = vi.fn().mockImplementation((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    }))
    vi.stubGlobal('fetch', fetch)
    const result = expect(api('/users', { signal: controller.signal })).rejects.toMatchObject({ status: 0 })
    controller.abort()
    await result
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
