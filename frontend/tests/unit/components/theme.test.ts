import { afterEach, describe, expect, it, vi } from 'vitest'
import { initTheme, setTheme, themePreference, toggleTheme } from '../../../src/shared/theme'
import { mount } from '@vue/test-utils'
import ThemeControl from '../../../src/components/ThemeControl.vue'

let cleanup = () => {}
function device(dark = false) {
  const media = { matches: dark, addEventListener: vi.fn(), removeEventListener: vi.fn() }
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => media),
  )
  return media
}
afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  document.documentElement.removeAttribute('data-theme')
})

describe('theme preference', () => {
  it.each([true, false])(
    'toggles the resolved device theme with one button and remembers the result (%s)',
    async (dark) => {
      const media = device(dark)
      cleanup = initTheme()
      const wrapper = mount(ThemeControl)
      expect(wrapper.find('select').exists()).toBe(false)
      expect(wrapper.get('button').attributes('aria-label')).toBe(
        dark ? 'Включить светлую тему' : 'Включить тёмную тему',
      )
      await wrapper.get('button').trigger('click')
      expect(document.documentElement.dataset.theme).toBe(dark ? 'light' : 'dark')
      expect(localStorage.getItem('teplo.theme')).toBe(dark ? 'light' : 'dark')
      media.matches = dark
      media.addEventListener.mock.calls[0]![1]()
      expect(document.documentElement.dataset.theme).toBe(dark ? 'light' : 'dark')
      toggleTheme()
      expect(localStorage.getItem('teplo.theme')).toBe(dark ? 'dark' : 'light')
      wrapper.unmount()
    },
  )
  it('follows device changes in automatic mode', () => {
    const media = device(true)
    cleanup = initTheme()
    expect(themePreference.value).toBe('system')
    expect(document.documentElement.dataset.theme).toBe('dark')
    media.matches = false
    media.addEventListener.mock.calls[0]![1]()
    expect(document.documentElement.dataset.theme).toBe('light')
  })
  it('persists a manual choice and ignores system changes until automatic mode is selected', () => {
    const media = device(false)
    cleanup = initTheme()
    setTheme('dark')
    expect(localStorage.getItem('teplo.theme')).toBe('dark')
    media.addEventListener.mock.calls[0]![1]()
    expect(document.documentElement.dataset.theme).toBe('dark')
    setTheme('system')
    expect(document.documentElement.dataset.theme).toBe('light')
  })
  it('restores a saved theme', () => {
    device(true)
    localStorage.setItem('teplo.theme', 'light')
    cleanup = initTheme()
    expect(themePreference.value).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
  })
  it('falls back to the device for unknown stored values and synchronizes tabs', () => {
    device(true)
    localStorage.setItem('teplo.theme', 'unknown')
    cleanup = initTheme()
    expect(document.documentElement.dataset.theme).toBe('dark')
    window.dispatchEvent(new StorageEvent('storage', { key: 'teplo.theme', newValue: 'light' }))
    expect(document.documentElement.dataset.theme).toBe('light')
  })
  it('can switch themes even when storage is blocked', () => {
    device(false)
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    cleanup = initTheme()
    expect(() => setTheme('dark')).not.toThrow()
    expect(document.documentElement.dataset.theme).toBe('dark')
  })
})
