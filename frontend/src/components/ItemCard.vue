<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Archive, ArrowUpRight, Gift, Heart, Lightbulb, Star, Store, Ticket } from 'lucide-vue-next';
import { imageUrl, itemTitle, type Item } from '../shared/api';
import type { CardOrigin } from '../shared/cardTransition';
import WishImage from './WishImage.vue';
import { itemPalette } from '../shared/itemPalette';
import { certificateTitle } from '../shared/certificateTitle';
import { certificateIcon } from '../shared/certificateStores';
import { linkBookmark } from '../shared/linkBookmark';
import { ticketService } from '../shared/ticketServices';
import { AppButton, Avatar } from './ui';

const props = defineProps<{ item: Item; index: number }>();
const emit = defineEmits<{ open: [item: Item, origin: CardOrigin] }>();
const plasticCard = computed(() => props.item.item_type === 'certificate');
const ticketDesk = computed(() =>
  props.item.item_type === 'gift' || props.item.item_type === 'ticket'
    ? ticketService(props.item.url)
    : undefined,
);
const ticketCard = computed(
  () => props.item.item_type === 'ticket' || Boolean(ticketDesk.value),
);
const imageFailed = ref(false);
const bookmarkLogoFailed = ref(false);
const hasPhoto = computed(() => Boolean(props.item.image_id && !imageFailed.value));
const hasProductPhoto = computed(
  () => Boolean(props.item.image_id && !props.item.image_is_icon && !imageFailed.value),
);
const bookmark = computed(() =>
  !ticketCard.value &&
  props.item.item_type === 'gift' &&
  props.item.url?.trim() &&
  !props.item.title?.trim() &&
  !hasProductPhoto.value
    ? linkBookmark(props.item.url)
    : null,
);
const linkBookmarkCard = computed(() => Boolean(bookmark.value));
const title = computed(
  () => props.item.title?.trim() || (props.item.url?.trim() ? itemTitle(props.item) : ''),
);
const ticketTitle = computed(
  () => props.item.title?.trim() || ticketDesk.value?.name || (ticketCard.value ? 'Билет' : ''),
);
const certificateText = computed(() => certificateTitle(itemTitle(props.item)));
const reservationLabel = computed(() => {
  const reservation = props.item.reservation;
  if (!reservation) return '';
  return reservation.reserved_by_me ? 'Вы забронировали' : 'Уже забронировано';
});
const cardHash = computed(() =>
  Array.from(props.item.id).reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, 0),
);
const surfaceStyle = computed(() => itemPalette(props.item.id));
const iconUrl = computed(() => certificateIcon(props.item));
const bookmarkIcon = computed(
  () =>
    bookmark.value?.icon ||
    (props.item.image_id ? imageUrl(props.item.image_id, props.item.image_is_icon ? undefined : 400) : null),
);
const certificateLogoFailed = ref(false);
watch(
  () => `${iconUrl.value || ''}|${props.item.image_id || ''}`,
  () => {
    certificateLogoFailed.value = false;
  },
  { immediate: true },
);
watch(
  () => `${bookmarkIcon.value || ''}|${props.item.id}`,
  () => {
    bookmarkLogoFailed.value = false;
  },
  { immediate: true },
);
const photoLayout = ref<'landscape' | 'portrait' | 'square'>('square');
const photoRatio = ref('1 / 1');
const cardStyle = computed(() => {
  const [width, height] = photoRatio.value.split('/').map(Number);
  return {
    ...surfaceStyle.value,
    '--tile-photo-ratio': String(width! / height!),
    '--idea-gradient': `var(--idea-gradient-${cardHash.value % 4})`,
    '--idea-ink': `var(--idea-ink-${cardHash.value % 4}, var(--ink))`,
    '--card-outline': `var(--card-outline-${cardHash.value % 4}, transparent)`,
    '--ticket-accent': ticketDesk.value?.accent || '#1f3b57',
  };
});

