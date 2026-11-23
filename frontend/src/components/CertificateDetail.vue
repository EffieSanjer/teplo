<script setup lang="ts">
import { ArrowUpRight, Heart, Pencil, Store, Trash2 } from 'lucide-vue-next';
import Modal from './Modal.vue';
import { imageUrl, itemTitle, type Item } from '../shared/api';
import { openExternal } from '../integrations/telegram';

defineProps<{ item: Item; ownProfile: boolean; busy: boolean }>();
const emit = defineEmits<{
  close: [];
  edit: [];
  delete: [];
  reserve: [];
  priority: [];
}>();
</script>

<template>
  <Modal :title="itemTitle(item)" class="certificate-mini" @close="emit('close')">
    <div class="flex items-center gap-3 rounded-lg bg-forest/5 p-4 dark:bg-white/5">
      <img
        v-if="item.image_id"
        :src="imageUrl(item.image_id)"
        alt=""
        class="size-10 rounded bg-white p-1 object-contain"
      />
      <Store v-else :size="28" class="text-forest dark:text-sand" />
      <span class="text-xs text-muted">Магазин для сертификата</span>
    </div>
    <p
      v-if="item.description?.trim()"
      class="my-5 text-sm leading-relaxed whitespace-pre-wrap break-words"
    >
      {{ item.description }}
    </p>
    <p v-if="!ownProfile && item.reservation" class="mt-4 text-xs text-muted">
      {{
        item.reservation.reserved_by_me
          ? 'Вы забронировали'
          : `Забронировано: ${item.reservation.reserver_name}`
      }}
    </p>
    <div class="mt-5 grid gap-2">
      <button
        v-if="item.url"
        class="button primary justify-between"
        @click="openExternal(item.url)"
      >
        Открыть ссылку<ArrowUpRight :size="18" />
      </button>
      <button
        v-if="!ownProfile && item.can_reserve"
        class="button secondary"
        :disabled="busy"
        @click="emit('reserve')"
      >
        {{ item.reservation?.reserved_by_me ? 'Снять бронь' : 'Забронировать' }}
      </button>
      <button
        v-if="ownProfile && item.list_type === 'wishlist' && !item.archived_at"
        class="button secondary gap-2"
        :aria-pressed="item.most_wanted"
        :disabled="busy"
        @click="emit('priority')"
      >
        <Heart :size="16" :fill="item.most_wanted ? 'currentColor' : 'none'" />Очень хочу
      </button>
      <div v-if="item.can_manage" class="mt-2 grid grid-cols-2 gap-2 border-t border-line pt-3">
        <button
          v-if="!item.archived_at"
          class="button secondary gap-2"
          :disabled="busy"
          @click="emit('edit')"
        >
          <Pencil :size="16" />Редактировать
        </button>
        <button
          class="button secondary gap-2 text-[#a04432]"
          :disabled="busy"
          @click="emit('delete')"
        >
          <Trash2 :size="16" />Удалить
        </button>
      </div>
    </div>
  </Modal>
</template>

<style>
dialog.certificate-mini {
  width: min(420px, calc(100vw - 28px));
  border-radius: 18px;
}
</style>
