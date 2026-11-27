<script setup lang="ts">
import {computed, nextTick, onBeforeUnmount, onMounted, ref, watch} from 'vue';
import {
  ArchiveRestore,
  ArchiveX,
  ArrowLeft,
  ArrowUpRight,
  Heart,
  LockKeyhole,
  MoreHorizontal,
  Pencil,
  Trash2,
} from 'lucide-vue-next';
import {
  formatPrice,
  hasPrice,
  imageUrl,
  itemTitle,
  type Item
} from '../shared/api';
import {lockVerticalSwipes, openExternal} from '../integrations/telegram';
import CertificateDetail from './CertificateDetail.vue';
import type {CardOrigin} from '../shared/cardTransition';
import {theme} from '../shared/theme';
import {isTicketGift} from '../shared/ticketServices';
import {AppButton} from './ui';

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
let releaseSwipes: (() => void) | undefined;

// The viewer has an explicit close button; Escape and swipes must not dismiss it.
function keepOpen() {
}

const isOpen = ref(false)
const rootRef = ref<HTMLElement | null>(null)

function closeMenu() {
  isOpen.value = false
}

function toggleMenu() {
  if (props.busy) return
  isOpen.value = !isOpen.value
}

function handleOutsidePointerDown(event: PointerEvent) {
  if (!isOpen.value) return
  const target = event.target as Node | null
  if (rootRef.value && target && !rootRef.value.contains(target)) {
    closeMenu()
  }
}

watch(
    () => props.item.can_manage,
    (canManage) => {
      if (!canManage) closeMenu()
    },
)