function open(event: MouseEvent) {
  const card = event.currentTarget as HTMLElement;
  const bounds = card.getBoundingClientRect();
  const image = card.querySelector<HTMLImageElement>(
    '.card-art img:not(.site-icon), .ticket-art img:not(.site-icon)',
  );
  const photo = image?.complete && image.naturalWidth ? image.getBoundingClientRect() : undefined;
  const [width, height] = photoRatio.value.split('/').map(Number);
  emit('open', props.item, {
    left: bounds.left,
    top: bounds.top,
    width: bounds.width,
    height: bounds.height,
    photoRatio:
      image?.naturalWidth && image.naturalHeight
        ? image.naturalWidth / image.naturalHeight
        : props.item.image_id && !props.item.image_is_icon && !plasticCard.value
          ? width! / height!
          : undefined,
    background: getComputedStyle(card).backgroundColor,
    backgroundImage: getComputedStyle(card).backgroundImage,
    photo:
      photo && image
        ? {
            left: photo.left,
            top: photo.top,
            width: photo.width,
            height: photo.height,
            src: image.currentSrc || image.src,
          }
        : undefined,
  });
}

watch(
  () => props.item.image_id,
  () => {
    photoLayout.value = 'square';
    photoRatio.value = '1 / 1';
    imageFailed.value = false;
  },
);

function photoLoaded(event: Event) {
  const image = event.target as HTMLImageElement;
  if (!image.naturalWidth || !image.naturalHeight) return;
  if (props.item.image_is_icon || (image.naturalWidth <= 96 && image.naturalHeight <= 96)) {
    photoRatio.value = '1 / 1';
    return;
  }
  photoRatio.value = `${image.naturalWidth} / ${image.naturalHeight}`;
  photoLayout.value =
    image.naturalWidth > image.naturalHeight
      ? 'landscape'
      : image.naturalHeight > image.naturalWidth
        ? 'portrait'
        : 'square';
}
</script>

