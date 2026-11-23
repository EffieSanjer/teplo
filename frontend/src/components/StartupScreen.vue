<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';

const props = defineProps<{ ready: boolean }>();
const visible = ref(true);
const startedAt = performance.now();
let observer: MutationObserver | undefined;
let settleTimer: ReturnType<typeof setTimeout> | undefined;
let deadline: ReturnType<typeof setTimeout> | undefined;
let stopped = false;
const cleanups = new Set<() => void>();

function finish() {
  visible.value = false;
  stopped = true;
  observer?.disconnect();
  clearTimeout(settleTimer);
  clearTimeout(deadline);
  cleanups.forEach((cleanup) => cleanup());
  cleanups.clear();
}

function check() {
  clearTimeout(settleTimer);
  if (stopped || !props.ready) return;
  // Wait for the initial route's data before looking for its images.
  if (document.querySelector('.app-shell [aria-busy="true"]')) return;
  const images = Array.from(document.querySelectorAll<HTMLImageElement>('.app-shell img')).filter(
    (image) => {
      const rect = image.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.top < window.innerHeight && rect.bottom > 0;
    },
  );
  const pending = images.filter((image) => !image.complete);
  if (pending.length) {
    pending.forEach((image) => {
      const done = () => {
        cleanup();
        check();
      };
      const cleanup = () => {
        image.removeEventListener('load', done);
        image.removeEventListener('error', done);
        cleanups.delete(cleanup);
      };
      image.addEventListener('load', done, { once: true });
      image.addEventListener('error', done, { once: true });
      cleanups.add(cleanup);
    });
    return;
  }
  // Allow route transitions and newly rendered cards to settle.
  settleTimer = setTimeout(finish, Math.max(350, 4000 - (performance.now() - startedAt)));
}

watch(
  () => props.ready,
  async (ready) => {
    if (!ready || stopped) return;
    await nextTick();
    if (stopped) return;
    observer?.disconnect();
    observer = new MutationObserver(check);
    const shell = document.querySelector('.app-shell');
    if (shell)
      observer.observe(shell, {
        subtree: true,
        childList: true,
        attributes: true,
        attributeFilter: ['src', 'aria-busy'],
      });
    deadline = setTimeout(finish, 12000);
    check();
  },
  { immediate: true },
);

onBeforeUnmount(finish);
</script>

<template>
  <Transition name="startup">
    <div
      v-if="visible"
      class="fixed inset-0 z-[10000] grid place-items-center bg-paper px-6 text-ink dark:bg-[#202823] dark:text-[#ede9df]"
      role="status"
      aria-live="polite"
      aria-label="Загрузка приложения"
    >
      <div class="w-full max-w-[340px]">
        <div class="mb-6 flex items-center justify-between text-[9px] tracking-[.15em] text-muted">
          <span>ЛИЧНОЕ ПРОСТРАНСТВО</span><span>БЕТА</span>
        </div>
        <div class="rounded-md bg-[#304b40] px-7 py-10 text-paper">
          <div class="text-[60px] leading-none font-extrabold tracking-[-.065em]">
            кстати<span class="text-sand">,</span>
          </div>
          <h1 class="mt-9 font-editorial text-[36px] leading-[1.1] tracking-tight">
            Маленькие<br /><em class="text-sand">желания.</em>
          </h1>
          <p class="mt-4 text-xs leading-relaxed text-[#cbd4c6]">И подарки со смыслом.</p>
          <div
            class="mt-10 flex items-center gap-3 border-t border-white/15 pt-5 text-[11px] text-[#cbd4c6]"
          >
            <span
              class="size-4 animate-spin rounded-full border border-white/20 border-t-sand motion-reduce:animate-none"
              aria-hidden="true"
            />Открываем вашу коллекцию…
          </div>
        </div>
        <p class="mt-5 text-center text-[10px] text-muted">Для того, что хочется сохранить.</p>
      </div>
    </div>
  </Transition>
</template>
