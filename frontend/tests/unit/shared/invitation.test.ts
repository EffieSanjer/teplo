import { describe, expect, it } from 'vitest'
import { invitationToken } from '../../../src/shared/invitation'

describe('invitationToken', () => {
  const token = 'a'.repeat(20) + '--_' + 'b'.repeat(20)
  it.each(['start', 'startapp'])(
    'extracts a complete token from a Telegram %s link',
    (parameter) => {
      expect(invitationToken(`https://t.me/example_bot?${parameter}=friend_${token}`)).toBe(token)
    },
  )
  it('accepts a named Mini App link and surrounding whitespace', () => {
    expect(invitationToken(` https://t.me/example_bot/app?startapp=friend_${token} `)).toBe(token)
  })
  it('does not split tokens containing underscores or hyphens', () => {
    expect(invitationToken(`friend_${token}`)).toBe(token)
  })
  it.each([
    'https://evil.test/?startapp=friend_',
    'javascript:friend_',
    'https://t.me.evil.test/?startapp=friend_',
  ])('rejects unsupported links: %s', (prefix) => {
    expect(invitationToken(prefix + token)).toBeUndefined()
  })
})
