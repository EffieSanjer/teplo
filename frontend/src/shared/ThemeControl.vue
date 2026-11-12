<script setup lang="ts">
import { Monitor, Moon, Sun } from 'lucide-vue-next'
import { setTheme, themePreference, type ThemePreference } from './theme'
</script>

<template>
  <label class="theme-control" :title="`Тема: ${themePreference === 'system' ? 'как на устройстве' : themePreference === 'dark' ? 'тёмная' : 'светлая'}`">
    <Moon v-if="themePreference === 'dark'" :size="17" aria-hidden="true" />
    <Sun v-else-if="themePreference === 'light'" :size="17" aria-hidden="true" />
    <Monitor v-else :size="17" aria-hidden="true" />
    <select :value="themePreference" aria-label="Тема оформления" @change="setTheme(($event.target as HTMLSelectElement).value as ThemePreference)">
      <option value="system">Как на устройстве</option>
      <option value="light">Светлая</option>
      <option value="dark">Тёмная</option>
    </select>
  </label>
</template>
