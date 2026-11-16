<script setup lang="ts">
import { ref } from 'vue'
import { ChevronRight, Plus, Store } from 'lucide-vue-next'
import type { Item } from '../shared/api'
import type { CardOrigin } from '../shared/cardTransition'
import ItemCard from './ItemCard.vue'

defineProps<{ items: Item[]; canAdd: boolean }>()
const emit = defineEmits<{ add: []; open: [item: Item, origin: CardOrigin] }>()
const rail = ref<HTMLElement>()
function next() {
  rail.value?.scrollBy({ left: rail.value.clientWidth, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
}
</script>

<template>
  <section class="certificate-carousel" aria-label="Сертификаты">
    <div ref="rail" class="certificate-carousel-track" tabindex="0" aria-label="Магазины — листайте влево">
      <button class="certificate-carousel-cover" aria-label="Сертификаты — листайте или нажмите, чтобы посмотреть" @click="next"><span class="certificate-room-icon"><Store :size="26" :stroke-width="1.5" /></span><span class="certificate-room-copy"><h2>Сертификаты</h2><span class="certificate-room-caption">На покупки, занятия и впечатления</span></span><span class="certificate-swipe-hint"><ChevronRight :size="20" /></span></button>
      <ItemCard v-for="(item, index) in items" :key="item.id" :item="item" :index="index" @open="(item, origin) => emit('open', item, origin)" />
      <button v-if="canAdd" class="certificate-carousel-add" @click="emit('add')"><Plus :size="20" />Добавить магазин</button>
      <p v-else-if="!items.length" class="certificate-carousel-empty">Магазины пока не добавлены</p>
    </div>
  </section>
</template>
