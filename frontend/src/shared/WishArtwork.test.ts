import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import WishArtwork from './WishArtwork.vue'
import { Lightbulb, Store } from 'lucide-vue-next'

describe('WishArtwork', () => {
  it('creates decorative covers without fetching an image', () => {
    const wrapper = mount(WishArtwork, { props: { seed: 'wish', type: 'idea' } })
    expect(wrapper.attributes('aria-hidden')).toBe('true')
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.findAll('.artwork-shape')).toHaveLength(3)
    expect(wrapper.findComponent(Lightbulb).exists()).toBe(true)
  })
  it('offers four stable compositions', () => {
    const variants = ['a', 'b', 'c', 'd'].map(seed => mount(WishArtwork, {
      props: { seed, type: 'gift' },
    }).classes().find(name => name.startsWith('artwork-')))
    expect(new Set(variants).size).toBe(4)
  })
  it('uses a store symbol for a certificate', () => {
    const wrapper = mount(WishArtwork, { props: { seed: 'store', type: 'certificate' } })
    expect(wrapper.findComponent(Store).exists()).toBe(true)
  })
})
