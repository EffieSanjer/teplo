import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import WishImage from './WishImage.vue'

describe('WishImage', () => {
  it('keeps an imported logo compact even when the source is large', async () => {
    const wrapper = mount(WishImage, { props: { src: '/logo', isIcon: true }, attrs: { alt: 'Логотип' } })
    expect(wrapper.classes()).toContain('site-icon')
    expect(wrapper.attributes('style')).toContain('width: 64px')
    Object.defineProperties(wrapper.element, { naturalWidth: { value: 1024 }, naturalHeight: { value: 512 } })
    await wrapper.trigger('load')
    expect(wrapper.attributes('style')).toContain('width: 64px')
    expect(wrapper.attributes('alt')).toBe('Логотип')
    expect(wrapper.emitted('load')).toHaveLength(1)
  })
  it('does not enlarge old tiny images beyond their native size', async () => {
    const wrapper = mount(WishImage, { props: { src: '/old-icon' } })
    Object.defineProperties(wrapper.element, { naturalWidth: { value: 32 }, naturalHeight: { value: 32 } })
    await wrapper.trigger('load')
    expect(wrapper.classes()).toContain('site-icon')
    expect(wrapper.attributes('style')).toContain('width: 32px')
    await wrapper.setProps({ src: '/photo' })
    expect(wrapper.classes()).not.toContain('site-icon')
    expect(wrapper.attributes('style') || '').not.toContain('32px')
  })
  it('leaves ordinary photos full-sized', async () => {
    const wrapper = mount(WishImage, { props: { src: '/photo' } })
    Object.defineProperties(wrapper.element, { naturalWidth: { value: 800 }, naturalHeight: { value: 1200 } })
    await wrapper.trigger('load')
    expect(wrapper.classes()).not.toContain('site-icon')
    expect(wrapper.attributes('style')).toBeUndefined()
  })
})
