// Share sheets may copy a caption, a newline and a URL rather than just the URL.
export function extractSharedLink(text: string): string | null {
  const candidates = text.match(/https?:\/\/[^\s<>"«»“”]+|\bwww\.[^\s<>"«»“”]+/gi) || []
  for (let candidate of candidates) {
    candidate = candidate.replace(/[.,!?:;…'’]+$/u, '')
    // Remove surrounding prose punctuation, but keep balanced URL parentheses.
    for (const [open, close] of [
      ['(', ')'],
      ['[', ']'],
      ['{', '}'],
    ]) {
      while (
        candidate.endsWith(close!) &&
        candidate.split(close!).length > candidate.split(open!).length
      ) {
        candidate = candidate.slice(0, -1)
      }
    }
    candidate = candidate.replace(/[.,!?:;…'’]+$/u, '')
    if (/^www\./i.test(candidate)) candidate = `https://${candidate}`
    if (candidate.length > 2048) continue
    try {
      const url = new URL(candidate)
      if (
        !['http:', 'https:'].includes(url.protocol) ||
        !url.hostname ||
        url.username ||
        url.password
      )
        continue
      return candidate
    } catch {
      /* Try the next URL; server-side URL and SSRF validation still apply. */
    }
  }
  return null
}

export type SharedDetails = {
  url: string
  title?: string
  price?: string
  currency?: string
  price_mode?: 'from'
}

export function extractSharedDetails(text: string): SharedDetails | null {
  const url = extractSharedLink(text)
  if (!url) return null
  const result: SharedDetails = { url }
  // Only explicit currency amounts: sizes, model numbers and discount percentages are not prices.
  const currencyToken = '(?:₽|руб(?:лей|ля|ль)?\\.?|р\\.|RUB|RUR|USD|EUR|GEL|KZT|BYN|€|\\$|₸|₾)'
  const amountToken = '(?:\\d{1,3}(?:[ \\u00a0\\u202f]\\d{3})+|\\d+)(?:[.,]\\d{1,2})?'
  const spaces = '[ \\t\\u00a0\\u202f]*'
  const prices = new RegExp(
    `(?<![\\p{L}\\d.,])(?:(от)[ \\t]+)?(${amountToken})${spaces}(${currencyToken})(?![\\p{L}\\d])|(?<![\\p{L}\\d])(${currencyToken})${spaces}(${amountToken})(?![\\d.,])`,
    'giu',
  )
  let caption = text.slice(0, 16000).replace(/https?:\/\/[^\s<>"«»“”]+|\bwww\.[^\s<>"«»“”]+/gi, '')
  const matches = [...caption.matchAll(prices)]
  const currency = (token: string) => {
    if (/^(₽|руб|р\.|RUB|RUR)/i.test(token)) return 'RUB'
    if (/^(€|EUR)$/i.test(token)) return 'EUR'
    if (/^(\$|USD)$/i.test(token)) return 'USD'
    if (token === '₸') return 'KZT'
    if (token === '₾') return 'GEL'
    return token.toUpperCase()
  }
  const values = matches.map((match) => ({
    price: (match[2] || match[5])!.replace(/[\s\u00a0\u202f]/g, '').replace(',', '.'),
    currency: currency((match[3] || match[4])!),
  }))
  if (
    values.length &&
    values.every(
      (value) => value.price === values[0]!.price && value.currency === values[0]!.currency,
    ) &&
    Number(values[0]!.price) < 1e12
  ) {
    Object.assign(result, values[0])
    if (matches[0]![1]) result.price_mode = 'from'
  }
  caption = caption
    .replace(prices, '')
    .replace(/(?:цена|стоимость)\s*:?/gi, '')
    .replace(/\s+за\s*$/iu, '')
  const lines = caption
    .split(/[\r\n]+/)
    .map((line) =>
      line
        .replace(/^[\s:—–\-.,;!«»"()[\]]+|[\s:—–\-.,;!«»"()[\]]+$/g, '')
        .replace(/^(?:название|товар)\s*:\s*/i, '')
        .trim(),
    )
    .filter(
      (line) =>
        /\p{L}/u.test(line) &&
        !/^(?:поделиться.*|смотри(?:те)?.*|посмотри(?:те)?.*|это точно тво[её].*|пост|ссылка|купить|перейти|скидка.*)$/i.test(
          line,
        ),
    )
  if (lines[0]) result.title = lines[0].slice(0, 200)
  return result
}
