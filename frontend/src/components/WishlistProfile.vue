<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Plus } from 'lucide-vue-next';
import { Avatar, AppButton } from './ui';
import {
  avatarFallback,
  sampleAvatarPalette,
  type AvatarPalette,
} from '../shared/avatarPalette';
import ThemeCover from './ThemeCover.vue';

const props = defineProps<{ name: string; userId: string }>();
defineEmits<{ add: [] }>();

const palette = ref<AvatarPalette>();

const displayName = computed(() => props.name.trim() || 'Мой вишлист');

const coverStyle = computed(() => {
  const tones = palette.value || avatarFallback(props.userId);
  return {
    '--cover-primary': tones.primary,
    '--cover-secondary': tones.secondary,
  };
});

watch(
  () => props.userId,
  (id) => {
    palette.value = undefined;
    const image = new Image();
    image.onload = () => {
      palette.value = sampleAvatarPalette(image) || avatarFallback(id);
    };
    image.onerror = () => {
      palette.value = avatarFallback(id);
    };
    image.src = `/api/v1/users/${encodeURIComponent(id)}/avatar`;
  },
  { immediate: true },
);
</script>

<template>
  <section class="page-cover" :style="coverStyle" aria-label="Мой вишлист">
    <div class="page-cover-media">
      <div class="page-cover-backdrop" aria-hidden="true">
        <ThemeCover class="page-cover-image" />
        <div class="page-cover-shade" />
      </div>

      <article class="cover-capsule">
        <div class="cover-capsule-glass" aria-hidden="true" />
        <div class="cover-capsule-body">
          <Avatar class="cover-capsule-avatar" :name="displayName" :user-id="userId" :count="1" />
          <div class="cover-capsule-copy">
            <h1 class="cover-capsule-title">{{ displayName }}</h1>
            <p class="cover-capsule-lead">Тихий уголок для вещей, к которым хочется вернуться.</p>
          </div>
          <AppButton
            variant="custom"
            class="cover-add-action"
            label="Добавить желание"
            @click="$emit('add')"
          >
            <Plus :size="18" />Добавить желание
          </AppButton>
        </div>
      </article>
    </div>
  </section>
</template>
