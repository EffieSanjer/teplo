<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Archive, ArrowUpRight, Gift, Heart, Lightbulb, Store } from 'lucide-vue-next';
import { imageUrl, itemTitle, type Item } from '../shared/api';
import type { CardOrigin } from '../shared/cardTransition';
import WishImage from './WishImage.vue';
import { itemPalette } from '../shared/itemPalette';
import { certificateTitle } from '../shared/certificateTitle';
import { certificateIcon } from '../shared/certificateStores';
import { AppButton } from './ui';

const props = defineProps<{ item: Item; index: number }>();
const emit = defineEmits<{ open: [item: Item, origin: CardOrigin] }>();
const plasticCard = computed(() => props.item.item_type === 'certificate');
const title = computed(
  () => props.item.title?.trim() || (props.item.url?.trim() ? itemTitle(props.item) : ''),
);
const certificateText = computed(() => certificateTitle(itemTitle(props.item)));
const reservationLabel = computed(() => {
  const reservation = props.item.reservation;
  if (!reservation) return '';
  return reservation.reserved_by_me
    ? 'Вы забронировали'
    : `Забронировано: ${reservation.reserver_name}`;
});
const cardHash = computed(() =>
  Array.from(props.item.id).reduce((value, char) => (value * 31 + char.charCodeAt(0)) >>> 0, 0),
);
const surfaceStyle = computed(() => itemPalette(props.item.id));
const iconUrl = computed(() => certificateIcon(props.item));
const certificateLogoFailed = ref(false);
watch(
  () => `${iconUrl.value || ''}|${props.item.image_id || ''}`,
  () => {
    certificateLogoFailed.value = false;
  },
  { immediate: true },
);
const imageFailed = ref(false);
const hasPhoto = computed(() => Boolean(props.item.image_id && !imageFailed.value));
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
  };
});

function open(event: MouseEvent) {
  const card = event.currentTarget as HTMLElement;
  const bounds = card.getBoundingClientRect();
  const image = card.querySelector<HTMLImageElement>('.card-art img:not(.site-icon)');
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
        'without-photo': !hasPhoto,
        'certificate-card': plasticCard,
        'idea-card': item.item_type === 'idea',
        'most-wanted-card': item.most_wanted && !plasticCard,
      },
      `wish-note-${cardHash % 4}`,
    ]"
    :style="cardStyle"
  >
    <AppButton
      v-if="plasticCard"
      variant="custom"
      class="card-open certificate-face flex min-h-14 w-full items-center gap-2 rounded border border-[#c8cbb5] bg-[#e5e8d8] p-2.5 text-left text-[#344638] dark:border-[#56604b] dark:bg-[#3c4738] dark:text-[#eee8d8]"
      :label="`Открыть: ${itemTitle(item)}`"
      @click="open"
    >
      <span
        v-if="(iconUrl || item.image_id) && !certificateLogoFailed"
        class="certificate-logo flex size-8 shrink-0 items-center justify-center overflow-hidden rounded bg-white"
        ><img
          :src="iconUrl || imageUrl(item.image_id!)"
          class="site-icon block object-contain"
          style="
            width: 32px;
            height: 32px;
            min-width: 32px;
            max-width: 32px;
            max-height: 32px;
            flex: none;
          "
          alt=""
          loading="lazy"
          @error="certificateLogoFailed = true"
      /></span>
      <Store v-else class="shop-symbol opacity-80" :size="20" :stroke-width="1.2" />
      <div class="min-w-0 flex-1">
        <h3 class="text-sm font-medium leading-snug break-words">{{ certificateText.name }}</h3>

        <span v-if="item.archived_at" class="text-xs text-muted">В архиве</span>
        <span v-if="item.reservation" class="mt-2 block text-xs text-forest dark:text-sand">{{
          reservationLabel
        }}</span>
      </div>
      <ArrowUpRight class="shrink-0 text-muted" :size="16" />
    </AppButton>
    <AppButton
      v-else
      variant="custom"
      class="card-open wish-poster"
      :class="{ 'tile-photo': hasPhoto }"
      :label="`Открыть: ${itemTitle(item)}`"
      @click="open"
    >
      <span class="wish-type-icon" :aria-label="item.item_type === 'idea' ? 'Идея' : 'Подарок'">
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
          :src="imageUrl(item.image_id!)"
          :is-icon="item.image_is_icon"
          :class="`photo-${photoLayout}`"
          alt=""
          loading="lazy"
          @load="photoLoaded"
          @error="imageFailed = true"
        />
      </div>
      <span
        v-if="item.reservation"
        class="wish-status wish-reservation"
        >{{ reservationLabel }}</span
      >
      <div class="tile-content">
        <h3
          v-if="title"
          :title="title"
        >
          {{ title }}
        </h3>
      </div>
    </AppButton>
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
.collection-tile {
  --wish-radius: 16px;
  --wanted-gradient: linear-gradient(110deg, #28553f, #789849 30%, #c4ae65 60%, #45816a 82%, #28553f);
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
.wish-poster:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
.without-photo .wish-poster { aspect-ratio: 3 / 4; }
.wish-note-0 { --wish-background: radial-gradient(ellipse at 10% 15%, #bccba0, transparent 65%), linear-gradient(145deg, #698274, #284b3c); }
.wish-note-1 { --wish-background: radial-gradient(ellipse at 90% 5%, #c8b98b, transparent 65%), linear-gradient(145deg, #85917a, #324f46); }
.wish-note-2 { --wish-background: radial-gradient(ellipse at 95% 10%, #b7c5bb, transparent 65%), linear-gradient(145deg, #47645a, #8f9b79); }
.wish-note-3 { --wish-background: radial-gradient(ellipse at 85% 20%, #b4a787, transparent 60%), linear-gradient(145deg, #7b8a7b, #4c7067); }
.most-wanted-card .wish-poster { background: var(--wanted-gradient); }
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
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 44px 22px;
  background: none;
}
.without-photo h3 {
  -webkit-line-clamp: 3;
  font-family: var(--font-editorial);
  font-style: italic;
  font-size: 18px;
  font-weight: 500;
  line-height: 1.3;
  text-shadow: 0 1px 8px rgb(0 0 0 / 15%);
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
  background: rgb(243 240 233 / 85%);
  color: #354f40;
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
  background: rgb(243 240 233 / 92%);
  color: #354f40;
  font-size: 11px;
  line-height: 1.3;
}
.wish-archive { top: 46px; left: 12px; display: flex; gap: 4px; align-items: center; }
.wish-reservation { top: 46px; left: 12px; }
.archived .wish-reservation { top: 76px; }
.certificate-face { border-radius: var(--wish-radius); }
</style>
