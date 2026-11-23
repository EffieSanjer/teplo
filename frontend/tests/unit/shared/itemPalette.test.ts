import { describe, expect, it } from 'vitest'
import { itemPalette } from '../../../src/shared/itemPalette'

describe('item palette', () => {
  it('uses theme tokens and keeps surfaces stable by item id', () => {
    for (const id of ['book', 'trip', 'ceramics', 'coffee', 'shop', 'lamp']) {
      const palette = itemPalette(id)
      const tone = palette['--item-bg']
      expect(tone).toMatch(/^var\(--collection-tone-[0-3]\)$/)
      expect(palette['--item-accent']).toBe('var(--warm)')
      expect(palette['--certificate-bg']).toBe(tone)
      expect(palette['--photo-bg']).toBe(tone)
      expect(palette['--glass-ink']).toBe(palette['--item-ink'])
      expect(
        Object.values(palette).every(
          (value) => value === 'transparent' || value.startsWith('var('),
        ),
      ).toBe(true)
      expect(palette).toEqual(itemPalette(id))
    }
  })
})
