<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Archive, ArrowUpRight, Gift, MoreHorizontal, Pencil, RotateCcw, Trash2 } from 'lucide-vue-next'
import Modal from '../shared/Modal.vue'
import { formatPrice, hasPrice, imageUrl, itemTitle, type Item } from '../shared/api'
import { openExternal } from '../integrations/telegram'
import WishImage from '../shared/WishImage.vue'
import type { CardOrigin } from '../shared/cardTransition'
import { itemPalette } from '../shared/itemPalette'
const props = defineProps<{ item: Item; ownProfile: boolean; busy: boolean; canSurprise?: boolean; origin?: CardOrigin }>()
const emit = defineEmits<{ close: []; edit: [item: Item]; copy: [item: Item]; archive: [item: Item]; delete: [item: Item] }>()
const photoRatio = ref<number | undefined>(props.origin?.photoRatio)
const imageFailed = ref(false)
const surfaceStyle = computed(() => {
  const hash = Array.from(props.item.id).reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, 0)
  return { ...itemPalette(props.item.id), '--idea-gradient': `var(--idea-gradient-${hash % 4})`, '--idea-ink': `var(--idea-ink-${hash % 4}, var(--ink))`, '--card-pattern': props.origin?.backgroundImage || `var(--idea-gradient-${hash % 4})` }
})
const photoStyle = computed(() => photoRatio.value ? {
  aspectRatio: String(photoRatio.value), height: 'var(--detail-photo-height, auto)', flex: 'none',
} : undefined)
watch(() => props.item.image_id, () => { photoRatio.value = props.origin?.photoRatio; imageFailed.value = false })
function photoLoaded(event: Event) {
  const image = event.target as HTMLImageElement
  if (image.naturalWidth && image.naturalHeight && !props.item.image_is_icon && (image.naturalWidth > 96 || image.naturalHeight > 96)) {
    photoRatio.value = image.naturalWidth / image.naturalHeight
  }
}
</script>

<template>
  <Modal :title="itemTitle(item)" variant="item-detail" :surface-style="surfaceStyle" :origin="origin" :photo-ratio="photoRatio" :has-photo="Boolean(item.image_id && !imageFailed)" @close="emit('close')">
    <template #header-actions>
      <details v-if="item.can_manage" class="detail-menu">
        <summary class="icon-button" :aria-label="`Управление: ${itemTitle(item)}`"><MoreHorizontal :size="21" /></summary>
        <div class="dropdown">
          <button v-if="!item.archived_at" :disabled="busy" @click="emit('edit', item)"><Pencil :size="15" />Редактировать</button>
          <button :disabled="busy" @click="emit('archive', item); ($event.currentTarget as HTMLElement).closest('details')?.removeAttribute('open')"><RotateCcw v-if="item.archived_at" :size="15" /><Archive v-else :size="15" />{{ item.archived_at ? 'Восстановить' : 'В архив' }}</button>
          <button class="danger-text" :disabled="busy" @click="emit('delete', item)"><Trash2 :size="15" />Удалить</button>
        </div>
      </details>
    </template>
    <div v-if="item.image_id && !imageFailed" class="detail-art art-photo"><WishImage :src="imageUrl(item.image_id)" :is-icon="item.image_is_icon" :style="photoStyle" :alt="itemTitle(item)" @load="photoLoaded" @error="imageFailed = true" /><div class="detail-photo-caption"><span class="detail-photo-label">{{ item.archived_at ? 'В архиве' : item.item_type === 'certificate' ? 'Подарочная карта' : item.item_type === 'idea' ? 'Идея' : 'Желание' }}</span><h2 class="detail-mobile-title">{{ itemTitle(item) }}</h2></div></div>
    <div class="detail-body item-info" :style="surfaceStyle" :class="{ 'glass-panel': item.image_id && !imageFailed }">
      <div class="detail-sheet-content">
      <h2 v-if="item.image_id && !imageFailed" class="detail-card-title">{{ itemTitle(item) }}</h2>
      <p v-if="!item.image_id || imageFailed" class="detail-kicker">{{ item.archived_at ? 'В архиве' : item.item_type === 'certificate' ? 'Подарочная карта' : item.item_type === 'idea' ? 'Идея' : 'Желание' }}</p>
      <div v-if="!item.image_id || imageFailed || (item.item_type !== 'certificate' && hasPrice(item))" class="detail-heading">
        <h2 v-if="!item.image_id || imageFailed" class="detail-mobile-title">{{ itemTitle(item) }}</h2>
        <div v-if="item.item_type !== 'certificate' && hasPrice(item)" class="detail-price-row"><span>{{ item.price_mode === 'from' ? 'Стоимость от' : 'Ориентир по цене' }}</span><p class="detail-price">{{ formatPrice(item) }}</p></div>
      </div>
      <div v-if="item.description?.trim() || (item.list_type === 'surprise' && item.author_name?.trim())" class="detail-copy">
      <div v-if="item.description?.trim()" class="detail-note"><span class="collection-eyebrow">ПОЖЕЛАНИЯ И ПОДСКАЗКИ</span><p class="detail-description">{{ item.description }}</p></div>
      <p v-if="item.list_type === 'surprise' && item.author_name?.trim()" class="detail-author">От {{ item.author_name }}</p>
      </div>
      <div v-if="item.url?.trim() || (!ownProfile && canSurprise && item.list_type === 'wishlist')" class="detail-actions">
        <button v-if="item.url?.trim()" class="button primary" :aria-label="item.item_type === 'certificate' ? 'Открыть магазин' : 'Открыть ссылку'" @click="openExternal(item.url)"><ArrowUpRight :size="16" /><span class="action-full">{{ item.item_type === 'certificate' ? 'Открыть магазин' : 'Открыть ссылку' }}</span><span class="action-short" aria-hidden="true">{{ item.item_type === 'certificate' ? 'Магазин' : 'Ссылка' }}</span></button>
        <button v-if="!ownProfile && canSurprise && item.list_type === 'wishlist'" class="button secondary" :aria-label="busy ? 'Добавляем…' : 'Создать сюрприз'" :disabled="busy" @click="emit('copy', item)"><Gift :size="16" /><span class="action-full">{{ busy ? 'Добавляем…' : 'Создать сюрприз' }}</span><span class="action-short" aria-hidden="true">{{ busy ? 'Ждём…' : 'Сюрприз' }}</span></button>
      </div>
      </div>
    </div>
  </Modal>
</template>

<style scoped src="../styles/scoped/item-detail.css"></style>
