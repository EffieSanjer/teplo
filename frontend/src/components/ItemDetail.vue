<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import {
  ArchiveRestore,
  ArchiveX,
  ArrowUpRight,
  Heart,
  MoreHorizontal,
  Pencil,
  Trash2,
  X,
} from 'lucide-vue-next';
import { formatPrice, hasPrice, imageUrl, itemTitle, type Item } from '../shared/api';
import { openExternal } from '../integrations/telegram';
import CertificateDetail from './CertificateDetail.vue';
import type { CardOrigin } from '../shared/cardTransition';
const props = defineProps<{
  item: Item;
  ownProfile: boolean;
  busy: boolean;
  origin?: CardOrigin;
}>();
const emit = defineEmits<{
  close: [];
  edit: [item: Item];
  priority: [item: Item];
  reserve: [item: Item];
  archive: [item: Item];
  delete: [item: Item];
}>();
const viewer = ref<HTMLDialogElement>();
const sheet = ref<HTMLElement>();
const content = ref<HTMLElement>();
const heading = ref<HTMLElement>();
const imageFailed = ref(false);
const photoRatio = ref(props.origin?.photoRatio || 0);
const photoHeight = ref(0);
const viewportHeight = ref(0);
const contentHeight = ref(0);
const hasPhoto = computed(() =>
  Boolean(props.item.item_type !== 'certificate' && props.item.image_id && !imageFailed.value),
);
let observer: ResizeObserver | undefined;
let previous: HTMLElement | null = null;
let previousOverflow = '';
let current = 0;
let target = 0;

