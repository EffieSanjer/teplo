import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ItemDetail from '../../../src/components/ItemDetail.vue'
import type { Item } from '../../../src/shared/api'

const item: Item = {
  most_wanted: false,
  id: 'gift',
  recipient_id: 'friend',
  author_id: 'me',
  author_name: 'Автор',
  list_type: 'wishlist',
  item_type: 'gift',
  title: 'Подарок',
  description: null,
  url: null,
  image_id: null,
  image_is_icon: false,
  price: null,
  currency: null,
  price_mode: 'approximate',
  surprise_visibility: 'friends',
  can_reserve: false,
  archived_at: null,
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
  can_manage: false,
}

const wrappers: ReturnType<typeof mount>[] = []
const modal = { props: ['title'], template: '<section><h2>{{ title }}</h2><slot /></section>' }

beforeEach(() => {
  vi.stubGlobal('matchMedia', () => ({ matches: false }))
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      disconnect() {}
    },
  )
  HTMLDialogElement.prototype.showModal = vi.fn()
})
afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.unstubAllGlobals()
})

function open(overrides: Partial<Item> = {}) {
  const wrapper = mount(ItemDetail, {
    props: { item: { ...item, ...overrides }, ownProfile: true, busy: false },
    global: { stubs: { Modal: modal } },
  })
  wrappers.push(wrapper)
  return wrapper
}

function viewer() {
  const dialog = document.body.querySelector('dialog')
  if (!dialog) throw new Error('the detail dialog was not teleported to body')
  return dialog
}

function paragraphs() {
  return Array.from(viewer().querySelectorAll('p'))
}

function button(label: string) {
  const found = Array.from(viewer().querySelectorAll('button')).find(
    (entry) =>
      entry.getAttribute('aria-label') === label || entry.textContent?.includes(label),
  )
  if (!found) throw new Error(`no button labelled ${label}`)
  return found
}

async function openManageMenu() {
  button('Управление желанием').click()
  await flushPromises()
}

describe('item detail', () => {
  it('shows the title and note hero without inventing a price or description', () => {
    open()
    const dialog = viewer()
    expect(dialog.querySelector('#wish-viewer-title')?.textContent?.trim()).toBe('Подарок')
    expect(dialog.querySelector('.wish-note-hero')).not.toBeNull()
    expect(dialog.querySelector('.wish-note-hero-mark')).toBeNull()
    expect(dialog.textContent).not.toContain('Бесценно')
    expect(dialog.textContent).not.toContain('₽')
    expect(dialog.textContent).not.toContain('Однажды')
    expect(dialog.querySelector('img')).toBeNull()
  })
  it('shows only supplied content and available actions', async () => {
    const wrapper = open({
      description: 'Моя заметка',
      price: '0',
      currency: 'RUB',
      can_manage: true,
    })
    expect(paragraphs().some((p) => p.textContent?.trim() === 'Моя заметка')).toBe(true)
    expect(
      paragraphs().some((p) => p.textContent?.includes('0') && p.textContent.includes('₽')),
    ).toBe(true)
    await openManageMenu()
    button('Редактировать').click()
    await flushPromises()
    expect(wrapper.emitted('edit')).toHaveLength(1)
  })
  it.each([
    [600, 1200],
    [1600, 800],
  ])('fits the dialog to a %s × %s photo', async (width, height) => {
    open({ image_id: 'photo' })
    const image = viewer().querySelector('img') as HTMLImageElement
    Object.defineProperties(image, {
      naturalWidth: { value: width },
      naturalHeight: { value: height },
    })
    image.dispatchEvent(new Event('load'))
    await flushPromises()
    expect(image.parentElement?.style.height).toBe(`${window.innerWidth / (width / height)}px`)
  })
  it('hides whitespace-only text and certificate pricing', () => {
    const wrapper = open({
      item_type: 'certificate',
      description: '  ',
      price: '500',
      currency: 'RUB',
    })
    const section = wrapper.get('.certificate-mini')
    expect(section.get('h2').text()).toBe('Подарок')
    expect(section.findAll('p')).toHaveLength(0)
    expect(section.text()).not.toContain('500')
    expect(section.text()).not.toContain('Бесценно')
    expect(document.body.querySelector('dialog')).toBeNull()
  })
  it('keeps a supplied price beside the title even without notes', () => {
    open({ price: '680', currency: 'RUB' })
    expect(viewer().querySelector('#wish-viewer-title')?.textContent?.trim()).toBe('Подарок')
    expect(paragraphs().some((p) => p.textContent?.includes('680'))).toBe(true)
    expect(paragraphs().some((p) => p.textContent?.includes('О природе'))).toBe(false)
  })
  it('keeps text and actions if a photo fails to load', async () => {
    const wrapper = open({ image_id: 'broken', can_manage: true })
    expect(viewer().querySelector('#wish-viewer-title')?.textContent?.trim()).toBe('Подарок')
    ;(viewer().querySelector('img') as HTMLImageElement).dispatchEvent(new Event('error'))
    await flushPromises()
    expect(viewer().querySelector('img')).toBeNull()
    expect(viewer().querySelector('.wish-note-hero')).not.toBeNull()
    expect(viewer().textContent).not.toContain('Однажды')
    await openManageMenu()
    button('Редактировать').click()
    await flushPromises()
    expect(wrapper.emitted('edit')).toHaveLength(1)
  })
  it('emits close from the dialog close button', async () => {
    const wrapper = open()
    button('Назад').click()
    await flushPromises()
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
