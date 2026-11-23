<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { X } from 'lucide-vue-next';

defineProps<{ title: string }>();
const emit = defineEmits<{ close: [] }>();

const dialog = ref<HTMLDialogElement>();
let previous: HTMLElement | null = null;
let previousOverflow = '';
let viewportFrame = 0;

function fitKeyboard() {
  cancelAnimationFrame(viewportFrame);
  viewportFrame = requestAnimationFrame(() => {
    const modal = dialog.value;
    if (!modal?.querySelector('.item-form')) return;
    const viewport = window.visualViewport;
    modal.style.setProperty('--keyboard-height', `${viewport?.height ?? window.innerHeight}px`);
    modal.style.setProperty('--keyboard-top', `${viewport?.offsetTop ?? 0}px`);
    const field = document.activeElement;
    if (
      !(field instanceof HTMLElement) ||
      !modal.contains(field) ||
      !field.matches('input, textarea, select')
    )
      return;
    const bounds = field.getBoundingClientRect();
    const top = (viewport?.offsetTop ?? 0) + 24;
    const bottom = top + (viewport?.height ?? window.innerHeight) - 110;
    if (bounds.bottom > bottom) modal.scrollTop += bounds.bottom - bottom;
    else if (bounds.top < top) modal.scrollTop -= top - bounds.top;
  });
}

onMounted(async () => {
  previous = document.activeElement as HTMLElement;
  previousOverflow = document.body.style.overflow;
  document.body.style.overflow = 'hidden';
  await nextTick();
  dialog.value?.showModal();
  window.visualViewport?.addEventListener('resize', fitKeyboard);
  window.visualViewport?.addEventListener('scroll', fitKeyboard);
  dialog.value?.addEventListener('focusin', fitKeyboard);
  fitKeyboard();
  if (dialog.value) dialog.value.scrollTop = 0;
});

onBeforeUnmount(() => {
  cancelAnimationFrame(viewportFrame);
  window.visualViewport?.removeEventListener('resize', fitKeyboard);
  window.visualViewport?.removeEventListener('scroll', fitKeyboard);
  dialog.value?.removeEventListener('focusin', fitKeyboard);
  document.body.style.overflow = previousOverflow;
  previous?.focus({ preventScroll: true });
});
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="modal m-auto max-h-[calc(var(--keyboard-height,100dvh)-16px)] w-[min(820px,calc(100vw-20px))] max-w-none overflow-y-auto overscroll-contain rounded-lg border border-line bg-paper p-4 text-ink shadow-xl min-[641px]:p-6 dark:border-[#475349] dark:bg-[#202823] dark:text-[#ede9df]"
      aria-labelledby="modal-title"
      @cancel.prevent="emit('close')"
      @click="$event.target === dialog && emit('close')"
    >
      <div class="modal-inner">
        <header
          class="modal-header mb-5 flex items-center justify-between gap-3 border-b border-line pb-4"
        >
          <h2 id="modal-title" class="font-editorial text-2xl leading-tight tracking-tight">
            {{ title }}
          </h2>
          <slot name="header-actions" />
          <button class="icon-button" aria-label="Закрыть" @click="emit('close')">
            <X :size="22" />
          </button>
        </header>
        <slot />
      </div>
    </dialog>
  </Teleport>
</template>
