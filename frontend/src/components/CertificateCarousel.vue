<script setup lang="ts">
import { ref } from 'vue';
import { ChevronRight, Plus, Store } from 'lucide-vue-next';
import type { Item } from '../shared/api';
import type { CardOrigin } from '../shared/cardTransition';
import ItemCard from './ItemCard.vue';

defineProps<{ items: Item[]; canAdd: boolean }>();
const emit = defineEmits<{ add: []; open: [item: Item, origin: CardOrigin] }>();
const rail = ref<HTMLElement>();
function next() {
  rail.value?.scrollBy({
    left: rail.value.clientWidth,
    behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
  });
}
</script>

<template>
  <section
    class="certificate-carousel my-5 overflow-hidden rounded-lg border border-[#d4cfbb] bg-[#ede7d8] p-2 text-ink dark:border-[#4e594b] dark:bg-[#303b31] dark:text-paper"
    aria-label="Сертификаты"
  >
    <div
      ref="rail"
      class="certificate-carousel-track flex snap-x snap-mandatory items-stretch gap-2 overflow-x-auto overscroll-x-contain pb-1 [&>article]:w-[170px] [&>article]:shrink-0 [&>article]:snap-start"
      tabindex="0"
      aria-label="Магазины — листайте влево"
    >
      <button
        class="certificate-carousel-cover flex w-[calc(100%-24px)] shrink-0 snap-start items-center justify-start gap-3 rounded p-2 text-left"
        aria-label="Сертификаты — листайте или нажмите, чтобы посмотреть"
        @click="next"
      >
        <span class="certificate-room-icon"><Store :size="20" :stroke-width="1.5" /></span
        ><span class="certificate-room-copy [&_h2]:font-editorial [&_h2]:text-lg"
          ><h2>Сертификаты</h2> </span
        ><span class="certificate-swipe-hint ml-auto"><ChevronRight :size="20" /></span>
      </button>
      <ItemCard
        v-for="(item, index) in items"
        :key="item.id"
        :item="item"
        :index="index"
        @open="(item, origin) => emit('open', item, origin)"
      />
      <button
        v-if="canAdd"
        class="certificate-carousel-add flex w-40 shrink-0 items-center justify-center gap-2 rounded border border-dashed border-line p-4 text-xs"
        @click="emit('add')"
      >
        <Plus :size="20" />Добавить магазин
      </button>
      <p
        v-else-if="!items.length"
        class="certificate-carousel-empty self-center px-4 text-xs text-muted"
      >
        Магазины пока не добавлены
      </p>
    </div>
  </section>
</template>
