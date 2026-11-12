import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ItemCard from './ItemCard.vue'
import { itemTitle, type Item } from '../shared/api'

const item: Item = {
  id: 'test', recipient_id: 'recipient', author_id: 'author', author_name: 'Автор', list_type: 'wishlist',
  item_type: 'gift', title: 'Книга', description: 'О природе', url: 'https://example.com', image_id: null,
  price: '123.45', currency: 'RUB', price_mode: 'approximate', archived_at: null, created_at: '2026-01-01', updated_at: '2026-01-01', can_manage: true,
}

describe('ItemCard', () => {
  it('opens active cards', async () => {
    const wrapper = mount(ItemCard, { props: { item, index: 0 } })
    await wrapper.get('.card-open').trigger('click')
    expect(wrapper.emitted('open')?.[0]).toEqual([item])
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
  it('shows certificate shops and minimum prices', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, item_type: 'certificate', price_mode: 'from' }, index: 0 } })
    expect(wrapper.text()).toContain('Сертификат')
    expect(wrapper.get('.card-bottom strong').text()).toMatch(/^От /)
    expect(wrapper.text()).toContain('и выше')
  })
  it('keeps actual photos on a white background instead of placeholder artwork', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, image_id: 'photo' }, index: 0 } })
    expect(wrapper.get('.card-art').classes()).toContain('art-photo')
    expect(wrapper.find('.art-placeholder').exists()).toBe(false)
  })
})
