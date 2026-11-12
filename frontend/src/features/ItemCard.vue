<script setup lang="ts">
import { computed } from 'vue'
import { Archive, ArrowUpRight, Gift, Lightbulb, MoreHorizontal, Pencil, RotateCcw, Store, Trash2 } from 'lucide-vue-next'
import { formatPrice, imageUrl, itemTitle, type Item } from '../shared/api'

const props = defineProps<{ item: Item; index: number }>()
const emit = defineEmits<{ open: [item: Item]; edit: [item: Item]; archive: [item: Item]; delete: [item: Item] }>()
const artwork = computed(() => props.item.image_id ? 'art-photo' : ['art-paper', 'art-blueprint', 'art-paper', 'art-outline'][props.index % 4])
</script>

<template>
  <article class="gift-card" :class="{ archived: item.archived_at }">
    <button v-if="!item.archived_at" class="card-open" :aria-label="`Открыть: ${itemTitle(item)}`" @click="emit('open', item)">
      <div class="card-art" :class="artwork">
        <img v-if="item.image_id" :src="imageUrl(item.image_id)" alt="" loading="lazy" />
        <div v-else class="art-placeholder"><Store v-if="item.item_type === 'certificate'" :size="66" :stroke-width="1.4" /><Gift v-else-if="item.item_type === 'gift'" :size="66" :stroke-width="1.4" /><Lightbulb v-else :size="66" :stroke-width="1.4" /></div>
        <span class="type-pill"><Store v-if="item.item_type === 'certificate'" :size="12" /><Lightbulb v-else-if="item.item_type === 'idea'" :size="12" /><Gift v-else :size="12" />{{ item.item_type === 'certificate' ? 'Сертификат' : item.item_type === 'idea' ? 'Идея' : 'Подарок' }}</span>
        <span class="art-arrow"><ArrowUpRight :size="19" /></span>
      </div>
      <div class="card-body"><h3>{{ itemTitle(item) }}</h3><p>{{ item.description || (item.item_type === 'certificate' ? 'Сертификат в любимый магазин' : 'Хорошая идея на заметку') }}</p><div class="card-bottom"><strong>{{ item.item_type === 'certificate' && item.price == null ? 'Любой номинал' : formatPrice(item) }}</strong><span v-if="item.list_type === 'surprise'" class="author">{{ item.author_name }}</span><span v-else class="price-note">{{ item.price != null ? item.price_mode === 'from' ? 'и выше' : 'примерно' : 'главное — внимание' }}</span></div></div>
    </button>
    <div v-else class="archived-content">
      <div class="card-art" :class="artwork"><img v-if="item.image_id" :src="imageUrl(item.image_id)" alt="" loading="lazy" /><div v-else class="art-placeholder"><Gift :size="62" :stroke-width="1.1" /></div><span class="type-pill"><Archive :size="12" />В архиве</span></div>
      <div class="card-body"><h3>{{ itemTitle(item) }}</h3><p>{{ item.description }}</p><div class="card-bottom"><strong>{{ formatPrice(item) }}</strong><span class="price-note">В архиве</span></div></div>
    </div>
    <details v-if="item.can_manage" class="card-menu">
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
  object-fit: contain;
  object-position: center;
  min-width: 0;
  min-height: 0;
}
</style>
