<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Archive, ArrowUpRight, Store } from 'lucide-vue-next'
import { imageUrl, itemTitle, type Item } from '../shared/api'
import type { CardOrigin } from '../shared/cardTransition'
import WishImage from '../shared/WishImage.vue'
import { itemPalette } from '../shared/itemPalette'
import { certificateTitle } from '../shared/certificateTitle'

const props = defineProps<{ item: Item; index: number }>()
const emit = defineEmits<{ open: [item: Item, origin: CardOrigin] }>()
const plasticCard = computed(() => props.item.item_type === 'certificate' && !props.item.archived_at)
const title = computed(() => props.item.title?.trim() || (props.item.url?.trim() ? itemTitle(props.item) : ''))
const certificateText = computed(() => certificateTitle(itemTitle(props.item)))
const cardHash = computed(() => Array.from(props.item.id).reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, 0))
const certificatePattern = computed(() => ['flow', 'fold', 'halo'][cardHash.value % 3])
const surfaceStyle = computed(() => itemPalette(props.item.id))
const certificateLogoFailed = ref(false)
watch(() => plasticCard.value ? props.item.image_id : null, () => {
  certificateLogoFailed.value = false
}, { immediate: true })
const imageFailed = ref(false)
const hasPhoto = computed(() => Boolean(props.item.image_id && !imageFailed.value))
const photoLayout = ref<'landscape' | 'portrait' | 'square'>('square')
const photoRatio = ref('1 / 1')
const cardStyle = computed(() => {
  const [width, height] = photoRatio.value.split('/').map(Number)
  return {
    ...surfaceStyle.value, '--tile-photo-ratio': String(width! / height!),
    '--idea-gradient': `var(--idea-gradient-${cardHash.value % 4})`,
    '--idea-ink': `var(--idea-ink-${cardHash.value % 4}, var(--ink))`,
    '--card-outline': `var(--card-outline-${cardHash.value % 4}, transparent)`,
  }
})
function open(event: MouseEvent) {
  const card = event.currentTarget as HTMLElement
  const bounds = card.getBoundingClientRect()
  const image = card.querySelector<HTMLImageElement>('.card-art img:not(.site-icon)')
  const photo = image?.complete && image.naturalWidth ? image.getBoundingClientRect() : undefined
  const [width, height] = photoRatio.value.split('/').map(Number)
  emit('open', props.item, {
    left: bounds.left, top: bounds.top, width: bounds.width, height: bounds.height,
    photoRatio: image?.naturalWidth && image.naturalHeight ? image.naturalWidth / image.naturalHeight
      : props.item.image_id && !props.item.image_is_icon && !plasticCard.value ? width! / height! : undefined,
    background: getComputedStyle(card).backgroundColor,
    backgroundImage: getComputedStyle(card).backgroundImage,
    photo: photo && image ? { left: photo.left, top: photo.top, width: photo.width, height: photo.height, src: image.currentSrc || image.src } : undefined,
  })
}
watch(() => props.item.image_id, () => { photoLayout.value = 'square'; photoRatio.value = '1 / 1'; imageFailed.value = false })
function photoLoaded(event: Event) {
  const image = event.target as HTMLImageElement
  if (!image.naturalWidth || !image.naturalHeight) return
  if (props.item.image_is_icon || (image.naturalWidth <= 96 && image.naturalHeight <= 96)) {
    photoRatio.value = '1 / 1'
    return
  }
  photoRatio.value = `${image.naturalWidth} / ${image.naturalHeight}`
  photoLayout.value = image.naturalWidth > image.naturalHeight ? 'landscape'
    : image.naturalHeight > image.naturalWidth ? 'portrait' : 'square'
}
</script>

<template>
  <article class="gift-card collection-tile" :class="[{ archived: item.archived_at, 'without-photo': !hasPhoto, 'certificate-card': plasticCard, 'idea-card': item.item_type === 'idea' }, `wish-note-${cardHash % 4}`]" :style="cardStyle">
    <button v-if="plasticCard" class="card-open certificate-face" :class="[`certificate-pattern-${certificatePattern}`, { 'has-logo': item.image_id && !certificateLogoFailed }]" :aria-label="`Открыть: ${itemTitle(item)}`" @click="open">
      <span v-if="item.image_id && !certificateLogoFailed" class="certificate-logo"><WishImage :src="imageUrl(item.image_id)" :is-icon="true" alt="" loading="lazy" @error="certificateLogoFailed = true" /></span>
      <Store v-else class="shop-symbol" :size="28" :stroke-width="1.2" />
      <div class="certificate-text"><span class="tile-overline">ПОДАРОЧНАЯ КАРТА</span><h3>{{ certificateText.name }}</h3><span v-if="certificateText.description" class="certificate-subtitle">{{ certificateText.description }}</span></div><ArrowUpRight class="shop-arrow" :size="18" />
    </button>
    <button v-else class="card-open tile-open" :class="{ 'tile-photo': hasPhoto, 'tile-note': !hasPhoto }" :aria-label="`Открыть: ${itemTitle(item)}`" @click="open">
      <span v-if="item.archived_at" class="tile-kind"><Archive :size="12" aria-hidden="true" />В архиве</span>
      <div v-if="hasPhoto" class="card-art tile-media art-photo"><WishImage :src="imageUrl(item.image_id!)" :is-icon="item.image_is_icon" :class="`photo-${photoLayout}`" alt="" loading="lazy" @load="photoLoaded" @error="imageFailed = true" /></div>
      <div class="tile-content">
        <span v-if="!hasPhoto" class="wish-note-mark" aria-hidden="true">{{ item.item_type === 'idea' ? 'На заметку' : 'Хочется' }}</span>
        <h3 v-if="title" :title="title">{{ title }}</h3>
        <p v-if="!hasPhoto && item.description?.trim()" class="wish-note-excerpt">{{ item.description.trim() }}</p>
      </div>
    </button>
  </article>
</template>
