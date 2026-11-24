<script setup lang="ts">
import type { Component } from 'vue';

withDefaults(
  defineProps<{
    title: string;
    description?: string;
    icon?: Component;
    iconSize?: number;
    iconWidth?: number;
    alert?: boolean;
  }>(),
  { iconSize: 36 },
);
</script>

<template>
  <div class="empty-state">
    <slot name="icon">
      <component
        :is="icon"
        v-if="icon"
        :size="iconSize"
        :stroke-width="iconWidth"
        aria-hidden="true"
      />
    </slot>
    <h2>{{ title }}</h2>
    <p v-if="description || $slots.description" :role="alert ? 'alert' : undefined">
      <slot name="description">{{ description }}</slot>
    </p>
    <slot />
  </div>
</template>
