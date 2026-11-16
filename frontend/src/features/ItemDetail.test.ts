import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import ItemDetail from './ItemDetail.vue'
import type { Item } from '../shared/api'
import { itemPalette } from '../shared/itemPalette'

vi.mock('../shared/photoTone', () => ({ samplePhotoTone: () => 'rgb(200, 180, 160)' }))

const item: Item = {
  id: 'gift', recipient_id: 'friend', author_id: 'me', author_name: 'Автор', list_type: 'wishlist',
  item_type: 'gift', title: 'Подарок', description: null, url: null, image_id: null, image_is_icon: false,
  price: null, currency: null, price_mode: 'approximate', archived_at: null,
  created_at: '2026-01-01', updated_at: '2026-01-01', can_manage: false,
}
function open(overrides: Partial<Item> = {}) {
  return mount(ItemDetail, { props: { item: { ...item, ...overrides }, ownProfile: true, busy: false }, global: {
    stubs: { Modal: { props: ['title', 'variant', 'photoRatio', 'hasPhoto', 'surfaceStyle'], template: '<section :data-variant="variant" :data-ratio="photoRatio" :data-photo="hasPhoto"><h2>{{ title }}</h2><slot name="header-actions" /><slot /></section>' } },
  } })
}

describe('item detail', () => {
  it('omits invented descriptions, empty prices, type labels and placeholder art', () => {
    const wrapper = open()
    expect(wrapper.find('.detail-price').exists()).toBe(false)
    expect(wrapper.find('.detail-description').exists()).toBe(false)
    expect(wrapper.find('.detail-art').exists()).toBe(false)
    expect(wrapper.find('.eyebrow').exists()).toBe(false)
    expect(wrapper.find('.detail-actions').exists()).toBe(false)
    expect(wrapper.get('.detail-mobile-title').text()).toBe('Подарок')
    expect(wrapper.find('.detail-copy').exists()).toBe(false)
  })
  it('shows only supplied content and available actions', async () => {
    const wrapper = open({ description: 'Моя заметка', price: '0', currency: 'RUB', can_manage: true })
    expect(wrapper.get('.detail-description').text()).toBe('Моя заметка')
    expect(wrapper.get('.detail-price').text()).toContain('0')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('edit')).toBeTruthy()
  })
  it.each([[600, 1200], [1600, 800]])('fits the dialog to a %s × %s photo', async (width, height) => {
    const wrapper = open({ image_id: 'photo' })
    const image = wrapper.get('img')
    Object.defineProperties(image.element, { naturalWidth: { value: width }, naturalHeight: { value: height } })
    await image.trigger('load')
    expect(wrapper.attributes('data-variant')).toBe('item-detail')
    expect(wrapper.attributes('data-ratio')).toBe(String(width / height))
    expect(wrapper.attributes('data-photo')).toBe('true')
    await wrapper.setProps({ item: { ...item, image_id: 'new' } })
    expect(wrapper.attributes('data-ratio')).toBeUndefined()
  })
  it('hides whitespace-only text and certificate pricing', () => {
    const wrapper = open({ item_type: 'certificate', description: '  ', price: '500', currency: 'RUB' })
    expect(wrapper.find('.detail-price').exists()).toBe(false)
    expect(wrapper.find('.detail-description').exists()).toBe(false)
  })
  it('keeps a supplied price beside the title even without notes or actions', () => {
    const wrapper = open({ price: '680', currency: 'RUB' })
    expect(wrapper.get('.detail-heading .detail-price').text()).toContain('680')
    expect(wrapper.get('.detail-heading .detail-mobile-title').text()).toBe('Подарок')
    expect(wrapper.find('.detail-copy').exists()).toBe(false)
  })
  it('keeps text and actions if a photo fails to load', async () => {
    const wrapper = open({ image_id: 'broken', can_manage: true })
    expect(wrapper.get('.detail-body').classes()).toContain('glass-panel')
    await wrapper.get('img').trigger('error')
    expect(wrapper.get('.detail-body').classes()).not.toContain('glass-panel')
    expect(wrapper.find('.detail-art').exists()).toBe(false)
    expect(wrapper.get('.detail-mobile-title').text()).toBe('Подарок')
    expect(wrapper.find('.detail-menu button').exists()).toBe(true)
    expect(wrapper.get('.detail-menu button').text()).toBe('Редактировать')
  })
  it('uses the same surface palette as the gallery card', () => {
    const wrapper = open()
    expect(wrapper.get('.item-info').attributes('style')).toContain(`--item-bg: ${itemPalette(item.id)['--item-bg']}`)
  })
})
