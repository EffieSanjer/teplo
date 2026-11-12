export function certificateTitle(title: string): { name: string; description: string } {
  // A spaced separator is a subtitle; keep hyphens inside brand names intact.
  const match = /\s+[-–—]\s+/.exec(title)
  if (!match || match.index === 0) return { name: title, description: '' }
  const name = title.slice(0, match.index).trim()
  const description = title.slice(match.index + match[0].length).trim()
  return name && description ? { name, description } : { name: title, description: '' }
}