const sheet = ref<HTMLElement>();
const content = ref<HTMLElement>();
const heading = ref<HTMLElement>();
const imageFailed = ref(false);
const photoRatio = ref(props.origin?.photoRatio || 0);
const photoHeight = ref(0);
const viewportHeight = ref(0);
const hasPhoto = computed(() =>
    Boolean(props.item.item_type !== 'certificate' && props.item.image_id && !imageFailed.value),
);
const noteHeroTone = computed(() => {
  const hash = Array.from(props.item.id).reduce(
    (value, char) => (value * 31 + char.charCodeAt(0)) >>> 0,
    0,
  );
  return hash % 4;
});
const noteHeroStyle = computed(() => {
  const dark = theme.value === 'dark';
  const tones = dark
    ? [
        {
          wash: 'linear-gradient(160deg, #4a8ea0 0%, #2f6576 45%, #17323e 100%)',
          glow: 'rgb(150 220 230 / 48%)',
          flare: 'rgb(230 200 130 / 36%)',
          orb: 'rgb(90 160 150 / 28%)',
          spot: '12% 8%',
          flareAt: '88% 16%',
          orbAt: '70% 85%',
        },
        {
          wash: 'linear-gradient(152deg, #3f6f98 0%, #2a5078 45%, #152438 100%)',
          glow: 'rgb(140 200 235 / 40%)',
          flare: 'rgb(120 190 180 / 28%)',
          orb: 'rgb(210 170 100 / 22%)',
          spot: '92% 4%',
          flareAt: '18% 78%',
          orbAt: '40% 20%',
        },
        {
          wash: 'linear-gradient(148deg, #5a8a68 0%, #3a6a58 45%, #1a322c 100%)',
          glow: 'rgb(170 220 150 / 36%)',
          flare: 'rgb(220 200 130 / 26%)',
          orb: 'rgb(100 170 160 / 24%)',
          spot: '100% 10%',
          flareAt: '14% 14%',
          orbAt: '55% 90%',
        },
        {
          wash: 'linear-gradient(156deg, #9a7a48 0%, #6a6048 42%, #2a3e4c 100%)',
          glow: 'rgb(230 200 140 / 34%)',
          flare: 'rgb(120 180 200 / 24%)',
          orb: 'rgb(200 150 90 / 20%)',
          spot: '82% 10%',
          flareAt: '10% 88%',
          orbAt: '30% 35%',
        },
      ]
    : [
        {
          wash: 'linear-gradient(160deg, #8fd0dc 0%, #4f97a8 38%, #2a6478 72%, #1b4554 100%)',
          glow: 'rgb(210 245 250 / 78%)',
          flare: 'rgb(255 236 190 / 70%)',
          orb: 'rgb(120 190 170 / 42%)',
          spot: '12% 8%',
          flareAt: '88% 16%',
          orbAt: '70% 85%',
        },
        {
          wash: 'linear-gradient(152deg, #7eb8e8 0%, #4a7eb8 34%, #2f5688 68%, #1c3558 100%)',
          glow: 'rgb(220 240 255 / 72%)',
          flare: 'rgb(180 230 220 / 55%)',
          orb: 'rgb(255 220 170 / 38%)',
          spot: '92% 4%',
          flareAt: '18% 78%',
          orbAt: '40% 20%',
        },
        {
          wash: 'linear-gradient(148deg, #b7d6a4 0%, #6fa87a 36%, #3f7a68 70%, #25524c 100%)',
          glow: 'rgb(235 250 220 / 70%)',
          flare: 'rgb(255 242 205 / 62%)',
          orb: 'rgb(140 200 190 / 40%)',
          spot: '100% 10%',
          flareAt: '14% 14%',
          orbAt: '55% 90%',
        },
        {
          wash: 'linear-gradient(156deg, #e0c48a 0%, #b8925c 32%, #6e7a68 66%, #3a5564 100%)',
          glow: 'rgb(255 240 205 / 68%)',
          flare: 'rgb(170 215 230 / 52%)',
          orb: 'rgb(255 210 150 / 35%)',
          spot: '82% 10%',
          flareAt: '10% 88%',
          orbAt: '30% 35%',
        },
      ];
  const tone = tones[noteHeroTone.value]!;
  return {
    background: [
      `radial-gradient(ellipse 80% 55% at ${tone.flareAt}, ${tone.flare}, transparent 55%)`,
      `radial-gradient(ellipse 70% 60% at ${tone.spot}, ${tone.glow}, transparent 60%)`,
      `radial-gradient(ellipse 50% 40% at ${tone.orbAt}, ${tone.orb}, transparent 62%)`,
      tone.wash,
    ].join(', '),
  };
});
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
let scrollingContent = false;
let contentScrollStart = 0;
let contentScroll: HTMLElement | null = null;
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
    sheet.value.style.transform = `translate3d(0, ${current}px, 0)`;
    // Keep the blurred surface the same size during a drag to avoid rerasterizing
    // it on every frame. Only the inner scroll viewport needs to resize.
    sheet.value.style.height = `${Math.max(0, viewportHeight.value - minimum)}px`;
    if (content.value)
      content.value.style.height = `${Math.max(0, viewportHeight.value - current - 36)}px`;
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
              : Math.min(210, Math.max(156, height * 0.26));
  // Keep the complete title visible, including the handle and category above it.
  const peek = heading.value && content.value
      ? heading.value.getBoundingClientRect().bottom - content.value.getBoundingClientRect().top + 56
      : 160;
  const titleLimit = Math.max(0, height - peek);
  const preferred = hasPhoto.value
      ? Math.min(photoHeight.value, Math.max(0, Math.min(height * 0.6, height - peek)))
      : Math.min(photoHeight.value, titleLimit);
  // Keep the rounded sheet corners over the image rather than exposing its edge.
  lower = Math.min(Math.max(0, photoHeight.value - 36), titleLimit);
  maximum = Math.max(0, lower);
  minimum = Math.min(height * 0.1, maximum);
  base = clamp(preferred);
  // A ResizeObserver notification must not finish or restart an active gesture.
  if (!initialized || !positionedByUser) {
    current = target = base;
  } else {
    current = clamp(current);
    target = clamp(target);
  }
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
  // Only gestures starting on the description scroll the content; the title,
  // price and sheet background drag the sheet just like the photo does.
  contentScroll = event.target instanceof Element && event.target.closest('.wish-info-description')
      ? content.value || null
      : null;
  scrollingContent = Boolean(contentScroll && contentScroll.scrollHeight > contentScroll.clientHeight && current <= minimum + 1);
  contentScrollStart = contentScroll?.scrollTop || 0;
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
  if (scrollingContent && contentScroll) {
    const scroll = contentScrollStart - delta;
    contentScroll.scrollTop = Math.max(0, scroll);
    if (scroll < 0) moveTo(minimum - scroll);
    return;
  }
  if (Math.abs(delta) > 4) dragged = true;
  moveTo(dragStart + delta);
}

