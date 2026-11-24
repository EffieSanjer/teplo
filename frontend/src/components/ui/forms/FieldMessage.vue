<script setup lang="ts">
withDefaults(
  defineProps<{
    kind?: 'hint' | 'error';
    id?: string;
    role?: 'alert' | 'status';
  }>(),
  { kind: 'hint' },
);
</script>

<template>
  <p
    :id="id"
    class="field-message"
    :class="kind === 'error' ? 'field-message--error' : 'field-message--hint'"
    :role="role"
  >
    <slot />
  </p>
</template>
