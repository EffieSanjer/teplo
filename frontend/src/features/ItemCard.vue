<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Archive, ArrowUpRight, Gift, Lightbulb, MoreHorizontal, Pencil, RotateCcw, Store, Trash2 } from 'lucide-vue-next'
import { formatPrice, imageUrl, itemTitle, type Item } from '../shared/api'
import WishImage from '../shared/WishImage.vue'
import WishArtwork from '../shared/WishArtwork.vue'
import { loadCertificateColor, type CertificateColor } from '../shared/certificateColor'
import { certificateTitle } from '../shared/certificateTitle'

const props = defineProps<{ item: Item; index: number }>()
const emit = defineEmits<{ open: [item: Item]; edit: [item: Item]; archive: [item: Item]; delete: [item: Item] }>()
const plasticCard = computed(() => props.item.item_type === 'certificate' && !props.item.archived_at)
const certificateText = computed(() => certificateTitle(itemTitle(props.item)))
const certificatePattern = computed(() => {
  const hash = Array.from(props.item.id).reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, 0)
  return ['flow', 'fold', 'halo'][hash % 3]
})
const certificateTone = ref<CertificateColor | null>(null)
const certificateStyle = computed(() => certificateTone.value ? {
  '--certificate-bg': certificateTone.value.background, '--certificate-ink': certificateTone.value.ink,
  '--certificate-logo-bg': certificateTone.value.logoBackground || 'transparent',
} : undefined)
const certificateLogoFailed = ref(false)
watch(() => plasticCard.value ? props.item.image_id : null, async (id, _, onCleanup) => {
  let current = true
  onCleanup(() => { current = false })
  certificateTone.value = null
  certificateLogoFailed.value = false
  if (!id) return
  const tone = await loadCertificateColor(imageUrl(id))
  if (current) certificateTone.value = tone
}, { immediate: true })
const artwork = computed(() => props.item.image_id ? 'art-photo' : 'art-designed')
const photoLayout = ref<'landscape' | 'portrait' | 'square'>('square')
const photoRatio = ref('1 / 1')
const photoStyle = computed(() => props.item.image_id && props.item.item_type !== 'certificate' ? { aspectRatio: photoRatio.value } : undefined)
watch(() => props.item.image_id, () => { photoLayout.value = 'square'; photoRatio.value = '1 / 1' })
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
let cleanupMenu = () => {}
onBeforeUnmount(() => cleanupMenu())
function menuToggled(event: Event) {
  cleanupMenu()
  const menu = event.currentTarget as HTMLDetailsElement
  const dropdown = menu.querySelector<HTMLElement>('.dropdown')
  if (!menu.open || !dropdown) return
  if (menu.closest('.certificate-rail')) {
    // Escape the scrolling rail's clipping area, keeping every action visible.
    const position = () => {
      const bounds = menu.getBoundingClientRect()
      dropdown.style.left = `${Math.max(8, Math.min(bounds.right - dropdown.offsetWidth, window.innerWidth - dropdown.offsetWidth - 8))}px`
      dropdown.style.top = `${Math.max(8, Math.min(bounds.bottom + 6, window.innerHeight - dropdown.offsetHeight - 8))}px`
      dropdown.style.right = 'auto'
    }
    position()
    window.addEventListener('scroll', position, true)
    window.addEventListener('resize', position)
    cleanupMenu = () => { window.removeEventListener('scroll', position, true); window.removeEventListener('resize', position) }
    return
  }
  // Keep the menu beside its card, even in the leftmost narrow column.
  dropdown.style.right = `${Math.min(0, menu.getBoundingClientRect().right - dropdown.offsetWidth - 8)}px`
}
</script>

