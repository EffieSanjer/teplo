/** Russian plural form for a count: one / few / many. */
export function plural(
  count: number,
  one: string,
  few: string,
  many: string,
): string {
  const absolute = Math.abs(count) % 100
  const last = absolute % 10
  if (absolute > 10 && absolute < 20) return many
  if (last === 1) return one
  if (last >= 2 && last <= 4) return few
  return many
}

export function surprisesLabel(count: number): string {
  return `${count} ${plural(count, 'сюрприз', 'сюрприза', 'сюрпризов')}`
}

export function wishesLabel(count: number): string {
  return `${count} ${plural(count, 'желание', 'желания', 'желаний')}`
}
