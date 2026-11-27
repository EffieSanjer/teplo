<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { ChevronDown, Store } from 'lucide-vue-next';
import type { CertificateStore } from '../shared/certificateStores';

const props = withDefaults(
  defineProps<{
    stores: readonly CertificateStore[];
    modelValue?: string;
    disabled?: boolean;
    ariaLabel?: string;
  }>(),
  { modelValue: '', disabled: false, ariaLabel: 'Выбрать популярный магазин' },
);
const emit = defineEmits<{ 'update:modelValue': [host: string] }>();

const open = ref(false);
const root = ref<HTMLElement>();
const failedIcons = ref<string[]>([]);
const selected = computed(() => props.stores.find((store) => store.host === props.modelValue));

function choose(host: string) {
  emit('update:modelValue', host);
  open.value = false;
}

function fail(host: string) {
  if (!failedIcons.value.includes(host)) failedIcons.value = [...failedIcons.value, host];
}

function onPointerDown(event: PointerEvent) {
  if (!root.value?.contains(event.target as Node)) open.value = false;
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') open.value = false;
}

onMounted(() => document.addEventListener('pointerdown', onPointerDown));
onBeforeUnmount(() => document.removeEventListener('pointerdown', onPointerDown));
</script>

<template>
  <div ref="root" class="store-select mt-2" :class="{ open }" @keydown="onKeydown">
    <button
      type="button"
      class="store-select__trigger"
      :aria-label="ariaLabel"
      :aria-expanded="open"
      :disabled="disabled"
      @click="open = !open"
    >
      <img
        v-if="selected && !failedIcons.includes(selected.host)"
        :src="selected.icon"
        alt=""
        class="store-select__icon"
        @error="fail(selected.host)"
      />
      <Store v-else :size="20" class="store-select__icon text-muted" />
      <span class="store-select__value">{{
        selected?.name || 'Свой магазин — вставьте ссылку ниже'
      }}</span>
      <ChevronDown :size="16" class="ml-auto shrink-0 text-muted" />
    </button>
    <div v-if="open" class="store-select__list" role="listbox" :aria-label="ariaLabel">
      <button
        type="button"
        class="store-select__option"
        :class="{ selected: !modelValue }"
        data-value=""
        role="option"
        :aria-selected="!modelValue"
        @click="choose('')"
      >
        <Store :size="20" class="store-select__icon text-muted" />
        <span class="store-select__value">Свой магазин — вставьте ссылку ниже</span>
      </button>
      <button
        v-for="store in stores"
        :key="store.host"
        type="button"
        class="store-select__option"
        :class="{ selected: modelValue === store.host }"
        :data-value="store.host"
        role="option"
        :aria-selected="modelValue === store.host"
        @click="choose(store.host)"
      >
        <img
          v-if="!failedIcons.includes(store.host)"
          :src="store.icon"
          alt=""
          class="store-select__icon"
          @error="fail(store.host)"
        />
        <Store v-else :size="20" class="store-select__icon text-muted" />
        <span class="store-select__value">{{ store.name }}</span>
        <span class="store-select__host">{{ store.host }}</span>
      </button>
    </div>
  </div>
</template>
