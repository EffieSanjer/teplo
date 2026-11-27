<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowUpRight, Bookmark, Layers, LogOut, ShieldCheck, Users } from 'lucide-vue-next';
import {
  ApiError,
  api,
  authReady,
  clearSession,
  invalidation,
  send,
  session,
  type Session,
} from './shared/api';
import { notice } from './shared/notifications';
import {
  backButton,
  initData,
  initTelegram,
  launchInvitation,
  launchStartParam,
  onLaunchChange,
} from './integrations/telegram';
import { invitationToken } from './shared/invitation';
import SettingsControl from './components/SettingsControl.vue';
import StartupScreen from './components/StartupScreen.vue';
import { avatarFallback, sampleAvatarPalette } from './shared/avatarPalette';
import ThemeCover from './components/ThemeCover.vue';
import { AppButton, FieldMessage, LoadingLabel, ToastMessage } from './components/ui';

const showUiKitLink = import.meta.env.DEV;

watchEffect((onCleanup) => {
  const id = session.value?.user.id;
  if (!id) return;
  let active = true;
  const root = document.documentElement;
  root.style.setProperty('--own-canvas-tone', avatarFallback(id).primary);
  const image = new Image();
  image.onload = () => {
    const palette = sampleAvatarPalette(image);
    if (active && palette) root.style.setProperty('--own-canvas-tone', palette.primary);
  };
  image.src = `/api/v1/users/${encodeURIComponent(id)}/avatar`;
  onCleanup(() => {
    active = false;
    image.onload = null;
    root.style.removeProperty('--own-canvas-tone');
  });
});

const config = ref({ dev_login_enabled: false, telegram_enabled: false }),
  error = ref(''),
  busy = ref(false);
// Temporarily keep account controls out of the interface, without removing them.
const showAccountControls = false;
const route = useRoute(),
  router = useRouter();
