<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { X } from 'lucide-vue-next';
import { lockVerticalSwipes } from '../integrations/telegram';
import { AppButton } from './ui';

// The wish editor is edge-to-edge and supplies its own close button on the photo.
withDefaults(defineProps<{ title: string; bare?: boolean }>(), { bare: false });
const emit = defineEmits<{ close: [] }>();

const dialog = ref<HTMLDialogElement>();
let previous: HTMLElement | null = null;
let previousOverflow = '';
let viewportFrame = 0;
let releaseSwipes: (() => void) | undefined;
// Only explicit close buttons may dismiss a dialog: no backdrop click, no Escape.
function keepOpen() {}

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
  releaseSwipes = lockVerticalSwipes();
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
  releaseSwipes?.();
  document.body.style.overflow = previousOverflow;
  previous?.focus({ preventScroll: true });
});
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="modal max-w-none overflow-y-auto overscroll-contain bg-paper text-ink dark:bg-[#202823] dark:text-[#ede9df]"
      :class="
        bare
          ? 'm-0 h-[var(--keyboard-height,100dvh)] max-h-none w-full rounded-none border-0 p-0 shadow-none min-[641px]:m-auto min-[641px]:h-auto min-[641px]:max-h-[calc(var(--keyboard-height,100dvh)-16px)] min-[641px]:w-[min(820px,calc(100vw-20px))] min-[641px]:rounded-lg min-[641px]:border min-[641px]:border-line min-[641px]:shadow-xl min-[641px]:dark:border-[#475349]'
          : 'm-auto max-h-[calc(var(--keyboard-height,100dvh)-16px)] w-[min(820px,calc(100vw-20px))] rounded-lg border border-line p-4 shadow-xl min-[641px]:p-6 dark:border-[#475349]'
      "
      :aria-label="bare ? title : undefined"
      :aria-labelledby="bare ? undefined : 'modal-title'"
      @cancel.prevent="keepOpen"
      @click="!bare && $event.target === dialog && emit('close')"
    >
      <div class="modal-inner">
        <header
          v-if="!bare"
          class="modal-header mb-5 flex items-center justify-between gap-3 border-b border-line pb-4"
        >
          <h2 id="modal-title" class="font-editorial text-2xl leading-tight tracking-tight">
            {{ title }}
          </h2>
          <slot name="header-actions" />
          <AppButton variant="icon" label="Закрыть" @click="emit('close')">
            <X :size="22" />
          </AppButton>
        </header>
        <slot />
      </div>
    </dialog>
  </Teleport>
</template>
