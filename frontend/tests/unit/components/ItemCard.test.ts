import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ItemCard from '../../../src/components/ItemCard.vue'
import { itemTitle, type Item } from '../../../src/shared/api'

const item: Item = {
  most_wanted: false,
  id: 'test',
  recipient_id: 'recipient',
  author_id: 'author',
  author_name: 'Автор',
  list_type: 'wishlist',
  item_type: 'gift',
  title: 'Книга',
  description: 'О природе',
  url: 'https://example.com',
  image_id: null,
  image_is_icon: false,
  price: '123.45',
  currency: 'RUB',
  price_mode: 'approximate',
  surprise_visibility: 'friends',
  can_reserve: false,
  archived_at: null,
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
  can_manage: true,
}

function noteClass(wrapper: ReturnType<typeof mount>) {
  return wrapper.classes().find((name) => name.startsWith('wish-note-'))
}

function ideaGradient(wrapper: ReturnType<typeof mount>) {
  return wrapper.attributes('style')?.match(/--idea-gradient:[^;]+/)?.[0]
}

describe('ItemCard', () => {
  it('does not invent placeholder prices or an empty footer', () => {
    const wrapper = mount(ItemCard, {
      props: { item: { ...item, price: null, currency: null }, index: 0 },
    })
    expect(wrapper.text()).not.toContain('Бесценно')
    expect(wrapper.find('.card-bottom').exists()).toBe(false)
    expect(wrapper.find('strong').exists()).toBe(false)
  })
  it('omits an empty title instead of inventing visible text', () => {
    const wrapper = mount(ItemCard, {
      props: { item: { ...item, title: ' ', url: null, price: null, currency: null }, index: 0 },
    })
    expect(wrapper.find('h3').exists()).toBe(false)
    expect(wrapper.find('.card-body').exists()).toBe(false)
  })
  it('never renders price details in the gallery card', () => {
    const zero = mount(ItemCard, { props: { item: { ...item, price: '0' }, index: 0 } })
    const minimum = mount(ItemCard, {
      props: { item: { ...item, price: '123.45', price_mode: 'from' }, index: 0 },
    })
    for (const wrapper of [zero, minimum]) {
      expect(wrapper.text()).not.toMatch(/123|От |примерно|Бесценно|₽/)
      expect(wrapper.find('strong').exists()).toBe(false)
    }
  })
  it('opens active cards with the item and its origin', async () => {
    const wrapper = mount(ItemCard, { props: { item, index: 0 } })
    await wrapper.get('.card-open').trigger('click')
    const emitted = wrapper.emitted('open')!
    expect(emitted[0][0]).toEqual(item)
    expect(emitted[0][1]).toEqual(
      expect.objectContaining({
        left: expect.any(Number),
        top: expect.any(Number),
        width: expect.any(Number),
        height: expect.any(Number),
        photoRatio: undefined,
      }),
    )
  })
  it('reports the loaded photo ratio when a card is opened', async () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, image_id: 'photo' }, index: 0 } })
    const image = wrapper.get('img')
    Object.defineProperties(image.element, {
      naturalWidth: { value: 1200 },
      naturalHeight: { value: 800 },
    })
    await image.trigger('load')
    await wrapper.get('.card-open').trigger('click')
    expect(wrapper.emitted('open')![0][1]).toMatchObject({ photoRatio: 1.5 })
  })
  it('shows the note excerpt instead of a repeating card body', () => {
    const wrapper = mount(ItemCard, { props: { item, index: 0 } })
    expect(wrapper.find('.card-body p').exists()).toBe(false)
    expect(wrapper.get('h3').text()).toBe('Книга')
    expect(wrapper.get('.wish-note-excerpt').text()).toBe('О природе')
  })
  it('marks archived cards without inventing management or link controls', () => {
    const wrapper = mount(ItemCard, {
      props: { item: { ...item, archived_at: '2026-02-01' }, index: 0 },
    })
    expect(wrapper.find('a').exists()).toBe(false)
    expect(wrapper.text()).toContain('В архиве')
    expect(wrapper.find('details').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Восстановить')
    expect(wrapper.text()).not.toContain('Редактировать')
    expect(wrapper.find('.card-open').exists()).toBe(true)
  })
  it('does not add management controls based on can_manage', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, can_manage: false }, index: 1 } })
    expect(wrapper.find('details').exists()).toBe(false)
    expect(wrapper.find('summary').exists()).toBe(false)
  })
  it('uses a store domain for untitled gifts', () => {
    expect(itemTitle({ title: null, url: 'https://www.example.com/product' })).toBe('example.com')
  })
  it('shows certificate shops without prices, including older priced records', () => {
    const wrapper = mount(ItemCard, {
      props: { item: { ...item, item_type: 'certificate', price_mode: 'from' }, index: 0 },
    })
    expect(wrapper.get('.certificate-face').text()).toBe('Книга')
    expect(wrapper.find('strong').exists()).toBe(false)
    expect(wrapper.text()).not.toMatch(/123|примерно|номинал|и выше/)
    expect(wrapper.classes()).toContain('certificate-card')
    expect(wrapper.find('.certificate-label').exists()).toBe(false)
    expect(wrapper.find('.card-art').exists()).toBe(false)
    expect(wrapper.find('.art-arrow').exists()).toBe(false)
  })
  it('keeps actual photos on a white background instead of placeholder artwork', () => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, image_id: 'photo' }, index: 0 } })
    expect(wrapper.get('.card-art').classes()).toContain('art-photo')
    expect(wrapper.find('.art-placeholder').exists()).toBe(false)
    expect(wrapper.find('.wish-artwork').exists()).toBe(false)
  })
  it('keeps the designed cover stable when neighbouring cards change', async () => {
    const wrapper = mount(ItemCard, { props: { item, index: 0 } })
    const note = noteClass(wrapper)
    const gradient = ideaGradient(wrapper)
    expect(note).toBeTruthy()
    expect(gradient).toBeTruthy()
    await wrapper.setProps({ index: 3 })
    expect(noteClass(wrapper)).toBe(note)
    expect(ideaGradient(wrapper)).toBe(gradient)
    expect(wrapper.classes()).toContain('without-photo')
    await wrapper.setProps({ item: { ...item, archived_at: '2026-02-01' } })
    expect(noteClass(wrapper)).toBe(note)
    expect(ideaGradient(wrapper)).toBe(gradient)
  })
  it.each([
    [1200, 800, 'landscape'],
    [800, 1200, 'portrait'],
    [800, 800, 'square'],
  ])('matches the photo frame to %s × %s', async (width, height, layout) => {
    const wrapper = mount(ItemCard, { props: { item: { ...item, image_id: 'photo' }, index: 0 } })
    const image = wrapper.get('img')
    Object.defineProperties(image.element, {
      naturalWidth: { value: width },
      naturalHeight: { value: height },
    })
    await image.trigger('load')
    expect(image.classes()).toContain(`photo-${layout}`)
    expect(wrapper.attributes('style')).toContain(`--tile-photo-ratio: ${width / height}`)
    await wrapper.setProps({ item: { ...item, image_id: 'replacement' } })
    expect(wrapper.get('img').classes()).toContain('photo-square')
    expect(wrapper.attributes('style')).toContain('--tile-photo-ratio: 1')
  })
  it('uses the same orientation handling for archive photos', async () => {
    const wrapper = mount(ItemCard, {
      props: { item: { ...item, image_id: 'photo', archived_at: '2026-02-01' }, index: 0 },
    })
    const image = wrapper.get('img')
    Object.defineProperties(image.element, {
      naturalWidth: { value: 1200 },
      naturalHeight: { value: 800 },
    })
    await image.trigger('load')
    expect(image.classes()).toContain('photo-landscape')
    expect(wrapper.attributes('style')).toContain('--tile-photo-ratio: 1.5')
  })
  it('keeps a compact logo above the title on a certificate', () => {
    const wrapper = mount(ItemCard, {
      props: { item: { ...item, item_type: 'certificate', image_id: 'photo' }, index: 0 },
    })
    expect(wrapper.get('.certificate-logo img').attributes('src')).toContain('photo')
    expect(wrapper.get('.certificate-logo img').classes()).toContain('site-icon')
    expect(wrapper.get('.certificate-face h3').text()).toBe('Книга')
  })
  it('keeps the title when a certificate logo cannot load', async () => {
    const wrapper = mount(ItemCard, {
      props: { item: { ...item, item_type: 'certificate', image_id: 'missing' }, index: 0 },
    })
    await wrapper.get('.certificate-logo img').trigger('error')
    expect(wrapper.find('.certificate-logo').exists()).toBe(false)
    expect(wrapper.get('.certificate-face h3').text()).toBe('Книга')
  })
  it('keeps the certificate composition stable when its neighbours change', async () => {
    const wrapper = mount(ItemCard, {
      props: { item: { ...item, item_type: 'certificate' }, index: 0 },
    })
    const note = noteClass(wrapper)
    const gradient = ideaGradient(wrapper)
    expect(note).toBeTruthy()
    expect(gradient).toBeTruthy()
    await wrapper.setProps({ index: 7 })
    expect(noteClass(wrapper)).toBe(note)
    expect(ideaGradient(wrapper)).toBe(gradient)
  })
  it('shows only the certificate name while keeping the full title for the open action', () => {
    const certificate = {
      ...item,
      item_type: 'certificate' as const,
      title: 'Арт-студия - Керамика для двоих',
    }
    const wrapper = mount(ItemCard, { props: { item: certificate, index: 0 } })
    expect(wrapper.get('.certificate-face h3').text()).toBe('Арт-студия')
    expect(wrapper.find('.certificate-subtitle').exists()).toBe(false)
    expect(wrapper.get('.card-open').attributes('aria-label')).toBe(
      'Открыть: Арт-студия - Керамика для двоих',
    )
    expect(certificate.title).toBe('Арт-студия - Керамика для двоих')
  })
  it.each([null, '2026-02-01'])(
    'keeps imported logos small in active and archived cards (%s)',
    async (archived_at) => {
      const wrapper = mount(ItemCard, {
        props: { item: { ...item, image_id: 'logo', image_is_icon: true, archived_at }, index: 0 },
      })
      const image = wrapper.get('img')
      Object.defineProperties(image.element, {
        naturalWidth: { value: 800 },
        naturalHeight: { value: 400 },
      })
      await image.trigger('load')
      expect(image.classes()).toContain('site-icon')
      expect(image.attributes('style')).toContain('width: 64px')
      expect(wrapper.attributes('style')).toContain('--tile-photo-ratio: 1')
    },
  )
})
