// Stable monochrome material variations; the active theme supplies the tones.
export function itemPalette(id: string) {
  const hash = Array.from(id).reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, 0)
  const tone = `--collection-tone-${hash % 4}`
  return {
    '--item-bg': `var(${tone})`,
    '--item-sheen': `var(--collection-sheen-${hash % 4})`,
    '--item-ink': 'var(--ink)',
    '--item-muted': 'var(--muted)',
    '--item-accent': 'var(--warm)',
    '--certificate-bg': `var(${tone})`,
    '--certificate-ink': 'var(--ink)',
    '--photo-bg': `var(${tone})`,
    '--glass-bg': `var(${tone})`,
    '--glass-blur-bg': `var(${tone})`,
    '--glass-ink': 'var(--ink)',
    '--glass-muted': 'var(--muted)',
    '--glass-edge': 'transparent',
  }
}
