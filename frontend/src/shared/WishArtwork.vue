<script setup lang="ts">
import { Gift, Lightbulb, Sparkles, Store } from 'lucide-vue-next'
import { computed } from 'vue'

const props = defineProps<{ seed: string; type: 'idea' | 'gift' | 'certificate' }>()
const variant = computed(() => {
  // Stable per wish: adding or archiving a neighbour must not change its cover.
  const hash = Array.from(props.seed).reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, 0)
  return ['orbit', 'ribbon', 'tiles', 'bloom'][hash % 4]
})
</script>

<template>
  <div class="wish-artwork" :class="`artwork-${variant}`" aria-hidden="true">
    <span class="artwork-shape shape-one" />
    <span class="artwork-shape shape-two" />
    <span class="artwork-shape shape-three" />
    <div class="art-placeholder">
      <Store v-if="type === 'certificate'" :size="32" :stroke-width="1.5" />
      <Lightbulb v-else-if="type === 'idea'" :size="32" :stroke-width="1.5" />
      <Gift v-else :size="32" :stroke-width="1.5" />
    </div>
    <Sparkles class="artwork-sparkle" :size="18" :stroke-width="1.4" />
  </div>
</template>

<style scoped src="../styles/scoped/wish-artwork.css"></style>
