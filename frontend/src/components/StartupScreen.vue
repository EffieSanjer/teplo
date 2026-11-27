<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { Spinner } from './ui';
import ThemeCover from './ThemeCover.vue';

const props = defineProps<{ ready: boolean }>();
// Survives a component remount from Vue HMR, so the splash does not flash again.
let startupShown = false;
const visible = ref(!startupShown);
const startedAt = performance.now();
let observer: MutationObserver | undefined;
let settleTimer: ReturnType<typeof setTimeout> | undefined;
let deadline: ReturnType<typeof setTimeout> | undefined;
let stopped = false;
const cleanups = new Set<() => void>();

function finish() {
  startupShown = true;
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
  settleTimer = setTimeout(finish, Math.max(200, 2500 - (performance.now() - startedAt)));
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
    deadline = setTimeout(finish, 8000);
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
      class="startup-screen"
      role="status"
      aria-live="polite"
      aria-label="Загрузка приложения"
    >
      <div class="startup-backdrop" aria-hidden="true">
        <ThemeCover class="startup-cover" />
        <div class="startup-shade" />
      </div>
      <div class="startup-plaque">
        <div class="startup-plaque-glass" aria-hidden="true" />
        <div class="startup-plaque-body">
          <div class="startup-meta">
            <span>ЛИЧНОЕ ПРОСТРАНСТВО</span><span>БЕТА</span>
          </div>
          <div class="brand startup-brand">кстати<span class="brand-comma">,</span></div>
          <h1 class="startup-title">
            Маленькие<br /><em>желания.</em>
          </h1>
          <p class="startup-lead">И подарки со смыслом.</p>
          <div class="startup-status">
            <Spinner :size="16" class="text-ember" />Открываем вашу коллекцию…
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.startup-screen {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  color: var(--ink);
}
.startup-backdrop {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.startup-cover {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 35%;
}
.startup-shade {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(
      180deg,
      rgb(18 40 58 / 18%) 0%,
      transparent 42%,
      color-mix(in srgb, var(--paper) 35%, transparent) 78%,
      var(--paper) 100%
    );
}
:root[data-theme='dark'] .startup-shade {
  background:
    linear-gradient(
      180deg,
      rgb(8 14 22 / 42%) 0%,
      transparent 40%,
      color-mix(in srgb, var(--paper) 40%, transparent) 78%,
      var(--paper) 100%
    );
}
.startup-plaque {
  position: relative;
  z-index: 1;
  width: min(100%, 340px);
  isolation: isolate;
}
.startup-plaque-glass {
  position: absolute;
  inset: 0;
  border-radius: 28px;
  border: 1px solid rgb(255 255 255 / 48%);
  background:
    linear-gradient(
      165deg,
      rgb(255 255 255 / 42%) 0%,
      rgb(243 246 248 / 26%) 48%,
      rgb(255 255 255 / 16%) 100%
    );
  box-shadow:
    0 18px 48px rgb(12 24 36 / 14%),
    inset 0 1px 0 rgb(255 255 255 / 65%);
  -webkit-backdrop-filter: blur(16px) saturate(1.15);
  backdrop-filter: blur(16px) saturate(1.15);
  pointer-events: none;
}
:root[data-theme='dark'] .startup-plaque-glass {
  border-color: rgb(255 255 255 / 14%);
  background:
    linear-gradient(
      165deg,
      rgb(255 255 255 / 10%) 0%,
      rgb(16 22 30 / 34%) 50%,
      rgb(12 16 22 / 42%) 100%
    );
  box-shadow:
    0 18px 48px rgb(0 0 0 / 30%),
    inset 0 1px 0 rgb(255 255 255 / 12%);
}
.startup-plaque-body {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 0.85rem;
  padding: 1.35rem 1.4rem 1.45rem;
}
.startup-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  color: var(--muted);
}
:root[data-theme='dark'] .startup-meta {
  color: rgb(255 255 255 / 62%);
}
.startup-brand {
  font-size: 42px;
}
.startup-title {
  margin: 0.35rem 0 0;
  font-family: var(--font-editorial);
  font-size: clamp(30px, 8vw, 36px);
  font-weight: 400;
  line-height: 1.1;
  letter-spacing: -0.02em;
}
.startup-title em {
  color: var(--ember);
  font-style: italic;
}
.startup-lead,
.startup-status {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.45;
  color: var(--muted);
}
:root[data-theme='dark'] .startup-title,
:root[data-theme='dark'] .startup-brand {
  color: #fff;
}
:root[data-theme='dark'] .startup-lead,
:root[data-theme='dark'] .startup-status {
  color: rgb(255 255 255 / 72%);
}
.startup-status {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-top: 0.35rem;
  padding-top: 0.9rem;
  border-top: 1px solid color-mix(in srgb, var(--line) 80%, transparent);
}
:root[data-theme='dark'] .startup-status {
  border-top-color: rgb(255 255 255 / 12%);
}
</style>