let cleanupBack = () => {};
let handledLaunch = '';
let handledExplicitInvite = '';
let cleanupLaunch = () => {};
let disposed = false;
async function openLaunchTarget() {
  await router.isReady();
  // A bot WebApp button contains an explicit invite query. Never replace it
  // with an older start_param retained by Telegram's existing WebView.
  const savedInvite = launchInvitation();
  const explicit =
    typeof route.query.invite === 'string'
      ? route.query.invite
      : savedInvite !== handledExplicitInvite
        ? savedInvite
        : '';
  if (explicit) {
    if (handledExplicitInvite === explicit) return;
    handledExplicitInvite = explicit;
    handledLaunch = launchStartParam();
    if (route.path !== '/friends' || route.query.invite !== explicit)
      await router.replace({ path: '/friends', query: { invite: explicit } });
    return;
  }
  const start = launchStartParam();
  if (!start || handledLaunch === start) return;
  const invite = start.startsWith('friend_') ? invitationToken(start) : undefined;
  if (invite) {
    handledLaunch = start;
    await router.replace({ path: '/friends', query: { invite } });
  } else if (start === 'friends' && !route.query.invite) {
    handledLaunch = start;
    await router.replace('/friends');
  }
}
watch(
  () => route.path,
  () => {
    cleanupBack();
    cleanupBack = backButton(route.path !== '/me', () => {
      void router.push(route.path.startsWith('/users/') ? '/friends' : '/me');
    });
  },
);
async function login(dev = false) {
  busy.value = true;
  error.value = '';
  try {
    // A 401 from bootstrap has already cleared it; avoid a second remount.
    if (session.value) clearSession();
    session.value = await send<Session>(
      dev ? '/auth/dev' : '/auth/telegram',
      dev ? undefined : { init_data: initData() },
    );
    await openLaunchTarget();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function bootstrap() {
  error.value = '';
  busy.value = true;
  try {
    config.value = await api('/auth/config');
    try {
      session.value = await api<Session>('/auth/session');
      await openLaunchTarget();
    } catch (e) {
      if (!(e instanceof ApiError) || e.status !== 401) throw e;
      // Local dev stack: enter immediately as the user configured by DEV_USER_ID.
      if (config.value.dev_login_enabled) await login(true);
      else if (initData() && config.value.telegram_enabled) await login();
    }
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    authReady.value = true;
    busy.value = false;
  }
}
async function logout() {
  try {
    await send('/auth/logout');
  } finally {
    clearSession();
    await router.replace('/me');
  }
}
onMounted(async () => {
  // Launch credentials are captured locally; an unreachable optional SDK must
  // not delay authentication or leave the initial screen waiting for it.
  const resume = () => {
    if (session.value) void openLaunchTarget().catch(() => {});
  };
  cleanupLaunch = onLaunchChange(resume);
  const telegramReady = initTelegram().catch(() => undefined);
  // A Vue HMR remount keeps the shared session/auth refs; do not rebootstrap
  // or run the splash transition again just because the component was replaced.
  if (authReady.value && session.value) return;
  await bootstrap();
  if (disposed) return;
  await telegramReady;
  if (disposed) return;
  cleanupLaunch();
  cleanupLaunch = onLaunchChange(resume);
  if (session.value) await openLaunchTarget();
  // SDK may expose fresher initData after bootstrap; retry once if still logged out.
  else if (config.value.telegram_enabled && initData() && !busy.value) await login();
});
onBeforeUnmount(() => {
  disposed = true;
  cleanupLaunch();
  cleanupBack();
});
</script>

<template>
  <StartupScreen :ready="authReady && !busy" />
  <div class="app-shell min-h-dvh">
    <main
      v-if="session"
      class="main-content min-h-dvh"
      :class="{
        'friends-shell': route.path === '/friends',
        'wishlist-shell': route.path === '/me' || route.path.startsWith('/users/'),
      }"
    >
      <header
        class="topbar mx-auto flex min-h-[84px] max-w-[1440px] items-center gap-4 px-5 min-[761px]:px-10"
        :class="{
          'topbar-over-hero':
            route.path === '/friends' ||
            route.path === '/me' ||
            route.path.startsWith('/users/'),
        }"
      >
        <div class="brand-block">
          <RouterLink to="/me" class="brand" aria-label="Кстати — мой вишлист"
            >кстати<span class="brand-comma">,</span></RouterLink
          >
        </div>
        <nav
          class="main-nav ml-auto hidden items-center gap-1 min-[761px]:flex"
          aria-label="Основная навигация"
        >
          <RouterLink to="/me" :class="{ current: route.path === '/me' }"
            ><Bookmark :size="18" />Мой вишлист</RouterLink
          >
          <RouterLink to="/friends" :class="{ current: route.path === '/friends' }"
            ><Users :size="18" />Друзья</RouterLink
          >
          <RouterLink v-if="showUiKitLink" to="/ui" :class="{ current: route.path === '/ui' }"
            ><Layers :size="18" />UI-кит</RouterLink
          >
        </nav>
        <div class="appearance-control ml-auto min-[761px]:ml-0">
          <SettingsControl />
        </div>
        <div v-if="showAccountControls" class="topbar-actions flex items-center gap-2">
          <AppButton
            variant="icon"
            class="logout-button"
            label="Выйти"
            :title="`Выйти · ${session.user.display_name}`"
            @click="logout"
          >
            <LogOut :size="19" />
          </AppButton>
        </div>
      </header>
      <RouterView
        :key="`${session.user.id}:${session.community_id}:${invalidation}`"
        v-slot="{ Component }"
        ><Transition name="page" mode="out-in"><component :is="Component" /></Transition
      ></RouterView>
    </main>
    <main v-else class="welcome-page">
      <div class="welcome-backdrop" aria-hidden="true">
        <ThemeCover class="welcome-cover" />
        <div class="welcome-shade" />
      </div>
      <div class="login-theme"><SettingsControl /></div>
      <div class="welcome-copy">
        <div class="login-brand brand">кстати<span class="brand-comma">,</span></div>
        <h1 class="font-editorial text-[clamp(42px,7vw,76px)] leading-[1.05] tracking-tight">
          Это тебе<br /><em>идеально подойдёт.</em>
        </h1>
        <p class="mt-5 max-w-sm text-sm leading-relaxed">
          Сохраняй желания и находи подарки для своих.
        </p>
      </div>
      <div class="login-card welcome-card">
        <div class="welcome-card-glass" aria-hidden="true" />
        <div class="welcome-card-body">
          <div class="login-art" aria-hidden="true">
            <Bookmark :size="28" :stroke-width="1.2" />
          </div>
          <h2 class="font-editorial text-2xl">Войти</h2>
          <p>Вишлисты и сюрпризы — рядом.</p>
          <LoadingLabel v-if="!authReady" label="Загрузка…" role="status" />
          <template v-else
            ><AppButton
              v-if="config.dev_login_enabled"
              variant="primary"
              class="login-button"
              :loading="busy"
              loading-text="Входим…"
              @click="login(true)"
            >
              {{ busy ? 'Входим…' : 'Войти в локальную версию'
              }}<ArrowUpRight :size="18" /></AppButton
            ><AppButton
              v-else-if="initData() && config.telegram_enabled"
              variant="primary"
              :loading="busy"
              loading-text="Проверяем доступ…"
              @click="login()"
            >
              {{ busy ? 'Проверяем доступ…' : 'Войти' }}
            </AppButton>
            <FieldMessage v-else-if="!error" class="inline-hint">
              Откройте приложение через бота.
            </FieldMessage>
            <p v-if="config.dev_login_enabled" class="login-disclaimer">
              <ShieldCheck :size="14" />Локальная тестовая версия
            </p>
            <FieldMessage v-if="error" class="inline-error" kind="error" role="alert">
              {{ error }}
            </FieldMessage>
            <AppButton v-if="error" variant="text" @click="bootstrap">
              Повторить подключение
            </AppButton></template
          >
        </div>
      </div>
    </main>
    <nav
      v-if="session"
      class="mobile-nav fixed bottom-[max(16px,env(safe-area-inset-bottom))] left-1/2 z-40 flex -translate-x-1/2 gap-1 min-[761px]:hidden"
      aria-label="Навигация на телефоне"
    >
      <RouterLink to="/me" :class="{ current: route.path === '/me' }"
        ><span class="dock-icon flex items-center"><Bookmark :size="20" /></span
        ><span>Вишлист</span></RouterLink
      ><RouterLink to="/friends" :class="{ current: route.path !== '/me' }"
        ><span class="dock-icon flex items-center"><Users :size="20" /></span
        ><span>Друзья</span></RouterLink
      >
    </nav>
    <Transition name="toast">
      <ToastMessage v-if="notice" :message="notice" />
    </Transition>
  </div>
</template>
