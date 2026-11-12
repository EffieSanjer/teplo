import { describe, expect, it } from 'vitest'
import { certificateColor, certificateLogoBackground } from './certificateColor'

describe('certificateColor', () => {
  it('ignores white margins and transparent pixels', () => {
    expect(certificateColor([255, 255, 255, 255, 0, 0, 0, 0, 255, 120, 56, 255]))
      .toEqual({ background: 'rgb(255, 120, 56)', ink: '#111111' })
  })
  it('uses white text on a dark brand colour', () => {
    expect(certificateColor([40, 50, 100, 255])?.ink).toBe('#ffffff')
  })
  it('falls back when there are no usable pixels', () => {
    expect(certificateColor([255, 255, 255, 255])).toBeNull()
    expect(certificateColor([])).toBeNull()
  })
  it('blends white-backed logos from white rather than their brand colour', () => {
    const pixels = Array.from({ length: 9 }, (_, i) => i === 4 ? [120, 40, 20, 255] : [255, 255, 255, 255]).flat()
    expect(certificateLogoBackground(pixels, 3, 3)).toBe('rgb(255, 255, 255)')
  })
  it('does not add a patch behind a transparent logo', () => {
    expect(certificateLogoBackground(new Uint8Array(36), 3, 3)).toBe('transparent')
  })
})
