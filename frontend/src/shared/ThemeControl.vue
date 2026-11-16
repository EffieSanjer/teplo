<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { theme, toggleTheme } from './theme'
</script>

<template>
  <button type="button" class="theme-control" :title="theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'" :aria-label="theme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'" @click.stop="toggleTheme">
    <Sun v-if="theme === 'dark'" :size="19" aria-hidden="true" />
    <Moon v-else :size="19" aria-hidden="true" />
  </button>
</template>
