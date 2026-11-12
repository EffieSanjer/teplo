import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ItemCard from './ItemCard.vue'
import { itemTitle, type Item } from '../shared/api'

const item: Item = {
  id: 'test', recipient_id: 'recipient', author_id: 'author', author_name: 'Автор', list_type: 'wishlist',
  item_type: 'gift', title: 'Книга', description: 'О природе', url: 'https://example.com', image_id: null, image_is_icon: false,
  price: '123.45', currency: 'RUB', price_mode: 'approximate', archived_at: null, created_at: '2026-01-01', updated_at: '2026-01-01', can_manage: true,
}

describe('ItemCard', () => {
  it('opens active cards', async () => {
    const wrapper = mount(ItemCard, { props: { item, index: 0 } })
    await wrapper.get('.card-open').trigger('click')
    expect(wrapper.emitted('open')?.[0]).toEqual([item])
  })
  it('keeps gallery cards concise without repeating the personal description', () => {
    const wrapper = mount(ItemCard, { props: { item, index: 0 } })
    expect(wrapper.find('.card-body p').exists()).toBe(false)
    expect(wrapper.get('h3').text()).toBe('Книга')
    expect(wrapper.text()).not.toContain('О природе')
  })
  it('does not make an archived card or its link interactive', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, archived_at: '2026-02-01' }, index: 0 } })
    expect(wrapper.find('.card-open').exists()).toBe(false)
    expect(wrapper.find('a').exists()).toBe(false)
    expect(wrapper.text()).toContain('В архиве')
    expect(wrapper.find('summary').exists()).toBe(true)
    expect(wrapper.text()).toContain('Восстановить')
    expect(wrapper.text()).not.toContain('Редактировать')
  })
  it('hides management from non-authors', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, can_manage: false }, index: 1 } })
    expect(wrapper.find('details').exists()).toBe(false)
  })
  it('uses a store domain for untitled gifts', () => {
    expect(itemTitle({ title: null, url: 'https://www.example.com/product' })).toBe('example.com')
  })
  it('shows certificate shops without prices, including older priced records', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, item_type: 'certificate', price_mode: 'from' }, index: 0 } })
    expect(wrapper.text()).toContain('Сертификат')
    expect(wrapper.find('.card-bottom strong').exists()).toBe(false)
    expect(wrapper.text()).not.toMatch(/123|примерно|номинал|и выше/)
    expect(wrapper.classes()).toContain('certificate-card')
    expect(wrapper.get('.certificate-label').text()).toBe('Подарочная карта')
  })
  it('shows a minimum price without an approximate label', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, price_mode: 'from' }, index: 0 } })
    expect(wrapper.get('.card-bottom strong').text()).toMatch(/^От /)
    expect(wrapper.text()).not.toContain('примерно')
  })
  it('keeps actual photos on a white background instead of placeholder artwork', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, image_id: 'photo' }, index: 0 } })
    expect(wrapper.get('.card-art').classes()).toContain('art-photo')
    expect(wrapper.find('.art-placeholder').exists()).toBe(false)
  })
  it.each([
    [1200, 800, 'landscape'], [800, 1200, 'portrait'], [800, 800, 'square'],
  ])('matches the photo frame to %s × %s', async (width, height, layout) => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, image_id: 'photo' }, index: 0 } })
    const image = wrapper.get('img')
    Object.defineProperties(image.element, { naturalWidth: { value: width }, naturalHeight: { value: height } })
    await image.trigger('load')
    expect(image.classes()).toContain(`photo-${layout}`)
    expect(wrapper.get('.card-art').attributes('style')).toContain(`aspect-ratio: ${width} / ${height}`)
    await wrapper.setProps({ item: { ...item, image_id: 'replacement' } })
    expect(wrapper.get('img').classes()).toContain('photo-square')
    expect(wrapper.get('.card-art').attributes('style')).toContain('aspect-ratio: 1 / 1')
  })
  it('uses the same orientation handling for archive photos', async () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, image_id: 'photo', archived_at: '2026-02-01' }, index: 0 } })
    const image = wrapper.get('img')
    Object.defineProperties(image.element, { naturalWidth: { value: 1200 }, naturalHeight: { value: 800 } })
    await image.trigger('load')
    expect(image.classes()).toContain('photo-landscape')
    expect(wrapper.get('.card-art').attributes('style')).toContain('aspect-ratio: 1200 / 800')
  })
  it('keeps certificates in gift-card format regardless of photo proportions', async () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, item_type: 'certificate', image_id: 'photo' }, index: 0 } })
    const image = wrapper.get('img')
    Object.defineProperties(image.element, { naturalWidth: { value: 800 }, naturalHeight: { value: 1200 } })
    await image.trigger('load')
    expect(wrapper.get('.card-art').attributes('style')).toBeUndefined()
  })
  it.each([null, '2026-02-01'])('keeps imported logos small in active and archived cards (%s)', async archived_at => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, image_id: 'logo', image_is_icon: true, archived_at }, index: 0 } })
    const image = wrapper.get('img')
    Object.defineProperties(image.element, { naturalWidth: { value: 800 }, naturalHeight: { value: 400 } })
    await image.trigger('load')
    expect(image.classes()).toContain('site-icon')
    expect(image.attributes('style')).toContain('width: 64px')
    expect(wrapper.get('.card-art').attributes('style')).toContain('aspect-ratio: 1 / 1')
  })
})
