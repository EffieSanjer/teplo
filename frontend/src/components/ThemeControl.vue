<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next';
import { theme, toggleTheme } from '../shared/theme';
import { AppButton } from './ui';

const label = () => (theme.value === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему');
</script>

<template>
  <AppButton
    variant="icon"
    class="theme-control"
    :label="label()"
    :title="label()"
    @click.stop="toggleTheme"
  >
    <Sun v-if="theme === 'dark'" :size="19" aria-hidden="true" />
    <Moon v-else :size="19" aria-hidden="true" />
  </AppButton>
</template>
