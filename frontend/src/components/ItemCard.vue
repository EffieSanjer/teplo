<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Archive, ArrowUpRight, Heart, Store } from 'lucide-vue-next';
import { imageUrl, itemTitle, type Item } from '../shared/api';
import type { CardOrigin } from '../shared/cardTransition';
import WishImage from './WishImage.vue';
import { itemPalette } from '../shared/itemPalette';
import { certificateTitle } from '../shared/certificateTitle';

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
const certificateLogoFailed = ref(false);
watch(
  () => (plasticCard.value ? props.item.image_id : null),
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
      },
      `wish-note-${cardHash % 4}`,
    ]"
    :style="cardStyle"
  >
    <button
      v-if="plasticCard"
      class="card-open certificate-face flex min-h-14 w-full items-center gap-2 rounded border border-[#c8cbb5] bg-[#e5e8d8] p-2.5 text-left text-[#344638] dark:border-[#56604b] dark:bg-[#3c4738] dark:text-[#eee8d8]"
      :aria-label="`Открыть: ${itemTitle(item)}`"
      @click="open"
    >
      <span
        v-if="item.image_id && !certificateLogoFailed"
        class="certificate-logo flex size-8 shrink-0 items-center justify-center overflow-hidden rounded bg-white"
        ><img
          :src="imageUrl(item.image_id)"
          class="site-icon block object-contain"
          style="
            width: 24px;
            height: 24px;
            min-width: 24px;
            max-width: 24px;
            max-height: 24px;
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
    </button>
    <button
      v-else
      class="card-open tile-open relative block w-full overflow-hidden rounded border border-line text-left dark:border-[#475349]"
      :class="
        hasPhoto
          ? 'tile-photo bg-surface dark:bg-[#2b362e]'
          : [
              'tile-note min-h-[155px]',
              ['bg-[#c7d5b7]', 'bg-[#dfc8b9]', 'bg-[#e5dece]', 'bg-[#c7d5cc]'][cardHash % 4],
            ]
      "
      :aria-label="`Открыть: ${itemTitle(item)}`"
      @click="open"
    >
      <span
        v-if="item.archived_at"
        class="tile-kind absolute left-2 top-2 z-10 flex items-center gap-1 rounded bg-paper/90 px-2 py-1 text-[9px] text-forest"
        ><Archive :size="12" aria-hidden="true" />В архиве</span
      >
      <div
        v-if="hasPhoto"
        class="card-art tile-media art-photo m-1 overflow-hidden rounded-sm [&_img]:block [&_img]:max-h-[230px] [&_img]:w-full [&_img]:object-contain [&_img.site-icon]:mx-auto [&_img.site-icon]:my-6"
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
        class="relative z-10 m-2 block rounded bg-paper/95 px-2 py-1 text-xs text-forest"
        >{{ reservationLabel }}</span
      >
      <div class="tile-content" :class="hasPhoto ? 'px-3 pt-2 pb-3' : 'p-4 text-[#344136]'">
        <span
          v-if="!hasPhoto"
          class="wish-note-mark mb-4 block text-[8px] tracking-[.12em] uppercase opacity-75"
          aria-hidden="true"
          >{{ item.item_type === 'idea' ? 'На заметку' : 'Хочется' }}</span
        >
        <h3
          v-if="title"
          :title="title"
          :class="
            hasPhoto
              ? 'text-[13px] leading-snug break-words'
              : 'font-editorial text-xl leading-tight break-words'
          "
        >
          {{ title }}
        </h3>
        <p
          v-if="!hasPhoto && item.description?.trim()"
          class="wish-note-excerpt mt-3 line-clamp-3 text-xs leading-relaxed opacity-80"
        >
          {{ item.description.trim() }}
        </p>
      </div>
    </button>
    <span
      v-if="item.most_wanted"
      class="pointer-events-none absolute top-2 right-2 z-10 rounded-full bg-paper p-1.5 text-forest"
      aria-label="Очень хочу"
      title="Очень хочу"
      ><Heart :size="16" fill="currentColor"
    /></span>
  </article>
</template>