let minimum = 0;
let maximum = 0;
let lower = 0;
let initialized = false;
let dragging = false;
let dragY = 0;
let dragStart = 0;
let dragged = false;
let positionedByUser = false;
let base = 0;
let animation = 0;
let lastPointerY = 0;
let lastPointerTime = 0;
let velocity = 0;
let gestureStartTime = 0;
const clamp = (value: number) => Math.min(maximum, Math.max(minimum, value));
function stopAnimation() {
  cancelAnimationFrame(animation);
  animation = 0;
}
function glideTo(value: number, duration = 380) {
  stopAnimation();
  target = clamp(value);
  positionedByUser = true;
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
    current = target;
    paint();
    return;
  }
  const start = current;
  const destination = target;
  const started = performance.now();
  function tick(now: number) {
    const progress = Math.min(1, (now - started) / duration);
    current = start + (destination - start) * (1 - (1 - progress) ** 3);
    paint();
    if (progress < 1) animation = requestAnimationFrame(tick);
    else animation = 0;
  }
  animation = requestAnimationFrame(tick);
}
function paint() {
  if (sheet.value) {
    sheet.value.style.transform = `translateY(${current}px)`;
    sheet.value.style.minHeight = `${Math.max(0, viewportHeight.value - current)}px`;
  }
}
function moveTo(value: number) {
  stopAnimation();
  target = clamp(value);
  current = target;
  positionedByUser = true;
  paint();
}
function measure() {
  const height = viewer.value?.clientHeight || window.innerHeight;
  const width = viewer.value?.clientWidth || window.innerWidth;
  viewportHeight.value = height;
  photoHeight.value =
    props.item.item_type === 'certificate'
      ? 0
      : hasPhoto.value && photoRatio.value
        ? width / photoRatio.value
        : height * 0.6;
  contentHeight.value = content.value?.offsetHeight || 0;
  const lineHeight = heading.value
    ? parseFloat(getComputedStyle(heading.value).lineHeight) || 38
    : 38;
  const peek = lineHeight * 2 + 64;
  base = Math.min(photoHeight.value, Math.max(0, Math.min(height * 0.6, height - peek)));
  lower = height - photoHeight.value >= peek ? photoHeight.value : base;
  minimum = Math.min(0, height - contentHeight.value);
  maximum = Math.max(base, lower);
  target = initialized && positionedByUser ? clamp(target) : base;
  current = target;
  initialized = true;
  paint();
}
function loaded(event: Event) {
  const image = event.target as HTMLImageElement;
  photoRatio.value = image.naturalWidth / image.naturalHeight;
  measure();
}
async function failed() {
  imageFailed.value = true;
  await nextTick();
  measure();
}
function interactive(target: EventTarget | null) {
  return (
    target instanceof Element &&
    Boolean(target.closest('a, button, summary, details, input, textarea, select'))
  );
}
function pointerDown(event: PointerEvent) {
  if (event.button !== 0 || interactive(event.target)) return;
  stopAnimation();
  target = current;
  dragging = true;
  dragged = false;
  dragY = event.clientY;
  dragStart = target;
  lastPointerY = event.clientY;
  gestureStartTime = lastPointerTime = performance.now();
  velocity = 0;
  (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
}
function pointerMove(event: PointerEvent) {
  if (!dragging) return;
  const now = performance.now();
  const elapsed = now - lastPointerTime;
  if (elapsed > 0) velocity = (event.clientY - lastPointerY) / elapsed;
  lastPointerY = event.clientY;
  lastPointerTime = now;
  const delta = event.clientY - dragY;
  if (Math.abs(delta) > 4) dragged = true;
  moveTo(dragStart + delta);
}
function pointerUp(event: PointerEvent) {
  if (!dragging) return;
  dragging = false;
  const element = event.currentTarget as HTMLElement;
  if (element.hasPointerCapture(event.pointerId)) element.releasePointerCapture(event.pointerId);
  const distance = event.clientY - dragY;
  const now = performance.now();
  const quickSwipe = Math.abs(distance) >= 12 && now - gestureStartTime < 350;
  const freshVelocity = now - lastPointerTime < 100 ? velocity : 0;
  if (event.type !== 'pointercancel' && dragged && (quickSwipe || Math.abs(freshVelocity) > 0.2)) {
    const direction = Math.sign(quickSwipe ? distance : freshVelocity);
    const travel = Math.min(
      viewportHeight.value * 0.9,
      Math.max(viewportHeight.value * 0.5, Math.abs(freshVelocity) * 280),
    );
    glideTo(current + direction * travel);
  }
}
function wheel(event: WheelEvent) {
  if (event.ctrlKey || (event.target instanceof Element && event.target.closest('details[open]')))
    return;
  event.preventDefault();
  const delta =
    event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? viewportHeight.value : 1);
  glideTo(target - delta * 1.5, 180);
}
function keyboard(event: KeyboardEvent) {
  if (interactive(event.target)) return;
  const steps: Record<string, number> = {
    ArrowDown: -48,
    ArrowUp: 48,
    PageDown: -viewportHeight.value * 0.7,
    PageUp: viewportHeight.value * 0.7,
    ' ': -viewportHeight.value * 0.7,
  };
  if (event.key in steps) {
    event.preventDefault();
    moveTo(target + steps[event.key]!);
  } else if (event.key === 'Home' || event.key === 'End') {
    event.preventDefault();
    moveTo(event.key === 'Home' ? maximum : minimum);
  }
}
function toggle() {
  if (dragged) {
    dragged = false;
    return;
  }
  moveTo(Math.abs(target - lower) < 12 ? minimum : lower);
}
onMounted(async () => {
  if (props.item.item_type === 'certificate') return;
  previous = document.activeElement as HTMLElement | null;
  previousOverflow = document.body.style.overflow;
  document.body.style.overflow = 'hidden';
  await nextTick();
  viewer.value?.showModal();
  viewer.value?.focus({ preventScroll: true });
  measure();
  observer = new ResizeObserver(measure);
  for (const element of [viewer.value, content.value, heading.value])
    if (element) observer.observe(element);
  viewer.value?.addEventListener('wheel', wheel, { passive: false });
});
onBeforeUnmount(() => {
  stopAnimation();
  observer?.disconnect();
  viewer.value?.removeEventListener('wheel', wheel);
  if (props.item.item_type !== 'certificate') document.body.style.overflow = previousOverflow;
  previous?.focus({ preventScroll: true });
});
</script>
<template>
  <CertificateDetail
    v-if="item.item_type === 'certificate'"
    :item="item"
    :own-profile="ownProfile"
    :busy="busy"
    @close="emit('close')"
    @edit="emit('edit', item)"
    @delete="emit('delete', item)"
    @reserve="emit('reserve', item)"
    @priority="emit('priority', item)"
  />
  <Teleport to="body">
    <dialog
      v-if="item.item_type !== 'certificate'"
      ref="viewer"
      class="fixed inset-0 m-0 h-dvh max-h-none w-full max-w-none overflow-hidden border-0 bg-paper p-0 text-ink dark:bg-[#202823] dark:text-[#ede9df]"
      aria-labelledby="wish-viewer-title"
      tabindex="-1"
      @cancel.prevent="emit('close')"
      @keydown="keyboard"
    >
      <article
        class="relative h-full touch-none overflow-hidden"
        @pointerdown="pointerDown"
        @pointermove="pointerMove"
        @pointerup="pointerUp"
        @pointercancel="pointerUp"
      >
        <div class="absolute inset-x-0 top-0" :style="{ height: `${photoHeight}px` }">
          <img
            v-if="hasPhoto"
            :src="imageUrl(item.image_id!)"
            :alt="itemTitle(item)"
            class="block h-auto w-full max-w-none select-none"
            draggable="false"
            @load="loaded"
            @error="failed"
          />
          <div
            v-else
            class="grid h-full place-items-center bg-[#c7cdb6] font-editorial text-[32px] leading-tight text-forest"
            aria-hidden="true"
          >
            Однажды<br /><em>сбудется.</em>
          </div>
        </div>
        <div
          ref="sheet"
          class="absolute inset-x-0 top-0 z-10 rounded-t-[18px] bg-paper dark:bg-[#202823]"
        >
          <div
            ref="content"
            class="bg-paper px-4 pb-[max(24px,env(safe-area-inset-bottom))] dark:bg-[#202823]"
          >
            <div
              class="relative flex h-9 shrink-0 touch-none items-center justify-center bg-paper dark:bg-[#202823]"
              @pointerdown.stop="pointerDown"
              @click="toggle"
              data-sheet-handle
              role="button"
              tabindex="0"
              aria-label="Развернуть или опустить описание"
              @keydown.enter.prevent="toggle"
              @keydown.space.prevent="toggle"
            >
              <span class="h-1 w-9 rounded-full bg-[#b0b8a7]" />
            </div>
            <div class="pt-1 pb-5">
              <h1
                id="wish-viewer-title"
                ref="heading"
                class="mb-3 min-h-[2.5em] font-editorial text-[clamp(23px,5vw,30px)] leading-tight tracking-tight break-words"
              >
                {{ itemTitle(item) }}
              </h1>
              <p
                v-if="item.list_type === 'surprise' && item.author_name?.trim()"
                class="mb-3 text-xs text-muted"
              >
                Сюрприз от {{ item.author_name }}
              </p>
              <p v-if="item.list_type === 'surprise'" class="mb-3 text-xs text-muted">
                {{ item.surprise_visibility === 'private' ? 'Только мне' : 'Всем друзьям' }}
              </p>
              <p
                v-if="!ownProfile && item.reservation"
                class="mb-3 text-sm text-forest dark:text-sand"
                role="status"
              >
                {{
                  item.reservation.reserved_by_me
                    ? 'Вы забронировали этот подарок'
                    : `Забронировано: ${item.reservation.reserver_name}`
                }}
              </p>
              <button
                v-if="!ownProfile && item.can_reserve"
                type="button"
                class="button secondary mb-3"
                :disabled="busy"
                @click="emit('reserve', item)"
              >
                {{
                  busy
                    ? 'Сохраняем…'
                    : item.reservation?.reserved_by_me
                      ? 'Снять бронь'
                      : 'Забронировать подарок'
                }}
              </button>
              <button
                v-if="ownProfile && item.list_type === 'wishlist' && !item.archived_at"
                type="button"
                class="button secondary mb-3 gap-2"
                :aria-pressed="Boolean(item.most_wanted)"
                :disabled="busy"
                @click="emit('priority', item)"
              >
                <Heart :size="18" :fill="item.most_wanted ? 'currentColor' : 'none'" />Очень хочу
              </button>
              <p
                v-else-if="item.most_wanted"
                class="mb-3 flex items-center gap-2 text-sm text-forest dark:text-sand"
              >
                <Heart :size="18" fill="currentColor" />Очень хочу
              </p>
              <p v-if="hasPrice(item)" class="text-sm text-muted">{{ formatPrice(item) }}</p>
              <p
                v-if="item.description?.trim()"
                class="mt-5 text-sm leading-relaxed whitespace-pre-wrap break-words text-muted"
              >
                {{ item.description }}
              </p>
            </div>
            <div v-if="item.url?.trim()" class="grid gap-2 border-t border-line pt-4">
              <button
                v-if="item.url?.trim()"
                type="button"
                class="button primary justify-between"
                @click="openExternal(item.url)"
              >
                <span>Открыть ссылку</span><ArrowUpRight :size="19" />
              </button>
            </div>
          </div>
        </div>
      </article>
      <div
        class="absolute top-[max(12px,env(safe-area-inset-top))] right-3 z-30 flex items-center gap-2"
      >
        <details v-if="item.can_manage" class="relative">
          <summary
            class="icon-button list-none [&::-webkit-details-marker]:hidden"
            aria-label="Управление желанием"
          >
            <MoreHorizontal :size="20" />
          </summary>
          <div
            class="absolute top-12 right-0 grid w-48 gap-1 rounded-md border border-line bg-paper p-2 shadow-lg dark:bg-[#2b362e] [&_button]:flex [&_button]:min-h-10 [&_button]:items-center [&_button]:gap-2 [&_button]:rounded [&_button]:px-2 [&_button]:text-left [&_button]:text-xs [&_button:hover]:bg-forest/10"
          >
            <button v-if="!item.archived_at" :disabled="busy" @click="emit('edit', item)">
              <Pencil :size="16" />Редактировать
            </button>
            <button :disabled="busy" @click="emit('archive', item)">
              <ArchiveRestore v-if="item.archived_at" :size="16" /><ArchiveX v-else :size="16" />{{
                item.archived_at ? 'Вернуть из архива' : 'В архив'
              }}
            </button>
            <button class="text-[#a04432]" :disabled="busy" @click="emit('delete', item)">
              <Trash2 :size="16" />Удалить
            </button>
          </div>
        </details>
        <button class="icon-button" type="button" aria-label="Закрыть" @click="emit('close')">
          <X :size="20" />
        </button>
      </div>
    </dialog>
  </Teleport>
</template>
