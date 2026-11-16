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
  it('does not show empty prices, author fields or a blank footer', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, price: null, currency: null }, index: 0 } })
    expect(wrapper.find('.card-bottom').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Бесценно')
  })
  it('omits an empty title instead of inventing visible text', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, title: ' ', url: null, price: null, currency: null }, index: 0 } })
    expect(wrapper.find('h3').exists()).toBe(false)
    expect(wrapper.find('.card-body').exists()).toBe(false)
  })
  it('shows a zero price when supplied', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, price: '0' }, index: 0 } })
    expect(wrapper.get('.card-bottom strong').text()).toContain('0')
  })
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
    expect(wrapper.get('.certificate-face').text()).toBe('Книга')
    expect(wrapper.find('.card-bottom strong').exists()).toBe(false)
    expect(wrapper.text()).not.toMatch(/123|примерно|номинал|и выше/)
    expect(wrapper.classes()).toContain('certificate-card')
    expect(wrapper.find('.certificate-label').exists()).toBe(false)
    expect(wrapper.find('.card-art').exists()).toBe(false)
    expect(wrapper.find('.art-arrow').exists()).toBe(false)
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
    expect(wrapper.find('.wish-artwork').exists()).toBe(false)
  })
  it('keeps the designed cover stable when neighbouring cards change', async () => {
    const wrapper = mount(ItemCard, { props: { item, index: 0 } })
    const cover = wrapper.get('.wish-artwork').classes()
    await wrapper.setProps({ index: 3 })
    expect(wrapper.get('.wish-artwork').classes()).toEqual(cover)
    expect(wrapper.classes()).toContain('without-photo')
    await wrapper.setProps({ item: { ...item, archived_at: '2026-02-01' } })
    expect(wrapper.get('.wish-artwork').classes()).toEqual(cover)
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
  it('keeps a compact logo above the title on a certificate', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, item_type: 'certificate', image_id: 'photo' }, index: 0 } })
    expect(wrapper.get('.certificate-logo img').attributes('src')).toContain('photo')
    expect(wrapper.get('.certificate-logo img').classes()).toContain('site-icon')
    expect(wrapper.get('.certificate-face h3').text()).toBe('Книга')
  })
  it('keeps the title when a certificate logo cannot load', async () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, item_type: 'certificate', image_id: 'missing' }, index: 0 } })
    await wrapper.get('.certificate-logo img').trigger('error')
    expect(wrapper.find('.certificate-logo').exists()).toBe(false)
    expect(wrapper.get('.certificate-face h3').text()).toBe('Книга')
  })
  it('keeps the certificate composition stable when its neighbours change', async () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, item_type: 'certificate' }, index: 0 } })
    const pattern = wrapper.get('.certificate-face').classes().find(name => name.startsWith('certificate-pattern-'))
    expect(pattern).toBeTruthy()
    await wrapper.setProps({ index: 7 })
    expect(wrapper.get('.certificate-face').classes()).toContain(pattern)
  })
  it('shows the part after a dash as a certificate subtitle without changing the item', () => {
    const certificate = { ...item, item_type: 'certificate' as const, title: 'Арт-студия - Керамика для двоих' }
    const wrapper = mount(ItemCard, { props: { item: certificate, index: 0 } })
    expect(wrapper.get('.certificate-face h3').text()).toBe('Арт-студия')
    expect(wrapper.get('.certificate-subtitle').text()).toBe('Керамика для двоих')
    expect(wrapper.get('.card-open').attributes('aria-label')).toBe('Открыть: Арт-студия - Керамика для двоих')
    expect(certificate.title).toBe('Арт-студия - Керамика для двоих')
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
