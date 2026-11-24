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
  return certificateIcon(item) || (item.image_id ? imageUrl(item.image_id) : '');
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
      @scroll.passive="updateReveal"
      @keydown.right.prevent="navigate(true)"
      @keydown.left.prevent="navigate(false)"
    >
      <AppButton
        variant="custom"
        class="certificate-carousel-cover"
        label="Посмотреть магазины сертификатов"
        @click="navigate(true)"
      >
        <span class="certificate-emblem" aria-hidden="true"><Store :size="21" :stroke-width="1.5" /></span>
        <span class="certificate-copy">
          <h2>Сертификаты</h2>
          <span>Любимые магазины — подарок на ваш вкус</span>
        </span>
        <ArrowRight class="certificate-arrow" :size="19" aria-hidden="true" />
      </AppButton>

      <div ref="stores" class="certificate-stores" :class="{ 'is-visible': storesVisible }" role="group" aria-label="Магазины сертификатов">
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
              @error="failLogo(logo(item))"
            />
            <Store v-else :size="26" :stroke-width="1.5" aria-hidden="true" />
          </AppButton>
          <AppButton
            v-if="canAdd"
            variant="custom"
            class="certificate-shop certificate-carousel-add"
            :style="{ '--order': Math.min(items.length, 6) }"
            label="Добавить магазин"
            title="Добавить магазин"
            @click="emit('add')"
          ><Plus :size="24" :stroke-width="1.5" /></AppButton>
        </div>
        <p v-if="!items.length && !canAdd" class="certificate-empty">Магазины пока не добавлены</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.certificate-carousel {
  margin: 20px 0;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 20%);
  border-radius: 24px;
  background: linear-gradient(110deg, #28553f 0%, #648c4a 32%, #b7a85f 65%, #45816a 100%);
  color: #faf7ee;
  box-shadow: inset 0 0 16px rgb(255 255 255 / 8%), 0 8px 0 -5px rgb(114 121 107 / 15%);
}
.certificate-carousel-track {
  display: flex;
  align-items: stretch;
  overflow-x: auto;
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
  min-height: 96px;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  scroll-snap-align: start;
}
.certificate-carousel-cover { text-align: left; color: inherit; }
.certificate-emblem {
  display: grid;
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid rgb(255 255 255 / 15%);
  border-radius: 14px;
  background: rgb(255 255 255 / 8%);
}
.certificate-copy { flex: 1; min-width: 0; }
.certificate-copy h2 { margin: 0; font: 400 22px / 1.2 var(--font-editorial); }
.certificate-copy > span { display: block; margin-top: 5px; font-size: 12px; line-height: 1.4; opacity: .8; }
.certificate-arrow { flex-shrink: 0; opacity: .8; }
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
  flex: 0 0 62px;
  width: 62px;
  height: 62px;
  place-items: center;
  padding: 2px;
  border: 1px solid rgb(255 255 255 / 25%);
  border-radius: 16px;
  background: rgb(255 255 255 / 15%);
  color: inherit;
  opacity: 0;
  transform: translate(34px, 22px) rotate(-12deg) scale(.9);
  transition: transform 480ms cubic-bezier(.22, 1, .36, 1), opacity 260ms ease;
}
.certificate-stores.is-visible .certificate-shop {
  opacity: 1;
  transform: translate(0, 0) rotate(5deg) scale(1);
  transition-delay: calc(var(--order, 0) * 70ms);
}
.certificate-shop + .certificate-shop { margin-left: -8px; }
.certificate-shop img { width: 56px; height: 56px; border-radius: 13px; object-fit: contain; background: #fff; }
.certificate-shop:focus-visible { z-index: 1; }
.certificate-carousel-add { background: rgb(255 255 255 / 12%); }
.certificate-empty { margin: 0; font-size: 12px; opacity: .8; }
@media (prefers-reduced-motion: reduce) {
  .certificate-stores .certificate-shop { opacity: 1; transform: rotate(5deg); transition: none; }
}
button:focus-visible { outline: 2px solid #faf7ee; outline-offset: 3px; }
@media (hover: hover) {
  .certificate-back:hover,
  .certificate-carousel-add:hover { background: rgb(255 255 255 / 24%); }
}
</style>
