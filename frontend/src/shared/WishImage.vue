<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{ src: string; isIcon?: boolean }>()
const emit = defineEmits<{ load: [event: Event] }>()
const width = ref(0), height = ref(0)
watch(() => props.src, () => { width.value = 0; height.value = 0 })
// Older imports have no icon marker. Never enlarge a tiny raster image either.
const compact = computed(() => props.isIcon || (width.value > 0 && width.value <= 96 && height.value <= 96))
const iconStyle = computed(() => compact.value ? {
  width: `${Math.min(width.value || 64, 64)}px`, height: `${Math.min(height.value || 64, 64)}px`,
} : undefined)
function loaded(event: Event) {
  const image = event.target as HTMLImageElement
  width.value = image.naturalWidth; height.value = image.naturalHeight
  emit('load', event)
}
</script>

<template>
  <img :src="src" :class="{ 'site-icon': compact }" :style="iconStyle" @load="loaded" />
</template>

<style scoped>
img.site-icon { object-fit: contain; object-position: center; flex-shrink: 0; }
</style>
