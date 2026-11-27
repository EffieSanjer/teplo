<script setup lang="ts">
import { theme } from '../shared/theme';

withDefaults(
  defineProps<{
    class?: string;
    fetchpriority?: 'high' | 'low' | 'auto';
  }>(),
  { fetchpriority: 'high' },
);
</script>

<template>
  <div class="theme-cover" :class="$props.class" aria-hidden="true">
    <img
      class="theme-cover-layer"
      :class="{ 'is-visible': theme !== 'dark' }"
      src="/wishlist-cover-mobile-light.jpg"
      srcset="/wishlist-cover-mobile-light.jpg 768w, /wishlist-cover-light.jpg 1280w"
      sizes="100vw"
      alt=""
      width="1280"
      height="720"
      decoding="async"
      :fetchpriority="fetchpriority"
    />
    <img
      class="theme-cover-layer"
      :class="{ 'is-visible': theme === 'dark' }"
      src="/wishlist-cover-mobile-dark.jpg"
      srcset="/wishlist-cover-mobile-dark.jpg 768w, /wishlist-cover-dark.jpg 1280w"
      sizes="100vw"
      alt=""
      width="1280"
      height="720"
      decoding="async"
      fetchpriority="low"
    />
  </div>
</template>

<style scoped>
.theme-cover {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.theme-cover-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 35%;
  opacity: 0;
  transition: opacity 0.22s ease;
}
.theme-cover-layer.is-visible {
  opacity: 1;
}
</style>
