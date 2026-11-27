<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { User } from '../shared/api';
import { Avatar } from './ui';
import {
  avatarFallback,
  sampleAvatarPalette,
  type AvatarPalette,
} from '../shared/avatarPalette';
import { plural } from '../shared/plural';
import ThemeCover from './ThemeCover.vue';

const props = withDefaults(
  defineProps<{
    user: User;
    prominent?: boolean;
    to?: string;
    wishCount?: number;
    surpriseCount?: number;
  }>(),
  { wishCount: 0, surpriseCount: 0 },
);

const wishesWord = computed(() =>
  plural(props.wishCount, 'желание', 'желания', 'желаний'),
);
const surprisesWord = computed(() =>
  plural(props.surpriseCount, 'сюрприз', 'сюрприза', 'сюрпризов'),
);

const hasAvatar = ref(false);
const palette = ref<AvatarPalette>();

const avatarSrc = computed(
  () => `/api/v1/users/${encodeURIComponent(props.user.id)}/avatar`,
);
const coverStyle = computed(() => {
  const tones = palette.value || avatarFallback(props.user.id);
  return {
    '--cover-primary': tones.primary,
    '--cover-secondary': tones.secondary,
  };
});

watch(
  () => props.user.id,
  (id) => {
    hasAvatar.value = false;
    palette.value = undefined;
    const image = new Image();
    image.onload = () => {
      hasAvatar.value = true;
      palette.value = sampleAvatarPalette(image) || avatarFallback(id);
    };
    image.onerror = () => {
      hasAvatar.value = false;
      palette.value = avatarFallback(id);
    };
    image.src = `/api/v1/users/${encodeURIComponent(id)}/avatar`;
  },
  { immediate: true },
);
</script>

<template>
  <section
    v-if="prominent"
    class="page-cover friend-cover"
    :style="coverStyle"
    :aria-label="user.display_name"
  >
    <div class="page-cover-media friend-cover-media">
      <div class="page-cover-backdrop" aria-hidden="true">
        <img
          v-if="hasAvatar"
          class="page-cover-image page-cover-photo friend-cover-avatar-bg"
          :src="avatarSrc"
          alt=""
          width="512"
          height="512"
          decoding="async"
          fetchpriority="high"
        />
        <ThemeCover v-else class="page-cover-image" />
        <div class="page-cover-shade" />
      </div>

      <div class="friend-cover-stack">
        <RouterLink to="/friends" class="friend-cover-back" aria-label="Вернуться к друзьям">
          ← Друзья
        </RouterLink>
        <article class="friend-cover-card">
          <div class="friend-cover-glass" aria-hidden="true" />
          <div class="friend-cover-body">
            <div class="friend-cover-identity">
              <Avatar
                class="friend-cover-avatar"
                :name="user.display_name"
                :user-id="user.id"
                :count="2"
              />
              <div class="friend-cover-copy">
                <h1 class="friend-cover-title">{{ user.display_name }}</h1>
                <p class="friend-cover-stats">
                  <strong>{{ wishCount }}</strong> {{ wishesWord }}
                  <template v-if="user.can_surprise">
                    <span class="friend-cover-sep" aria-hidden="true">·</span>
                    <strong>{{ surpriseCount }}</strong> {{ surprisesWord }}
                  </template>
                </p>
              </div>
            </div>
            <nav class="friend-cover-actions" aria-label="Списки друга">
              <slot />
            </nav>
          </div>
        </article>
      </div>
    </div>
  </section>

  <article v-else class="friend-card">
    <RouterLink
      v-if="to"
      :to="to"
      class="absolute inset-0 z-10 rounded-[20px]"
      :aria-label="`Вишлист: ${user.display_name}`"
    />
    <Avatar class="size-14 text-xl" :name="user.display_name" :user-id="user.id" lazy />
    <h3 class="min-w-0 font-editorial text-xl leading-tight break-words">
      {{ user.display_name }}
    </h3>
    <div
      class="relative z-20 [&_button]:grid [&_button]:size-8 [&_button]:place-items-center [&_button]:rounded-full [&_button]:text-muted"
    >
      <slot />
    </div>
  </article>
</template>