function pointerUp(event: PointerEvent) {
  if (!dragging) return;
  dragging = false;
  const element = event.currentTarget as HTMLElement;
  if (element.hasPointerCapture(event.pointerId)) element.releasePointerCapture(event.pointerId);
  if (scrollingContent) {
    scrollingContent = false;
    return;
  }
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
  const delta =
      event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? viewportHeight.value : 1);
  const scroll = event.target instanceof Element && event.target.closest('.wish-info-description')
      ? content.value
      : null;
  if (scroll && (current <= minimum + 1 || scroll.scrollTop > 0)) {
    if (delta > 0 || scroll.scrollTop > 0) {
      event.preventDefault();
      scroll.scrollTop += delta;
      return;
    }
  }
  event.preventDefault();
  // Wheel input is already paced by the browser; don't restart an easing on each tick.
  moveTo(current - delta);
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
  glideTo(Math.abs(target - maximum) < 12 ? minimum : maximum);
}

onMounted(async () => {
  if (props.item.item_type === 'certificate') return;
  previous = document.activeElement as HTMLElement | null;
  previousOverflow = document.body.style.overflow;
  document.body.style.overflow = 'hidden';
  releaseSwipes = lockVerticalSwipes();
  await nextTick();
  viewer.value?.showModal();
  viewer.value?.focus({preventScroll: true});
  measure();
  observer = new ResizeObserver(measure);
  for (const element of [viewer.value, heading.value])
    if (element) observer.observe(element);
  viewer.value?.addEventListener('wheel', wheel, {passive: false});
});
onBeforeUnmount(() => {
  stopAnimation();
  observer?.disconnect();
  viewer.value?.removeEventListener('wheel', wheel);
  releaseSwipes?.();
  if (props.item.item_type !== 'certificate') document.body.style.overflow = previousOverflow;
  previous?.focus({preventScroll: true});
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
        class="fixed inset-0 m-0 h-dvh max-h-none w-full max-w-none overflow-hidden border-0 bg-paper p-0 text-ink"
        aria-labelledby="wish-viewer-title"
        tabindex="-1"
        @cancel.prevent="keepOpen"
        @keydown="keyboard"
    >
      <article
          class="relative h-full touch-none overflow-hidden"
          @pointerdown="pointerDown"
          @pointermove="pointerMove"
          @pointerup="pointerUp"
          @pointercancel="pointerUp"
      >
        <div class="absolute inset-x-0 top-0"
             :style="{ height: `${photoHeight}px` }">
          <img
              v-if="hasPhoto"
              :src="imageUrl(item.image_id!, item.image_is_icon ? undefined : 800)"
              :alt="itemTitle(item)"
              class="block h-auto w-full max-w-none select-none"
              decoding="async"
              fetchpriority="high"
              draggable="false"
              @load="loaded"
              @error="failed"
          />
          <div
              v-else
              class="wish-note-hero"
              :style="noteHeroStyle"
              aria-hidden="true"
          />
        </div>
        <div
            ref="sheet"
            class="wish-info-sheet absolute inset-x-0 top-0 z-10"
        >
          <div
              class="wish-info-handle relative flex h-9 shrink-0 touch-none items-center justify-center"
              @pointerdown.stop="pointerDown"
              @click="toggle"
              data-sheet-handle
              role="button"
              tabindex="0"
              aria-label="Развернуть или опустить описание"
              @keydown.enter.prevent="toggle"
              @keydown.space.prevent="toggle"
          >
            <span class="h-1 w-9 rounded-full bg-current opacity-30"/>
          </div>
          <div
              ref="content"
              class="wish-info-content"
          >
            <div class="wish-info-body">
              <p class="wish-info-kind">{{
                  item.list_type === 'surprise'
                    ? 'Сюрприз'
                    : item.item_type === 'idea'
                      ? 'Идея для подарка'
                      : isTicketGift(item)
                        ? 'Билет'
                        : 'В списке желаний'
                }}</p>
              <h1
                  id="wish-viewer-title"
                  ref="heading"
                  class="wish-info-title"
              >
                {{ itemTitle(item) }}
                <LockKeyhole
                    v-if="item.list_type === 'surprise' && item.surprise_visibility === 'private'"
                    :size="15" class="inline-block align-middle text-muted"
                    aria-label="Только мне"/>
              </h1>
              <p
                  v-if="!ownProfile && item.reservation && !item.reservation.reserved_by_me"
                  class="mb-3 text-sm text-forest dark:text-sand"
                  role="status"
              >
                Уже забронировано
              </p>
              <AppButton
                  v-if="!item.archived_at && !ownProfile && item.can_reserve"
                  variant="glass-secondary"
                  class="mb-3"
                  :loading="busy"
                  loading-text="Сохраняем…"
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
              </AppButton>
              <div v-if="hasPrice(item) || item.url?.trim()"
                   class="wish-info-purchase"
                   :class="{ 'wish-info-purchase-single': !hasPrice(item) || !item.url?.trim() }">
                <p v-if="hasPrice(item) && !item.archived_at" class="wish-info-price">
                  {{ formatPrice(item) }}</p>
                <AppButton
                    v-if="item.url?.trim()"
                    :variant="hasPrice(item) && !item.archived_at ? 'glass-icon' : 'glass'"
                    class="wish-info-link"
                    label="Открыть ссылку"
                    @click="openExternal(item.url)"
                >
                  <span v-if="!hasPrice(item) || item.archived_at">Открыть ссылку</span>
                  <ArrowUpRight :size="19"/>
                </AppButton>
              </div>
              <AppButton
                  v-if="!item.archived_at && ownProfile && item.list_type === 'wishlist'"
                  variant="custom"
                  class="most-wanted-toggle wish-info-priority"
                  :class="{ selected: item.most_wanted }"
                  :pressed="Boolean(item.most_wanted)"
                  :disabled="busy"
                  @click="emit('priority', item)"
              >
                <Heart :size="18"
                       :fill="item.most_wanted ? 'currentColor' : 'none'"/>
                Очень хочу
              </AppButton>
              <p
                  v-else-if="!item.archived_at && item.most_wanted"
                  class="mb-3 flex items-center gap-2 text-sm text-forest dark:text-sand"
              >
                <Heart :size="18" fill="currentColor"/>
                Очень хочу
              </p>
              <p
                  v-if="item.description?.trim()"
                  class="wish-info-description"
              >
                {{ item.description }}
              </p>
            </div>
          </div>
        </div>
      </article>
      <AppButton
          variant="glass-icon"
          class="absolute top-[max(12px,env(safe-area-inset-top))] left-3 z-30"
          label="Назад"
          @click="emit('close')"
      >
        <ArrowLeft :size="20"/>
      </AppButton>
      <div
          class="absolute top-[max(12px,env(safe-area-inset-top))] right-3 z-30 flex items-center gap-2"
      >
        <div v-if="item.can_manage && !item.archived_at" ref="rootRef" class="relative inline-flex">
          <AppButton
              type="button"
              variant="glass-icon"
              label="Управление желанием"
              :aria-expanded="isOpen"
              aria-haspopup="menu"
              :disabled="busy"
              @click.stop="toggleMenu"
          >
            <MoreHorizontal :size="20"/>
          </AppButton>

          <Transition
              enter-active-class="transition duration-200 ease-out"
              enter-from-class="opacity-0 -translate-y-2 scale-95"
              enter-to-class="opacity-100 translate-y-0 scale-100"
              leave-active-class="transition duration-150 ease-in"
              leave-from-class="opacity-100 translate-y-0 scale-100"
              leave-to-class="opacity-0 -translate-y-2 scale-95"
          >
            <div
                v-if="isOpen"
                role="menu"
                class="origin-top absolute top-full right-0 z-20 mt-2 flex flex-col items-center gap-1 rounded-full border border-line py-1.5 shadow-lg backdrop-blur-md"
            >
              <AppButton
                  variant="glass-icon"
                  :disabled="busy"
                  label="Редактировать"
                  title="Редактировать"
                  @click="emit('edit', item)"
              >
                <Pencil :size="18"/>
              </AppButton>

              <AppButton
                  variant="glass-icon"
                  :disabled="busy"
                  label="В архив"
                  title="В архив"
                  @click="emit('archive', item)"
              >
                <ArchiveX :size="18"/>
              </AppButton>

              <AppButton
                  variant="glass-icon"
                  class="text-[#a04432] hover:bg-[#a04432]/15"
                  :disabled="busy"
                  label="Удалить"
                  title="Удалить"
                  @click="emit('delete', item)"
              >
                <Trash2 :size="18"/>
              </AppButton>
            </div>
          </Transition>
        </div>
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.wish-info-sheet {
  will-change: transform;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 22%);
  border-bottom: 0;
  border-radius: 36px 36px 0 0;
  background: color-mix(in srgb, var(--paper) 50%, transparent);
  color: var(--ink);
  backdrop-filter: blur(12px);
  box-shadow: 0 -12px 48px rgb(22 42 30 / 10%);
}

.wish-info-content {
  box-sizing: border-box;
  height: 100%;
  /* Scrolling is routed through pointer/wheel handlers. Avoid a native touch
     scroll layer competing with the sheet drag on the first gesture. Unlike
     overflow: clip, hidden still permits our scrollTop updates. */
  overflow-y: hidden;
  /* This is a scroll container, so the article's touch-action does not govern
     gestures inside it. Let our pointer handlers route drag vs description. */
  touch-action: none;
  user-select: none;
  overscroll-behavior: contain;
  scrollbar-width: none;
  padding: 0 20px max(28px, env(safe-area-inset-bottom));
}

.wish-note-hero {
  height: 100%;
  width: 100%;
  background-size: cover;
  background-position: center;
}

.wish-info-handle {
  cursor: grab;
}

.wish-info-content::-webkit-scrollbar {
  display: none;
}

.wish-info-handle:active {
  cursor: grabbing;
}

.wish-info-handle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -5px;
}

