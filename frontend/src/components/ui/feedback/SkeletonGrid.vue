<script setup lang="ts">
withDefaults(
  defineProps<{
    count?: number;
    variant?: 'cards' | 'friends';
    label?: string;
  }>(),
  { count: 4, variant: 'cards' },
);
</script>

<template>
  <div class="loading-grid" :role="label ? 'status' : undefined" :aria-label="label">
    <div
      v-for="index in count"
      :key="index"
      class="skeleton"
      :class="{ 'friend-skeleton': variant === 'friends' }"
    />
  </div>
</template>
