<script setup lang="ts">
import { computed, ref, watch } from 'vue';

const props = withDefaults(
  defineProps<{
    name: string;
    userId: string;
    count?: number;
    lazy?: boolean;
  }>(),
  { count: 2, lazy: false },
);

const failed = ref(false);
const initials = computed(() =>
  props.name
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, props.count)
    .join(''),
);
watch(
  () => props.userId,
  () => {
    failed.value = false;
  },
);
</script>

<template>
  <div class="avatar">
    <img
      v-if="!failed"
      :src="`/api/v1/users/${encodeURIComponent(userId)}/avatar`"
      alt=""
      :loading="lazy ? 'lazy' : undefined"
      class="block size-full object-cover"
      @error="failed = true"
    />
    <span v-else>{{ initials }}</span>
  </div>
</template>

<style scoped src="../../../styles/scoped/avatar.css"></style>
