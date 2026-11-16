import { describe, expect, it } from 'vitest'
import { itemPalette } from './itemPalette'

describe('item palette', () => {
  it('uses only the reference palette and keeps surfaces stable by item id', () => {
    for (const id of ['book', 'trip', 'ceramics', 'coffee', 'shop', 'lamp']) {
      const palette = itemPalette(id)
      expect(palette['--item-bg']).toBe(palette['--item-accent'])
      expect(['#4b5839', '#c2442a']).toContain(palette['--item-accent'])
      expect(palette).toEqual(itemPalette(id))
      expect(palette['--certificate-bg']).toBe(palette['--item-bg'])
      expect(palette['--glass-ink']).toBe(palette['--item-ink'])
      expect(Object.values(palette)).not.toContain('#fffe94')
    }
  })
})
