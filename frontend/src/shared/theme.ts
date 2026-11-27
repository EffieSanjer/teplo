import { computed, ref } from 'vue'

export type ThemePreference = 'system' | 'light' | 'dark'
const storageKey = 'teplo.theme'
export const themePreference = ref<ThemePreference>('system')
const systemDark = ref(false)
export const theme = computed(() =>
  themePreference.value === 'system'
    ? systemDark.value
      ? 'dark'
      : 'light'
    : themePreference.value,
)

function preference(value: string | null): ThemePreference {
  return value === 'light' || value === 'dark' ? value : 'system'
}

function applyTheme() {
  document.documentElement.dataset.theme = theme.value
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', theme.value === 'dark' ? '#15202b' : '#eef3f8')
}

export function setTheme(value: ThemePreference) {
  themePreference.value = value
  try {
    localStorage.setItem(storageKey, value)
  } catch {
    /* Still usable when browser storage is unavailable. */
  }
  applyTheme()
}

export function toggleTheme() {
  setTheme(theme.value === 'dark' ? 'light' : 'dark')
}

export function initTheme() {
  const media = window.matchMedia('(prefers-color-scheme: dark)')
  systemDark.value = media.matches
  try {
    themePreference.value = preference(localStorage.getItem(storageKey))
  } catch {
    themePreference.value = 'system'
  }
  applyTheme()
  const changed = () => {
    systemDark.value = media.matches
    applyTheme()
  }
  const stored = (event: StorageEvent) => {
    if (event.key !== storageKey && event.key !== null) return
    themePreference.value = preference(event.newValue)
    applyTheme()
  }
  media.addEventListener('change', changed)
  window.addEventListener('storage', stored)
  return () => {
    media.removeEventListener('change', changed)
    window.removeEventListener('storage', stored)
  }
}
