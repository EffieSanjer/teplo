const tokenPattern = /^[A-Za-z0-9_-]{43}$/

export function invitationToken(value: string): string | undefined {
  const input = value.trim()
  if (tokenPattern.test(input)) return input
  const start = /^friend_([A-Za-z0-9_-]{43})$/.exec(input)
  if (start) return start[1]
  try {
    const url = new URL(input)
    if (url.protocol !== 'https:' || url.hostname !== 't.me') return
    const payload = url.searchParams.get('startapp') || url.searchParams.get('start') || ''
    return /^friend_([A-Za-z0-9_-]{43})$/.exec(payload)?.[1]
  } catch {
    return
  }
}
