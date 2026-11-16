export type AvatarPalette = { primary: string; secondary: string }

/** WCAG contrast against the portrait-derived, theme-tinted identity surface. */
export function portraitInk(color: string, dark: boolean): string {
  const channels = color.startsWith('#')
    ? color.slice(1).match(/.{2}/g)!.map(value => parseInt(value, 16))
    : (color.match(/[\d.]+/g) || []).slice(0, 3).map(Number)
  if (channels.length !== 3) return dark ? '#f7f8f2' : '#142019'
  const base = dark ? [9, 12, 11] : [114, 123, 118]
  const weight = dark ? .12 : .76
  const luminance = channels.map((channel, index) => {
    const value = (channel * weight + base[index]! * (1 - weight)) / 255
    return value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4
  }).reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index]!, 0)
  return (luminance + .05) / .05 > 1.05 / (luminance + .05) ? '#101813' : '#f7f8f2'
}

export function avatarFallback(id: string): AvatarPalette {
  const hash = Array.from(id).reduce((value, char) => value + char.charCodeAt(0), 0)
  const palettes = [
    { primary: '#788271', secondary: '#b49a76' },
    { primary: '#ad7267', secondary: '#765c85' },
    { primary: '#9c8b7a', secondary: '#596e81' },
    { primary: '#6f807a', secondary: '#b08a69' },
  ]
  return palettes[hash % palettes.length]!
}

export function sampleAvatarPalette(image: HTMLImageElement): AvatarPalette | undefined {
  try {
    const canvas = document.createElement('canvas')
    canvas.width = 32; canvas.height = 32
    const context = canvas.getContext('2d', { willReadFrequently: true })
    if (!context) return
    context.drawImage(image, 0, 0, 32, 32)
    const pixels = context.getImageData(0, 0, 32, 32).data
    const buckets = new Map<string, { weight: number; rgb: number[] }>()
    for (let i = 0; i < pixels.length; i += 4) {
      const rgb = [pixels[i]!, pixels[i + 1]!, pixels[i + 2]!]
      const max = Math.max(...rgb), min = Math.min(...rgb)
      if (pixels[i + 3]! < 128 || max < 30 || min > 235) continue
      const weight = 1 + (max - min) / 64
      const key = rgb.map(channel => channel >> 5).join(',')
      const bucket = buckets.get(key) || { weight: 0, rgb: [0, 0, 0] }
      bucket.weight += weight
      rgb.forEach((channel, index) => { bucket.rgb[index]! += channel * weight })
      buckets.set(key, bucket)
    }
    const colors = [...buckets.values()].sort((a, b) => b.weight - a.weight)
      .map(bucket => bucket.rgb.map(channel => Math.round(channel / bucket.weight)))
    const primary = colors[0]
    if (!primary) return
    const secondary = colors.find(color => color.reduce((sum, channel, index) => sum + (channel - primary[index]!) ** 2, 0) > 6400) || primary
    const css = (rgb: number[]) => `rgb(${rgb.join(', ')})`
    return { primary: css(primary), secondary: css(secondary) }
  } catch { /* Same-origin avatars normally allow sampling; retain the fallback otherwise. */ }
}
