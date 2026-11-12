<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'
defineProps<{ title: string }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement>()
let previous: HTMLElement | null = null
onMounted(async () => {
  previous = document.activeElement as HTMLElement
  document.body.style.overflow = 'hidden'
  await nextTick()
  dialog.value?.showModal()
})
onBeforeUnmount(() => { document.body.style.overflow = ''; previous?.focus() })
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="modal" aria-labelledby="modal-title" @cancel.prevent="emit('close')" @click="($event.target === dialog) && emit('close')">
      <div class="modal-inner">
        <header class="modal-header"><h2 id="modal-title">{{ title }}</h2><button class="icon-button" aria-label="Закрыть" @click="emit('close')"><X :size="22" /></button></header>
        <slot />
      </div>
    </dialog>
  </Teleport>
</template>
