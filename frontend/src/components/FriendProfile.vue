<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ArrowLeft, ArrowUpRight } from 'lucide-vue-next';
import type { User } from '../shared/api';
const props = defineProps<{ user: User; prominent?: boolean; to?: string }>();
const failed = ref(false);
const avatar = computed(() => `/api/v1/users/${encodeURIComponent(props.user.id)}/avatar`);
const initials = computed(() =>
  props.user.display_name
    .trim()
    .split(/\s+/)
    .map((name) => name[0])
    .slice(0, 2)
    .join(''),
);
watch(
  () => props.user.id,
  () => {
    failed.value = false;
  },
);
</script>
<template>
  <header
    v-if="prominent"
    class="grid min-w-0 gap-5 rounded-md bg-[#304b40] p-5 text-paper min-[761px]:p-6"
  >
    <div class="flex items-center justify-between gap-3">
      <RouterLink
        to="/friends"
        class="inline-flex min-h-10 items-center gap-2 text-xs text-sand"
        aria-label="Вернуться к друзьям"
        ><ArrowLeft :size="17" />Друзья</RouterLink
      >
      <span class="text-[8px] tracking-[.15em] text-[#c7d0c1]">ЛИЧНАЯ КОЛЛЕКЦИЯ</span>
    </div>
    <div class="flex min-w-0 items-center gap-4 min-[761px]:flex-col min-[761px]:items-start">
      <div
        class="grid size-[72px] shrink-0 place-items-center overflow-hidden rounded-full bg-sand text-forest"
      >
        <img
          v-if="!failed"
          :src="avatar"
          alt=""
          class="block size-full object-cover"
          @error="failed = true"
        />
        <span v-else class="text-2xl">{{ initials }}</span>
      </div>
      <div class="min-w-0">
        <h1 class="font-editorial text-[28px] leading-tight tracking-tight break-words">
          {{ user.display_name }}
        </h1>
        <p class="mt-2 text-xs text-[#d4c4a4]">Желания и находки</p>
      </div>
    </div>
    <div
      class="flex flex-wrap gap-x-5 gap-y-2 border-t border-white/15 pt-4 text-xs text-[#cbd4c6] [&_strong]:mr-1 [&_strong]:font-normal [&_strong]:text-sand"
    >
      <div><slot name="stats-left" /></div>
      <div><slot name="stats-right" /></div>
    </div>
    <nav
      aria-label="Списки друга"
      class="grid grid-cols-2 gap-2 min-[761px]:grid-cols-1 [&_a]:flex [&_a]:min-h-11 [&_a]:items-center [&_a]:gap-2 [&_a]:rounded [&_a]:border [&_a]:border-white/20 [&_a]:px-3 [&_a]:py-2 [&_a]:text-xs [&_a.active]:border-sand [&_a.active]:bg-sand [&_a.active]:text-forest"
    >
      <slot />
    </nav>
  </header>
  <article
    v-else
    class="relative grid min-w-0 grid-cols-[56px_minmax(0,1fr)_32px] items-center gap-x-3 gap-y-1 rounded-md border border-line bg-surface p-4 transition-colors hover:border-[#9eac92] dark:border-[#475349] dark:bg-[#2b362e]"
  >
    <RouterLink
      v-if="to"
      :to="to"
      class="absolute inset-0 z-10 rounded-md"
      :aria-label="`Вишлист: ${user.display_name}`"
    />
    <div
      class="row-span-2 grid size-14 shrink-0 place-items-center overflow-hidden rounded-full bg-sand text-forest"
    >
      <img
        v-if="!failed"
        :src="avatar"
        alt=""
        loading="lazy"
        class="block size-full object-cover"
        @error="failed = true"
      /><span v-else class="text-xl">{{ initials }}</span>
    </div>
    <h3 class="min-w-0 self-end font-editorial text-xl leading-tight break-words">
      {{ user.display_name }}
    </h3>
    <ArrowUpRight class="self-end text-[#8d7055]" :size="19" />
    <p class="col-start-2 self-start text-[10px] text-muted">Желания и находки</p>
    <div
      class="relative z-20 col-start-3 row-start-2 [&_button]:grid [&_button]:size-8 [&_button]:place-items-center [&_button]:rounded [&_button]:text-muted"
    >
      <slot />
    </div>
  </article>
</template>