<template>
  <article
    class="gift-card collection-tile relative min-w-0"
    :class="[
      {
        archived: item.archived_at,
        'without-photo': !hasPhoto && !linkBookmarkCard && !ticketCard,
        'certificate-card': plasticCard,
        'ticket-card': ticketCard,
        'link-bookmark-card': linkBookmarkCard,
        'idea-card': item.item_type === 'idea',
        'most-wanted-card': item.most_wanted && !plasticCard && !linkBookmarkCard && !ticketCard,
      },
      `wish-note-${cardHash % 4}`,
    ]"
    :style="cardStyle"
  >
    <AppButton
      v-if="plasticCard"
      variant="custom"
      class="card-open certificate-face"
      :label="`Открыть: ${itemTitle(item)}`"
      @click="open"
    >
      <span
        v-if="(iconUrl || item.image_id) && !certificateLogoFailed"
        class="certificate-logo"
        ><img
          :src="iconUrl || imageUrl(item.image_id!, item.image_is_icon ? undefined : 400)"
          class="site-icon"
          alt=""
          loading="lazy"
          @error="certificateLogoFailed = true"
      /></span>
      <Store v-else class="shop-symbol" :size="20" :stroke-width="1.2" />
      <div class="certificate-copy">
        <h3>{{ certificateText.name }}</h3>
        <span v-if="item.archived_at">В архиве</span>
        <span v-else-if="item.reservation && !item.reservation.reserved_by_me">{{
          reservationLabel
        }}</span>
      </div>
      <ArrowUpRight class="certificate-arrow" :size="16" />
    </AppButton>
    <AppButton
      v-else-if="ticketCard"
      variant="custom"
      class="card-open ticket-face"
      :class="{ 'ticket-with-photo': hasPhoto }"
      :label="`Открыть: ${ticketTitle || 'билет'}`"
      @click="open"
    >
      <span
        v-if="!item.archived_at"
        class="wish-type-icon"
        aria-label="Билет"
      >
        <Ticket :size="13" :stroke-width="1.8" />
      </span>
      <div v-if="hasPhoto" class="ticket-art" aria-hidden="true">
        <WishImage
          :src="imageUrl(item.image_id!, item.image_is_icon ? undefined : 400)"
          :is-icon="item.image_is_icon"
          alt=""
          :loading="index < 4 ? 'eager' : 'lazy'"
          :fetchpriority="index < 2 ? 'high' : 'auto'"
          @load="photoLoaded"
          @error="imageFailed = true"
        />
      </div>
      <div class="ticket-copy">
        <h3 v-if="ticketTitle" class="ticket-face-title">{{ ticketTitle }}</h3>
        <span
          v-if="item.archived_at"
          class="wish-status wish-archive"
          ><Archive :size="12" aria-hidden="true" />В архиве</span
        >
        <span
          v-else-if="item.reservation && !item.reservation.reserved_by_me"
          class="wish-status wish-reservation"
          >{{ reservationLabel }}</span
        >
      </div>
      <span class="ticket-accent" aria-hidden="true" />
    </AppButton>
    <AppButton
      v-else-if="bookmark"
      variant="custom"
      class="card-open link-bookmark"
      :label="`Открыть: ${bookmark.name}`"
      @click="open"
    >
      <span class="link-bookmark-spine" aria-hidden="true">
        <img
          v-if="bookmarkIcon && !bookmarkLogoFailed"
          :src="bookmarkIcon"
          class="site-icon"
          alt=""
          loading="lazy"
          @error="bookmarkLogoFailed = true"
        />
        <span v-else>{{ bookmark.mark }}</span>
      </span>
      <div class="link-bookmark-copy">
        <h3>{{ bookmark.name }}</h3>
        <span class="link-bookmark-hint">{{ bookmark.hint }}</span>
        <span v-if="item.archived_at" class="link-bookmark-meta">В архиве</span>
        <span
          v-else-if="item.reservation && !item.reservation.reserved_by_me"
          class="link-bookmark-meta"
          >{{ reservationLabel }}</span
        >
      </div>
      <ArrowUpRight class="link-bookmark-arrow" :size="15" aria-hidden="true" />
    </AppButton>
    <AppButton
      v-else
      variant="custom"
      class="card-open wish-poster"
      :class="{ 'tile-photo': hasPhoto }"
      :label="`Открыть: ${itemTitle(item)}`"
      @click="open"
    >
      <Avatar
        v-if="!item.archived_at && item.list_type === 'surprise' && item.surprise_visibility === 'friends'"
        :name="item.author_name"
        :user-id="item.author_id"
        class="wish-author-avatar"
        :title="item.author_name"
        lazy
      />
      <span v-else-if="!item.archived_at" class="wish-type-icon" :aria-label="item.item_type === 'idea' ? 'Идея' : 'Подарок'">
        <Lightbulb v-if="item.item_type === 'idea'" :size="13" />
        <Gift v-else :size="13" />
      </span>
      <span
        v-if="item.archived_at"
        class="wish-status wish-archive"
        ><Archive :size="12" aria-hidden="true" />В архиве</span
      >
      <div
        v-if="hasPhoto"
        class="card-art tile-media art-photo"
      >
        <WishImage
          :src="imageUrl(item.image_id!, item.image_is_icon ? undefined : 400)"
          :is-icon="item.image_is_icon"
          :class="`photo-${photoLayout}`"
          alt=""
          :loading="index < 4 ? 'eager' : 'lazy'"
          :fetchpriority="index < 2 ? 'high' : 'auto'"
          @load="photoLoaded"
          @error="imageFailed = true"
        />
      </div>
      <span
        v-if="item.reservation && !item.reservation.reserved_by_me"
        class="wish-status wish-reservation"
        >{{ reservationLabel }}</span
      >
      <div class="tile-content">
        <h3
          v-if="title && !(item.archived_at && hasPhoto)"
          :title="title"
        >
          {{ title }}
        </h3>
      </div>
    </AppButton>
    <span
      v-if="item.reservation?.reserved_by_me"
      class="wish-reserved-star"
      :class="{ 'with-heart': item.most_wanted }"
      aria-label="Вы забронировали"
      title="Вы забронировали"
    ><Star :size="16" fill="currentColor" /></span>
    <span
      v-if="item.most_wanted"
      class="wish-heart"
      aria-label="Очень хочу"
      title="Очень хочу"
      ><Heart :size="16" fill="currentColor"
    /></span>
  </article>
