<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ArrowUpRight, Heart, LockKeyhole, Pencil, Store, Trash2, X } from 'lucide-vue-next';
import Modal from './Modal.vue';
import { imageUrl, itemTitle, type Item } from '../shared/api';
import { certificateIcon } from '../shared/certificateStores';
import { openExternal } from '../integrations/telegram';
import { AppButton } from './ui';

const props = defineProps<{ item: Item; ownProfile: boolean; busy: boolean }>();
const iconUrl = computed(() => certificateIcon(props.item));
const iconFailed = ref(false);
const accent = ref('#658464');
function sampleColor(event: Event) {
  accent.value = '#658464';
  try {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 24;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) return;
    context.drawImage(event.target as HTMLImageElement, 0, 0, 24, 24);
    const pixels = context.getImageData(0, 0, 24, 24).data;
    const buckets = new Map<string, { count: number; rgb: number[] }>();
    for (let i = 0; i < pixels.length; i += 4) {
      const rgb = [pixels[i]!, pixels[i + 1]!, pixels[i + 2]!];
      const max = Math.max(...rgb), min = Math.min(...rgb);
      if (pixels[i + 3]! < 128 || max < 40 || min > 225 || max - min < 25) continue;
      const key = rgb.map((value) => Math.round(value / 48)).join(',');
      const bucket = buckets.get(key) || { count: 0, rgb: [0, 0, 0] };
      bucket.count++;
      rgb.forEach((value, channel) => { bucket.rgb[channel]! += value; });
      buckets.set(key, bucket);
    }
    const dominant = [...buckets.values()].sort((a, b) => b.count - a.count)[0];
    if (dominant) accent.value = `rgb(${dominant.rgb.map((value) => Math.round(value / dominant.count)).join(' ')})`;
  } catch { /* Keep the theme fallback for images that cannot be sampled. */ }
}
watch(iconUrl, () => {
  iconFailed.value = false;
});
const imageSrc = computed(() =>
  iconUrl.value && !iconFailed.value
    ? iconUrl.value
    : props.item.image_id
      ? imageUrl(props.item.image_id, props.item.image_is_icon ? undefined : 400)
      : null,
);
const emit = defineEmits<{
  close: [];
  edit: [];
  delete: [];
  reserve: [];
  priority: [];
}>();
</script>

<template>
  <Modal bare close-on-backdrop :title="itemTitle(item)" class="certificate-mini" :style="{ '--store-accent': accent }" @close="emit('close')">
    <div class="certificate-detail-content">
    <header class="certificate-detail-header">
      <AppButton variant="glass-icon" label="Закрыть" @click="emit('close')"><X :size="18" /></AppButton>
    </header>
    <div class="certificate-detail-brand">
      <img
        v-if="imageSrc"
        :src="imageSrc"
        alt=""
        class="certificate-detail-logo"
        @load="sampleColor"
        @error="iconFailed = true"
      />
      <Store v-else :size="28" class="certificate-fallback-icon" />
      <h2>{{ itemTitle(item) }} <LockKeyhole v-if="item.list_type === 'surprise' && item.surprise_visibility === 'private'" :size="15" class="inline-block align-middle" aria-label="Только мне" /></h2>
    </div>
    <p
      v-if="item.description?.trim()"
      class="my-5 text-sm leading-relaxed whitespace-pre-wrap break-words"
    >
      {{ item.description }}
    </p>
    <p v-if="!ownProfile && item.reservation && !item.reservation.reserved_by_me" class="mt-4 text-xs certificate-muted">
      Уже забронировано
    </p>
    <div class="mt-5 grid gap-2">
      <div
        v-if="item.url || (ownProfile && item.list_type === 'wishlist' && !item.archived_at)"
        class="certificate-primary-actions"
        :class="{
          'certificate-primary-actions-single':
            !(item.url && ownProfile && item.list_type === 'wishlist' && !item.archived_at),
        }"
      >
        <AppButton
          v-if="item.url"
          variant="glass"
          class="certificate-link-action gap-2"
          @click="openExternal(item.url)"
        >
          Ссылка<ArrowUpRight :size="16" />
        </AppButton>
        <AppButton
          v-if="ownProfile && item.list_type === 'wishlist' && !item.archived_at"
          variant="glass-secondary"
          class="certificate-want-action gap-2"
          :pressed="item.most_wanted"
          :disabled="busy"
          @click="emit('priority')"
        >
          <Heart :size="16" :fill="item.most_wanted ? 'currentColor' : 'none'" />Очень хочу
        </AppButton>
      </div>
      <AppButton
        v-if="!ownProfile && item.can_reserve"
        variant="glass-secondary"
        :disabled="busy"
        @click="emit('reserve')"
      >
        {{ item.reservation?.reserved_by_me ? 'Снять бронь' : 'Забронировать' }}
      </AppButton>
      <div v-if="item.can_manage" class="mt-2 grid grid-cols-2 gap-2 border-t border-white/15 pt-3">
        <AppButton
          v-if="!item.archived_at"
          variant="glass-secondary"
          class="gap-2"
          :disabled="busy"
          @click="emit('edit')"
        >
          <Pencil :size="16" />Редактировать
        </AppButton>
        <AppButton
          variant="glass-secondary"
          class="gap-2 text-[#ffb4a8]"
          :disabled="busy"
          @click="emit('delete')"
        >
          <Trash2 :size="16" />Удалить
        </AppButton>
      </div>
    </div>
    </div>
  </Modal>
