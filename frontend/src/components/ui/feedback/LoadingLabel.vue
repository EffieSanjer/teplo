<script setup lang="ts">
import Spinner from './Spinner.vue';

withDefaults(
  defineProps<{
    label?: string;
    size?: number;
    role?: 'alert' | 'status';
  }>(),
  { label: 'Загрузка…', size: 16 },
);
</script>

<template>
  <p class="loading-label" :role="role">
    <Spinner :size="size" /><slot>{{ label }}</slot>
  </p>
</template>