<template>
  <article class="gift-card" :class="{ archived: item.archived_at, 'without-photo': !item.image_id, 'certificate-card': plasticCard }" :style="certificateStyle">
    <button v-if="plasticCard" class="card-open certificate-face" :class="[`certificate-pattern-${certificatePattern}`, { 'has-logo': item.image_id && !certificateLogoFailed }]" :aria-label="`Открыть: ${itemTitle(item)}`" @click="emit('open', item)">
      <span v-if="item.image_id && !certificateLogoFailed" class="certificate-logo"><WishImage :src="imageUrl(item.image_id)" :is-icon="true" alt="" loading="lazy" @error="certificateLogoFailed = true" /></span>
      <div class="certificate-text"><h3>{{ certificateText.name }}</h3><span v-if="certificateText.description" class="certificate-subtitle">{{ certificateText.description }}</span></div>
    </button>
    <button v-else-if="!item.archived_at" class="card-open" :aria-label="`Открыть: ${itemTitle(item)}`" @click="emit('open', item)">
      <div class="card-art" :class="artwork" :style="photoStyle">
        <WishImage v-if="item.image_id" :src="imageUrl(item.image_id)" :is-icon="item.image_is_icon" :class="`photo-${photoLayout}`" alt="" loading="lazy" @load="photoLoaded" />
        <WishArtwork v-else :seed="item.id" :type="item.item_type" />
        <span class="type-pill"><Store v-if="item.item_type === 'certificate'" :size="12" /><Lightbulb v-else-if="item.item_type === 'idea'" :size="12" /><Gift v-else :size="12" />{{ item.item_type === 'certificate' ? 'Сертификат' : item.item_type === 'idea' ? 'Идея' : 'Подарок' }}</span>
        <span class="art-arrow"><ArrowUpRight :size="19" /></span>
      </div>
      <div class="card-body"><span v-if="item.item_type === 'certificate'" class="certificate-label">Подарочная карта</span><h3>{{ itemTitle(item) }}</h3><div v-if="item.item_type !== 'certificate' || item.list_type === 'surprise'" class="card-bottom"><strong v-if="item.item_type !== 'certificate'">{{ formatPrice(item) }}</strong><span v-if="item.list_type === 'surprise'" class="author">{{ item.author_name }}</span></div></div>
    </button>
    <div v-else class="archived-content">
      <div class="card-art" :class="artwork" :style="photoStyle"><WishImage v-if="item.image_id" :src="imageUrl(item.image_id)" :is-icon="item.image_is_icon" :class="`photo-${photoLayout}`" alt="" loading="lazy" @load="photoLoaded" /><WishArtwork v-else :seed="item.id" :type="item.item_type" /><span class="type-pill"><Archive :size="12" />В архиве</span></div>
      <div class="card-body"><h3>{{ itemTitle(item) }}</h3><div class="card-bottom"><strong v-if="item.item_type !== 'certificate'">{{ formatPrice(item) }}</strong><span class="price-note">В архиве</span></div></div>
    </div>
    <details v-if="item.can_manage" class="card-menu" @toggle="menuToggled">
      <summary class="icon-button" :aria-label="`Управление: ${itemTitle(item)}`"><MoreHorizontal :size="21" /></summary>
      <div class="dropdown">
        <button v-if="!item.archived_at" @click="emit('edit', item); ($event.currentTarget as HTMLElement).closest('details')?.removeAttribute('open')"><Pencil :size="15" />Редактировать</button>
        <button @click="emit('archive', item); ($event.currentTarget as HTMLElement).closest('details')?.removeAttribute('open')"><RotateCcw v-if="item.archived_at" :size="15" /><Archive v-else :size="15" />{{ item.archived_at ? 'Восстановить' : 'В архив' }}</button>
        <button class="danger-text" @click="emit('delete', item); ($event.currentTarget as HTMLElement).closest('details')?.removeAttribute('open')"><Trash2 :size="15" />Удалить</button>
      </div>
    </details>
  </article>
</template>

<style scoped>
.card-art img {
  position: absolute;
  inset: 0;
  object-fit: contain;
  object-position: center;
  min-width: 0;
  min-height: 0;
}
.card-art :deep(img.site-icon) { position: static; inset: auto; }
</style>
