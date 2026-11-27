<script setup lang="ts">
import { ref } from 'vue';
import { ArrowLeft, ArrowRight, Plus, Store } from 'lucide-vue-next';
import { imageUrl, itemTitle, type Item } from '../shared/api';
import { certificateIcon } from '../shared/certificateStores';
import type { CardOrigin } from '../shared/cardTransition';
import { AppButton } from './ui';

defineProps<{ items: Item[]; canAdd: boolean }>();
const emit = defineEmits<{ add: []; open: [item: Item, origin: CardOrigin] }>();
const rail = ref<HTMLElement>();
const stores = ref<HTMLElement>();
const failedLogos = ref(new Set<string>());
const reveal = ref(0);
const storesVisible = ref(false);

function updateReveal() {
  if (!rail.value || !stores.value) return;
  const track = rail.value.getBoundingClientRect();
  const panel = stores.value.getBoundingClientRect();
  reveal.value = Math.max(0, Math.min(1, (track.right - panel.left) / track.width));
  if (reveal.value > .3) storesVisible.value = true;
  else if (reveal.value < .1) storesVisible.value = false;
}

function logo(item: Item) {
  return certificateIcon(item) || (item.image_id ? imageUrl(item.image_id, 400) : '');
}
function monogram(item: Item) {
  const words = itemTitle(item).replace(/[^\p{L}\p{N}\s]/gu, ' ').trim().split(/\s+/).filter(Boolean);
  return Array.from(words.join('') || '?').slice(0, 2).join('').toLocaleUpperCase('ru');
}
function fallbackStyle(item: Item) {
  const key = item.url || item.id;
  const hash = Array.from(key).reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, 0);
  const palettes = [ ['#426951', '#a5b87a'], ['#526e73', '#a3b8ad'], ['#77684b', '#c4b586'], ['#655c76', '#a7a48e'] ];
  const colors = palettes[hash % palettes.length]!;
  return { background: `linear-gradient(145deg, ${colors[0]}, ${colors[1]})` };
}
function failLogo(src: string) {
  failedLogos.value = new Set([...failedLogos.value, src]);
}
function navigate(toStores: boolean) {
  if (!rail.value || !stores.value) return;
  const left = toStores
    ? stores.value.getBoundingClientRect().left - rail.value.getBoundingClientRect().left + rail.value.scrollLeft
    : 0;
  rail.value.scrollTo({
    left,
    behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth',
  });
}
function open(item: Item, event: MouseEvent) {
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
  emit('open', item, { left: rect.left, top: rect.top, width: rect.width, height: rect.height });
}
</script>

