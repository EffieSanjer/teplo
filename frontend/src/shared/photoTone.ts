// Blend the lower edge of a stored photo into its surrounding surface. White
// and transparent pixels are intentional; this is not brand-colour detection.
export function photoTone(pixels: ArrayLike<number>): string | undefined {
  const sum = [0, 0, 0]
  let weight = 0
  for (let i = 0; i < pixels.length; i += 4) {
    const alpha = pixels[i + 3]! / 255
    weight += alpha
    for (let channel = 0; channel < 3; channel++) sum[channel]! += pixels[i + channel]! * alpha
  }
  if (!weight) return undefined
  return `rgb(${sum.map(value => Math.round(value / weight)).join(', ')})`
}

export function samplePhotoTone(image: HTMLImageElement): string | undefined {
  try {
    const canvas = document.createElement('canvas')
    canvas.width = 24; canvas.height = 8
    const context = canvas.getContext('2d', { willReadFrequently: true })
    if (!context) return undefined
    const strip = Math.max(1, Math.round(image.naturalHeight * .12))
    context.drawImage(image, 0, image.naturalHeight - strip, image.naturalWidth, strip, 0, 0, 24, 8)
    return photoTone(context.getImageData(0, 0, 24, 8).data)
  } catch { return undefined }
}