.wish-info-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 0 24px;
  text-align: center;
}

.wish-info-body > :not(.wish-info-description) {
  flex-shrink: 0;
}

.wish-info-sheet :deep(.glass-button) {
  color: var(--ink);
  border-color: color-mix(in srgb, var(--ink) 18%, transparent);
  background: color-mix(in srgb, var(--paper) 25%, transparent);
}

.wish-info-kind {
  margin: 0 0 10px;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: .04em;
}

.wish-info-title {
  max-width: 620px;
  width: 100%;
  margin: 0 auto 22px;
  font: 400 clamp(25px, 5vw, 34px) / 1.15 var(--font-editorial);
  letter-spacing: -.035em;
  overflow-wrap: anywhere;
  text-wrap: pretty;
}

.wish-info-price {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  text-align: left;
  font-size: 18px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.wish-info-description {
  width: 100%;
  margin: 26px 0 0;
  padding-top: 22px;
  border-top: 1px solid color-mix(in srgb, var(--ink) 15%, transparent);
  font-size: 14px;
  line-height: 1.75;
  text-align: left;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.wish-info-purchase {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 4px 0 18px;
}

.wish-info-link {
  flex-shrink: 0;
  margin-left: auto;
  border-radius: 999px;
}

.wish-info-link.button {
  min-height: 40px;
  padding: 8px 12px;
  font-size: 12px;
}

.wish-info-author {
  width: 28px;
  height: 28px;
  margin: -10px 0 14px;
  font-size: 10px;
}

.wish-info-priority {
  margin: 0 0 4px;
}

.wish-info-purchase-single {
  justify-content: center;
}

.wish-info-purchase-single .wish-info-link {
  margin-left: 0;
}

@media (max-width: 360px) {
  .wish-info-content {
    padding-inline: 20px;
  }
}
</style>