<template>
  <section class="certificate-carousel" aria-label="Сертификаты">
    <div
      ref="rail"
      class="certificate-carousel-track"
      tabindex="0"
      @scroll.passive="updateReveal"
      @keydown.right.prevent="navigate(true)"
      @keydown.left.prevent="navigate(false)"
    >
      <AppButton
        variant="custom"
        class="certificate-carousel-cover"
        label="Посмотреть сертификаты"
        @click="navigate(true)"
      >
        <span class="certificate-emblem" aria-hidden="true"><Store :size="21" :stroke-width="1.5" /></span>
        <span class="certificate-copy">
          <h2>Сертификаты</h2>
          <span>На впечатления и подарки</span>
        </span>
        <ArrowRight class="certificate-arrow" :size="19" aria-hidden="true" />
      </AppButton>

      <div ref="stores" class="certificate-stores" :class="{ 'is-visible': storesVisible }" role="group" aria-label="Сертификаты">
        <AppButton variant="custom" class="certificate-back" label="Назад к сертификатам" @click="navigate(false)">
          <ArrowLeft :size="17" />
        </AppButton>
        <div class="certificate-stack">
          <AppButton
            v-for="(item, index) in items"
            :key="item.id"
            variant="custom"
            class="certificate-shop"
            :style="{ '--order': Math.min(index, 6) }"
            :label="`Открыть: ${itemTitle(item)}`"
            :title="itemTitle(item)"
            @click="open(item, $event)"
          >
            <img
              v-if="logo(item) && !failedLogos.has(logo(item))"
              :src="logo(item)"
              alt=""
              loading="lazy"
              decoding="async"
              @error="failLogo(logo(item))"
            />
            <span v-else class="certificate-monogram" :style="fallbackStyle(item)" aria-hidden="true">{{ monogram(item) }}</span>
          </AppButton>
          <AppButton
            v-if="canAdd"
            variant="custom"
            class="certificate-shop certificate-carousel-add"
            :style="{ '--order': Math.min(items.length, 6) }"
            label="Добавить сертификат"
            title="Добавить сертификат"
            @click="emit('add')"
          ><Plus :size="24" :stroke-width="1.5" /></AppButton>
        </div>
        <p v-if="!items.length && !canAdd" class="certificate-empty">Сертификаты пока не добавлены</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.certificate-carousel {
  margin: 8px 0 20px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--accent) 22%, var(--line));
  border-radius: 28px;
  background:
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--accent) 22%, var(--surface)) 0%,
      color-mix(in srgb, var(--ember) 10%, var(--surface)) 48%,
      color-mix(in srgb, var(--accent) 14%, var(--surface)) 100%
    );
  color: var(--ink);
  box-shadow: 0 10px 28px rgb(12 24 36 / 8%);
}
:root[data-theme='dark'] .certificate-carousel {
  border-color: color-mix(in srgb, var(--accent) 28%, var(--line));
  background:
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--accent) 24%, var(--surface)) 0%,
      color-mix(in srgb, var(--ember) 12%, var(--surface)) 50%,
      color-mix(in srgb, var(--accent) 16%, var(--surface)) 100%
    );
  box-shadow: 0 10px 28px rgb(0 0 0 / 22%);
}
.certificate-carousel-track {
  display: flex;
  align-items: stretch;
  overflow-x: auto;
  overflow-y: hidden;
  overscroll-behavior-x: contain;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
}
.certificate-carousel-track::-webkit-scrollbar { display: none; }
.certificate-carousel-cover,
.certificate-stores {
  box-sizing: border-box;
  display: flex;
  flex: 0 0 100%;
  min-width: 0;
  min-height: 92px;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  scroll-snap-align: start;
}
.certificate-carousel-cover { text-align: left; color: inherit; }
.certificate-emblem {
  display: grid;
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--ember) 28%, var(--line));
  border-radius: 14px;
  background: color-mix(in srgb, var(--ember) 14%, var(--surface));
  color: var(--ember);
}
.certificate-copy { flex: 1; min-width: 0; }
.certificate-copy h2 {
  margin: 0;
  font: 600 18px / 1.2 var(--font-sans);
  letter-spacing: -0.02em;
}
.certificate-copy > span {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--muted);
}
.certificate-arrow { flex-shrink: 0; color: var(--muted); }
.certificate-stores { flex-basis: auto; min-width: 100%; }
.certificate-back {
  display: grid;
  flex: 0 0 32px;
  min-height: 44px;
  place-items: center;
  border-radius: 12px;
  color: inherit;
}
.certificate-stack { display: flex; align-items: center; padding: 3px 5px; }
.certificate-shop {
  position: relative;
  display: grid;
  flex: 0 0 58px;
  width: 58px;
  height: 58px;
  place-items: center;
  padding: 2px;
  border: 1px solid rgb(255 255 255 / 50%);
  border-radius: 16px;
  background: rgb(255 255 255 / 42%);
  color: inherit;
  opacity: 0;
  transform: translate(34px, 22px) rotate(-12deg) scale(.9);
  transition: transform 480ms cubic-bezier(.22, 1, .36, 1), opacity 260ms ease;
}
:root[data-theme='dark'] .certificate-shop {
  border-color: rgb(255 255 255 / 14%);
  background: rgb(255 255 255 / 8%);
}
.certificate-stores.is-visible .certificate-shop {
  opacity: 1;
  transform: translate(0, 0) rotate(5deg) scale(1);
  transition-delay: calc(var(--order, 0) * 70ms);
}
.certificate-shop + .certificate-shop { margin-left: -8px; }
.certificate-shop img {
  width: 52px;
  height: 52px;
  border-radius: 13px;
  object-fit: contain;
  background: #fff;
}
.certificate-monogram {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 13px;
  color: #fff;
  font: italic 500 22px / 1 var(--font-editorial);
  text-shadow: 0 1px 4px rgb(0 0 0 / 15%);
}
.certificate-shop:focus-visible { z-index: 1; }
.certificate-carousel-add { background: rgb(255 255 255 / 28%); color: var(--accent); }
.certificate-empty { margin: 0; font-size: 12px; color: var(--muted); }
@media (prefers-reduced-motion: reduce) {
  .certificate-stores .certificate-shop { opacity: 1; transform: rotate(5deg); transition: none; }
}
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (hover: hover) {
  .certificate-back:hover,
  .certificate-carousel-add:hover { background: rgb(255 255 255 / 48%); }
}
</style>
