<script setup lang="ts">
import { ref } from 'vue';
import { Bookmark } from 'lucide-vue-next';

defineProps<{ name: string; userId: string; count: number; loading: boolean }>();
const emit = defineEmits<{ add: [] }>();
const avatarFailed = ref(false);
</script>

<template>
  <header
    class="board-journal grid min-w-0 grid-cols-[minmax(0,1fr)_auto] gap-x-4 rounded-md bg-[#304b40] p-6 text-paper min-[761px]:block"
  >
    <span class="col-span-2 flex items-center gap-2 text-[8px] tracking-[.15em] text-[#c7d0c1]"
      ><Bookmark :size="13" /> ЛИЧНОЕ ПРОСТРАНСТВО</span
    >
    <div class="col-start-2 row-start-2 my-5 flex min-w-0 items-center gap-3 min-[761px]:mt-8">
      <div
        class="grid size-14 shrink-0 place-items-center overflow-hidden rounded-full bg-sand text-xl text-forest"
      >
        <img
          v-if="!avatarFailed"
          :src="`/api/v1/users/${encodeURIComponent(userId)}/avatar`"
          alt=""
          class="block size-full object-cover"
          @error="avatarFailed = true"
        /><span v-else>{{ name.slice(0, 1) }}</span>
      </div>
      <p class="hidden min-w-0 text-sm break-words min-[761px]:block">
        {{ name || 'Моя коллекция' }}
      </p>
    </div>
    <h1
      class="col-start-1 row-start-2 my-5 font-editorial text-[38px] leading-[1.1] tracking-tight"
    >
      Моя доска<br /><em class="text-sand">желаний.</em>
    </h1>
    <p class="col-span-2 mb-5 text-xs leading-relaxed text-[#cbd4c6]">
      Для того, что хочется сохранить.<br />И однажды воплотить.
    </p>
    <div
      class="col-span-2 flex items-center justify-between border-t border-white/15 pt-4 text-xs text-[#cbd4c6]"
    >
      <span>В моей коллекции</span
      ><strong class="font-editorial text-2xl font-normal text-sand">{{
        loading ? '—' : count
      }}</strong>
    </div>
  </header>
</template>
