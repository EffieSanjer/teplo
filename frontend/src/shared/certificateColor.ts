export type CertificateColor = { background: string; ink: string; logoBackground?: string }

// Match the image's outer edge, including opaque white, without altering the logo.
export function certificateLogoBackground(pixels: ArrayLike<number>, width: number, height: number): string {
  const edge: number[] = []
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    if (x !== 0 && y !== 0 && x !== width - 1 && y !== height - 1) continue
    const i = (y * width + x) * 4
    edge.push(pixels[i]!, pixels[i + 1]!, pixels[i + 2]!, pixels[i + 3]!)
  }
  const opaque = edge.filter((_, i) => i % 4 === 3 && edge[i]! >= 128).length
  if (!edge.length || opaque < edge.length / 8) return 'transparent'
  // Reuse the dominant-colour selection, but include white perimeter pixels.
  const buckets = new Map<string, { count: number; rgb: number[] }>()
  for (let i = 0; i < edge.length; i += 4) {
    if (edge[i + 3]! < 128) continue
    const rgb = edge.slice(i, i + 3)
    const key = rgb.map(value => value >> 5).join(',')
    const bucket = buckets.get(key) || { count: 0, rgb: [0, 0, 0] }
    bucket.count++
    rgb.forEach((value, channel) => { bucket.rgb[channel]! += value })
    buckets.set(key, bucket)
  }
  const dominant = [...buckets.values()].sort((a, b) => b.count - a.count)[0]!
  return `rgb(${dominant.rgb.map(value => Math.round(value / dominant.count)).join(', ')})`
}

// Ignore transparent padding and near-white backgrounds; favour the brand's colour.
export function certificateColor(pixels: ArrayLike<number>): CertificateColor | null {
  const buckets = new Map<string, { weight: number; r: number; g: number; b: number }>()
  for (let i = 0; i < pixels.length; i += 4) {
    const r = pixels[i]!, g = pixels[i + 1]!, b = pixels[i + 2]!, alpha = pixels[i + 3]! / 255
    if (alpha < .5 || Math.min(r, g, b) > 235) continue
    const saturation = (Math.max(r, g, b) - Math.min(r, g, b)) / 255
    const weight = alpha * (saturation > .15 ? 4 : 1)
    const key = `${r >> 5},${g >> 5},${b >> 5}`
    const bucket = buckets.get(key) || { weight: 0, r: 0, g: 0, b: 0 }
    bucket.weight += weight; bucket.r += r * weight; bucket.g += g * weight; bucket.b += b * weight
    buckets.set(key, bucket)
  }
  const dominant = [...buckets.values()].sort((a, b) => b.weight - a.weight)[0]
  if (!dominant) return null
  const rgb = [dominant.r, dominant.g, dominant.b].map(value => Math.round(value / dominant.weight))
  const linear = rgb.map(value => value / 255 <= .04045 ? value / 255 / 12.92 : ((value / 255 + .055) / 1.055) ** 2.4)
  const luminance = .2126 * linear[0]! + .7152 * linear[1]! + .0722 * linear[2]!
  return { background: `rgb(${rgb.join(', ')})`, ink: luminance > .179 ? '#111111' : '#ffffff' }
}

const cache = new Map<string, Promise<CertificateColor | null>>()
export function loadCertificateColor(src: string): Promise<CertificateColor | null> {
  const existing = cache.get(src)
  if (existing) return existing
  const result = new Promise<CertificateColor | null>(resolve => {
    const image = new Image()
    image.onload = () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width = 32; canvas.height = 32
        const context = canvas.getContext('2d', { willReadFrequently: true })
        if (!context) { resolve(null); return }
        context.drawImage(image, 0, 0, 32, 32)
        const pixels = context.getImageData(0, 0, 32, 32).data
        const tone = certificateColor(pixels)
        resolve(tone ? { ...tone, logoBackground: certificateLogoBackground(pixels, 32, 32) } : null)
      } catch { resolve(null) }
    }
    image.onerror = () => resolve(null)
    // Stored media is same-origin; no external URLs or new uploads are involved.
    image.src = src
  })
  cache.set(src, result)
  if (cache.size > 200) cache.delete(cache.keys().next().value!)
  return result
}
