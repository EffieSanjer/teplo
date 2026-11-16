import { describe, expect, it } from 'vitest'
import { photoTone } from './photoTone'

describe('photo edge tone', () => {
  it('averages opaque colours without excluding white', () => {
    expect(photoTone([255, 255, 255, 255, 25, 45, 65, 255])).toBe('rgb(140, 150, 160)')
  })
  it('ignores transparent padding and handles empty samples', () => {
    expect(photoTone([0, 0, 0, 0, 200, 180, 160, 255])).toBe('rgb(200, 180, 160)')
    expect(photoTone([255, 255, 255, 0])).toBeUndefined()
    expect(photoTone([])).toBeUndefined()
  })
})