</template>

<style>
/* Beat .modal.modal-shell-bare / bg-paper so the store gradient stays in both themes. */
dialog.certificate-mini.modal.modal-shell-bare {
  width: min(420px, calc(100vw - 28px));
  height: fit-content;
  min-height: 0;
  max-height: calc(100dvh - 32px);
  margin: auto;
  padding: 0;
  border: 1px solid rgb(255 255 255 / 14%);
  border-radius: 28px;
  color: #f4fafb;
  background-color: #15202b;
  background-image:
    radial-gradient(ellipse at 14% 0%, color-mix(in srgb, var(--store-accent) 28%, #4a8a9a), transparent 52%),
    linear-gradient(
      155deg,
      color-mix(in srgb, var(--store-accent) 38%, #2a5564) 0%,
      color-mix(in srgb, var(--store-accent) 18%, #15202b) 78%
    );
  box-shadow: 0 24px 80px rgb(0 0 0 / 42%);
  -webkit-backdrop-filter: none;
  backdrop-filter: none;
}
@media (min-width: 641px) {
  dialog.certificate-mini.modal.modal-shell-bare {
    border: 1px solid rgb(255 255 255 / 14%);
    background-color: #15202b;
    background-image:
      radial-gradient(ellipse at 14% 0%, color-mix(in srgb, var(--store-accent) 28%, #4a8a9a), transparent 52%),
      linear-gradient(
        155deg,
        color-mix(in srgb, var(--store-accent) 38%, #2a5564) 0%,
        color-mix(in srgb, var(--store-accent) 18%, #15202b) 78%
      );
    box-shadow: 0 24px 80px rgb(0 0 0 / 42%);
  }
}
.certificate-detail-content { padding: 16px 20px 20px; }
.certificate-detail-header { display: flex; align-items: center; justify-content: flex-end; gap: 16px; font-size: 14px; }
.certificate-detail-brand { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 14px 0 4px; text-align: center; }
.certificate-detail-logo { width: 64px; height: 64px; border-radius: 18px; background: #fff; object-fit: contain; }
.certificate-fallback-icon { color: #f4fafb; opacity: 0.92; }
.certificate-detail-brand h2 { margin: 0; font-size: 24px; font-weight: 500; line-height: 1.2; overflow-wrap: anywhere; }
.certificate-muted { color: rgb(244 250 251 / 72%); }
.certificate-primary-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.certificate-primary-actions-single {
  grid-template-columns: 1fr;
}
.certificate-link-action,
.certificate-want-action {
  width: 100%;
  justify-content: center;
}
.certificate-mini .glass-button,
.certificate-mini .glass-button-secondary {
  color: #f4fafb;
  border-color: rgb(255 255 255 / 22%);
  background: rgb(255 255 255 / 14%);
}
.certificate-mini .glass-button-secondary {
  background: rgb(255 255 255 / 8%);
}
.certificate-mini .glass-icon-button {
  color: #f4fafb;
  background: radial-gradient(circle at center, rgb(0 0 0 / 18%) 19px, transparent 20px);
}
</style>
