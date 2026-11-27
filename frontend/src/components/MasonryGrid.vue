<script setup lang="ts">
import { onBeforeUnmount, onMounted, onUpdated, ref } from 'vue';

const grid = ref<HTMLElement>();
let observer: ResizeObserver | undefined;
let frame = 0;
const cards = new Set<HTMLElement>();

function layout() {
  frame = 0;
  if (!grid.value) return;
  const gap = parseFloat(getComputedStyle(grid.value).columnGap) || 0;
  for (const card of cards) {
    // Pixel rows pack cards without stretching them or changing DOM/tab order.
    card.style.gridRowEnd = `span ${Math.ceil(card.getBoundingClientRect().height + gap)}`;
  }
}

function scheduleLayout() {
  if (!frame) frame = requestAnimationFrame(layout);
}

function observeCards() {
  if (!grid.value || !observer) return;
  const current = new Set(Array.from(grid.value.children) as HTMLElement[]);
  for (const card of cards) {
    if (!current.has(card)) {
      observer.unobserve(card);
      cards.delete(card);
    }
  }
  for (const card of current) {
    if (!cards.has(card)) {
      cards.add(card);
      observer.observe(card);
    }
  }
  scheduleLayout();
}

onMounted(() => {
  observer = new ResizeObserver(scheduleLayout);
  if (grid.value) observer.observe(grid.value);
  observeCards();
});
onUpdated(observeCards);
onBeforeUnmount(() => {
  observer?.disconnect();
  cancelAnimationFrame(frame);
});
</script>

<template>
  <div
    ref="grid"
    class="cards-grid masonry-grid grid auto-rows-[1px] grid-flow-dense items-start gap-x-2.5 gap-y-0"
  >
    <slot />
  </div>
</template>