</template>

<style scoped>
.wish-author-avatar { position: absolute; top: 12px; left: 12px; z-index: 3; width: 26px; height: 26px; font-size: 10px; }
.most-wanted-card .wish-author-avatar { top: 14px; left: 14px; }
.wish-reserved-star {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 0 var(--wish-radius) 0 16px;
  color: #fff;
  background: #4a7a9e;
  pointer-events: none;
}
.wish-reserved-star.with-heart { top: 36px; border-radius: 12px 0 0 12px; }
.collection-tile {
  --wish-radius: var(--radius-lg);
  --wanted-gradient: linear-gradient(110deg, #2f6878, #6a9aab 30%, #c4ae65 60%, #4a8a9a 82%, #2f6878);
  position: relative;
  min-width: 0;
  border: 0;
  border-radius: var(--wish-radius);
  background: none;
  box-shadow: none;
}
.wish-poster {
  position: relative;
  display: block;
  width: 100%;
  aspect-ratio: clamp(.65, var(--tile-photo-ratio, .75), 1.2);
  overflow: hidden;
  isolation: isolate;
  border: 0;
  border-radius: var(--wish-radius);
  background: var(--wish-background);
  color: #fff;
  text-align: center;
  cursor: pointer;
}
.wish-poster.tile-photo {
  box-shadow:
    inset 0 0 0 1px rgb(26 43 58 / 10%),
    0 1px 2px rgb(26 43 58 / 5%);
}
:root[data-theme='dark'] .wish-poster.tile-photo {
  box-shadow:
    inset 0 0 0 1px rgb(232 238 245 / 12%),
    0 1px 2px rgb(0 0 0 / 25%);
}
.wish-poster:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
.without-photo .wish-poster {
  aspect-ratio: auto;
  min-height: 188px;
  color: var(--wish-note-ink);
  text-align: left;
  isolation: isolate;
  overflow: hidden;
  background:
    radial-gradient(ellipse 80% 55% at var(--wish-note-flare), var(--wish-note-flare-color), transparent 55%),
    radial-gradient(ellipse 70% 60% at var(--wish-note-spot), var(--wish-note-glow), transparent 60%),
    radial-gradient(ellipse 50% 40% at var(--wish-note-orb), var(--wish-note-orb-color), transparent 62%),
    var(--wish-note-wash);
  box-shadow:
    inset 0 0 0 1px var(--wish-note-edge),
    0 12px 30px rgb(12 24 36 / 12%);
}
.without-photo .wish-poster::before {
  content: '';
  position: absolute;
  inset: -20% -10%;
  z-index: 0;
  pointer-events: none;
  background:
    linear-gradient(
      var(--wish-note-shear),
      transparent 0%,
      rgb(255 255 255 / 18%) 42%,
      transparent 58%
    );
  opacity: 0.85;
}
.wish-note-0 {
  --wish-background: radial-gradient(ellipse at 10% 15%, #9ec8d4, transparent 65%), linear-gradient(145deg, #4a8a9a, #1a3a48);
  --wish-note-wash: linear-gradient(160deg, #8fd0dc 0%, #4f97a8 38%, #2a6478 72%, #1b4554 100%);
  --wish-note-glow: rgb(210 245 250 / 78%);
  --wish-note-spot: 12% 8%;
  --wish-note-flare: 88% 16%;
  --wish-note-flare-color: rgb(255 236 190 / 70%);
  --wish-note-orb: 70% 85%;
  --wish-note-orb-color: rgb(120 190 170 / 42%);
  --wish-note-shear: 118deg;
  --wish-note-ink: #f7fbfc;
  --wish-note-edge: rgb(255 255 255 / 28%);
}
.wish-note-1 {
  --wish-background: radial-gradient(ellipse at 90% 5%, #b8d8e2, transparent 65%), linear-gradient(145deg, #6a9aab, #243f4c);
  --wish-note-wash: linear-gradient(152deg, #7eb8e8 0%, #4a7eb8 34%, #2f5688 68%, #1c3558 100%);
  --wish-note-glow: rgb(220 240 255 / 72%);
  --wish-note-spot: 92% 4%;
  --wish-note-flare: 18% 78%;
  --wish-note-flare-color: rgb(180 230 220 / 55%);
  --wish-note-orb: 40% 20%;
  --wish-note-orb-color: rgb(255 220 170 / 38%);
  --wish-note-shear: 135deg;
  --wish-note-ink: #f7fbfc;
  --wish-note-edge: rgb(255 255 255 / 28%);
}
.wish-note-2 {
  --wish-background: radial-gradient(ellipse at 95% 10%, #a8c8d4, transparent 65%), linear-gradient(145deg, #3a6a7a, #6a9aab);
  --wish-note-wash: linear-gradient(148deg, #b7d6a4 0%, #6fa87a 36%, #3f7a68 70%, #25524c 100%);
  --wish-note-glow: rgb(235 250 220 / 70%);
  --wish-note-spot: 100% 10%;
  --wish-note-flare: 14% 14%;
  --wish-note-flare-color: rgb(255 242 205 / 62%);
  --wish-note-orb: 55% 90%;
  --wish-note-orb-color: rgb(140 200 190 / 40%);
  --wish-note-shear: 125deg;
  --wish-note-ink: #f7fbfc;
  --wish-note-edge: rgb(255 255 255 / 28%);
}
.wish-note-3 {
  --wish-background: radial-gradient(ellipse at 85% 20%, #a4c0cc, transparent 60%), linear-gradient(145deg, #5a8898, #2f5564);
  --wish-note-wash: linear-gradient(156deg, #e0c48a 0%, #b8925c 32%, #6e7a68 66%, #3a5564 100%);
  --wish-note-glow: rgb(255 240 205 / 68%);
  --wish-note-spot: 82% 10%;
  --wish-note-flare: 10% 88%;
  --wish-note-flare-color: rgb(170 215 230 / 52%);
  --wish-note-orb: 30% 35%;
  --wish-note-orb-color: rgb(255 210 150 / 35%);
  --wish-note-shear: 112deg;
  --wish-note-ink: #f7fbfc;
  --wish-note-edge: rgb(255 255 255 / 28%);
}
:root[data-theme='dark'] .wish-note-0 {
  --wish-note-wash: linear-gradient(160deg, #4a8ea0 0%, #2f6576 45%, #17323e 100%);
  --wish-note-glow: rgb(150 220 230 / 48%);
  --wish-note-flare-color: rgb(230 200 130 / 36%);
  --wish-note-orb-color: rgb(90 160 150 / 28%);
}
:root[data-theme='dark'] .wish-note-1 {
  --wish-note-wash: linear-gradient(152deg, #3f6f98 0%, #2a5078 45%, #152438 100%);
  --wish-note-glow: rgb(140 200 235 / 40%);
  --wish-note-flare-color: rgb(120 190 180 / 28%);
  --wish-note-orb-color: rgb(210 170 100 / 22%);
}
:root[data-theme='dark'] .wish-note-2 {
  --wish-note-wash: linear-gradient(148deg, #5a8a68 0%, #3a6a58 45%, #1a322c 100%);
  --wish-note-glow: rgb(170 220 150 / 36%);
  --wish-note-flare-color: rgb(220 200 130 / 26%);
  --wish-note-orb-color: rgb(100 170 160 / 24%);
}
:root[data-theme='dark'] .wish-note-3 {
  --wish-note-wash: linear-gradient(156deg, #9a7a48 0%, #6a6048 42%, #2a3e4c 100%);
  --wish-note-glow: rgb(230 200 140 / 34%);
  --wish-note-flare-color: rgb(120 180 200 / 24%);
  --wish-note-orb-color: rgb(200 150 90 / 20%);
}
:root[data-theme='dark'] .collection-tile {
  --wanted-gradient: linear-gradient(110deg, #1a3a48, #4a8a9a 28%, #a8904a 58%, #3a6a7a 82%, #1a3a48);
}
.most-wanted-card:not(.without-photo) .wish-poster { background: var(--wanted-gradient); }
.most-wanted-card.without-photo .wish-poster {
  box-shadow:
    inset 0 0 0 1px color-mix(in srgb, #6a9ec4 55%, var(--wish-note-edge)),
    inset 0 0 0 2px color-mix(in srgb, #c4b07a 45%, transparent);
}
.card-art {
  position: absolute;
  inset: 0;
  margin: 0;
  overflow: hidden;
  border-radius: var(--wish-radius);
}
.card-art :deep(img) {
  display: block;
  width: 100%;
  height: 100%;
  max-height: none;
  border-radius: inherit;
  object-fit: cover;
}
.card-art :deep(img.site-icon) {
  object-fit: contain;
  padding: 32px;
}
.most-wanted-card .card-art { inset: 4px; }
.most-wanted-card:not(.without-photo) .wish-poster::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  border-radius: inherit;
  padding: 4px;
  background: var(--wanted-gradient);
  mask:
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 34 34'%3E%3Cpath fill='white' d='M0 0h34v34H16A16 16 0 0 1 0 18Z'/%3E%3C/svg%3E") top right / 34px 34px no-repeat,
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  mask-composite: add, exclude;
}
.tile-content {
  position: absolute;
  inset: auto 0 0;
  z-index: 1;
  padding: 36px 20px 16px;
  background: linear-gradient(transparent, rgb(0 0 0 / 60%));
}
.tile-content h3 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  overflow-wrap: anywhere;
  margin: 0;
  font: 400 14px / 1.35 var(--font-sans);
}
.without-photo .tile-content {
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 44px 14px 18px;
  background: none;
  text-align: center;
}
.without-photo h3 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  overflow: hidden;
  max-width: 100%;
  margin: 0;
  padding: 0 4px;
  border: 0;
  background: none;
  box-shadow: none;
  font-family: var(--font-editorial);
  font-style: italic;
  font-size: 20px;
  font-weight: 500;
  line-height: 1.3;
  letter-spacing: -0.02em;
  color: inherit;
  text-shadow: 0 1px 12px rgb(12 24 36 / 28%);
}
.without-photo .wish-type-icon {
  background: rgb(255 255 255 / 18%);
  color: #fff;
  border: 1px solid rgb(255 255 255 / 28%);
}
.wish-type-icon,
.wish-heart {
  position: absolute;
  top: 12px;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 50%;
}
.wish-type-icon {
  left: 12px;
  background: rgb(238 243 248 / 85%);
  color: var(--board);
  backdrop-filter: blur(8px);
}
.most-wanted-card .wish-type-icon { top: 14px; left: 14px; }
.wish-heart {
  top: 0;
  right: 0;
  width: 34px;
  height: 34px;
  pointer-events: none;
  color: #fff;
  background: none;
}
.most-wanted-card:not(.without-photo) .wish-heart {
  top: 0;
  right: 0;
  width: 34px;
  height: 34px;
  border-radius: 0 var(--wish-radius) 0 16px;
  background: none;
}
.wish-status {
  position: absolute;
  z-index: 3;
  max-width: calc(100% - 24px);
  padding: 5px 8px;
  border-radius: 8px;
  background: rgb(238 243 248 / 92%);
  color: var(--board);
  font-size: 11px;
  line-height: 1.3;
}
.wish-archive { top: 46px; left: 12px; display: flex; gap: 4px; align-items: center; }
.wish-reservation { top: 46px; left: 12px; }
.archived .wish-reservation { top: 76px; }
.certificate-face {
  position: relative;
  display: flex;
  width: 100%;
  min-height: 96px;
  align-items: center;
  gap: 12px;
  padding: 14px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--accent) 16%, var(--line));
  border-radius: var(--wish-radius);
  background:
    linear-gradient(
      165deg,
      color-mix(in srgb, var(--accent) 10%, var(--surface)) 0%,
      var(--surface) 100%
    );
  color: var(--ink);
  text-align: left;
  box-shadow: 0 8px 20px rgb(12 24 36 / 5%);
  cursor: pointer;
}
.certificate-face:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
.certificate-logo {
  display: grid;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  place-items: center;
  overflow: hidden;
  border-radius: 12px;
  background: #fff;
  box-shadow: inset 0 0 0 1px var(--line);
}
.certificate-logo .site-icon {
  display: block;
  width: 28px;
  height: 28px;
  object-fit: contain;
}
.shop-symbol {
  flex-shrink: 0;
  color: var(--accent);
  opacity: 0.85;
}
.certificate-copy {
  min-width: 0;
  flex: 1;
}
.certificate-copy h3 {
  margin: 0;
  overflow-wrap: anywhere;
  font: 500 14px / 1.35 var(--font-sans);
}
.certificate-copy span {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}
.certificate-arrow {
  flex-shrink: 0;
  color: var(--muted);
}
.ticket-face {
  position: relative;
  display: flex;
  width: 100%;
  min-height: 168px;
  flex-direction: column;
  justify-content: flex-end;
  padding: 16px 14px 14px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--ticket-accent) 18%, var(--line));
  border-radius: var(--wish-radius);
  background:
    radial-gradient(
      ellipse at 12% 0%,
      color-mix(in srgb, var(--ticket-accent) 16%, transparent),
      transparent 55%
    ),
    color-mix(in srgb, var(--ticket-accent) 8%, var(--surface));
  color: var(--ink);
  text-align: left;
  cursor: pointer;
  box-shadow: 0 8px 22px rgb(12 24 36 / 6%);
}
.ticket-face:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
.ticket-with-photo {
  aspect-ratio: clamp(0.65, var(--tile-photo-ratio, 0.75), 1);
  min-height: 0;
  color: #f4f7fa;
  border-color: transparent;
  background: #101c28;
}
.ticket-art {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.ticket-art :deep(img) {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.ticket-copy {
  position: relative;
  z-index: 1;
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}
.ticket-with-photo .ticket-copy {
  padding-top: 28px;
  background: linear-gradient(transparent, rgb(8 14 22 / 72%));
  margin: 0 -14px -14px;
  padding: 36px 14px 14px;
}
.ticket-face-title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  overflow-wrap: anywhere;
  margin: 0;
  max-width: 100%;
  font: 500 16px / 1.3 var(--font-editorial);
  letter-spacing: -0.02em;
}
.ticket-meta {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.3;
}
.ticket-with-photo .ticket-meta {
  color: rgb(244 247 250 / 78%);
}
.ticket-face .wish-type-icon {
  z-index: 3;
}
.ticket-with-photo .wish-type-icon {
  background: rgb(16 28 40 / 72%);
  color: #f4f7fa;
}
.ticket-face .wish-status {
  position: static;
  max-width: none;
  margin-top: 6px;
  padding: 0;
  background: none;
  color: var(--muted);
}
.ticket-with-photo .wish-status {
  color: rgb(244 247 250 / 78%);
}
.ticket-accent {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 4px;
  background: color-mix(in srgb, var(--ticket-accent) 72%, #1a2b3a);
}
.ticket-with-photo .ticket-accent {
  width: 3px;
  background: color-mix(in srgb, var(--ticket-accent) 80%, #fff);
}
.archived .ticket-face {
  opacity: 0.92;
}
.link-bookmark {
  position: relative;
  display: flex;
  width: 100%;
  min-height: 148px;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  padding: 14px;
  overflow: hidden;
  isolation: isolate;
  border: 0;
  border-radius: var(--wish-radius);
  background:
    radial-gradient(ellipse 80% 55% at var(--wish-note-flare, 88% 16%), var(--wish-note-flare-color, rgb(255 236 190 / 55%)), transparent 55%),
    radial-gradient(ellipse 70% 60% at var(--wish-note-spot, 12% 8%), var(--wish-note-glow, rgb(190 236 244 / 55%)), transparent 60%),
    radial-gradient(ellipse 50% 40% at var(--wish-note-orb, 70% 85%), var(--wish-note-orb-color, rgb(120 190 170 / 35%)), transparent 62%),
    var(--wish-note-wash, linear-gradient(160deg, #6eb8c6, #245466));
  color: #f7fbfc;
  text-align: left;
  cursor: pointer;
  box-shadow:
    inset 0 0 0 1px var(--wish-note-edge, rgb(255 255 255 / 24%)),
    0 12px 30px rgb(12 24 36 / 12%);
}
.link-bookmark::before {
  content: '';
  position: absolute;
  inset: -20% -10%;
  z-index: 0;
  pointer-events: none;
  background:
    linear-gradient(
      var(--wish-note-shear, 118deg),
      transparent 0%,
      rgb(255 255 255 / 16%) 42%,
      transparent 58%
    );
  opacity: 0.85;
}
.link-bookmark:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
.link-bookmark-spine {
  position: relative;
  z-index: 1;
  display: flex;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid rgb(255 255 255 / 28%);
  background: rgb(255 255 255 / 88%);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 55%);
  color: #2a5564;
  font: 600 15px / 1 var(--font-editorial);
}
.link-bookmark-spine .site-icon {
  display: block;
  width: 24px;
  height: 24px;
  object-fit: contain;
}
.link-bookmark-copy {
  position: relative;
  z-index: 1;
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  justify-content: flex-end;
  gap: 4px;
  padding: 10px 28px 10px 12px;
  border: 1px solid rgb(255 255 255 / 22%);
  border-radius: 16px;
  background:
    linear-gradient(
      165deg,
      rgb(255 255 255 / 18%) 0%,
      rgb(255 255 255 / 7%) 100%
    );
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 28%);
  -webkit-backdrop-filter: blur(10px) saturate(1.1);
  backdrop-filter: blur(10px) saturate(1.1);
}
.link-bookmark-copy h3 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  overflow-wrap: anywhere;
  word-break: break-word;
  margin: 0;
  font: 500 15px / 1.3 var(--font-editorial);
  font-style: italic;
  color: inherit;
  text-shadow: 0 1px 10px rgb(12 24 36 / 18%);
}
.link-bookmark-hint,
.link-bookmark-meta {
  color: rgb(247 251 252 / 78%);
  font-size: 12px;
  line-height: 1.3;
}
.link-bookmark-arrow {
  position: absolute;
  right: 22px;
  bottom: 24px;
  z-index: 2;
  color: #fff;
  opacity: 0.92;
}
.archived .link-bookmark {
  opacity: 0.92;
}
.archived .wish-poster::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  border-radius: inherit;
  background:
    linear-gradient(115deg, transparent 15%, rgb(255 255 255 / 28%) 16%, rgb(255 255 255 / 7%) 35%, transparent 36% 60%, rgb(255 255 255 / 16%) 61%, transparent 78%),
    linear-gradient(145deg, rgb(215 230 224 / 28%), rgb(55 79 70 / 18%));
  backdrop-filter: blur(0.5px) saturate(75%) contrast(95%);
  box-shadow: inset 0 0 0 1px rgb(255 255 255 / 45%), inset 0 0 22px rgb(255 255 255 / 18%), inset 0 -12px 25px rgb(25 45 35 / 15%);
}
.archived .wish-poster { opacity: 1; }
.archived .tile-content { z-index: 3; }
.archived .wish-archive {
  top: auto;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  background: rgb(238 243 248 / 75%);
  backdrop-filter: blur(12px);
}
.archived .wish-reservation { top: 46px; }
</style>
