<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowUpRight, Bookmark, LogOut, MessageCircle, ShieldCheck, Users } from 'lucide-vue-next';
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
import ThemeControl from './components/ThemeControl.vue';
import StartupScreen from './components/StartupScreen.vue';
import { avatarFallback, sampleAvatarPalette } from './shared/avatarPalette';

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
    clearSession();
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
      if (initData() && config.value.telegram_enabled) await login();
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
  void initTelegram()
    .then(async () => {
      if (disposed) return;
      cleanupLaunch();
      cleanupLaunch = onLaunchChange(resume);
      if (session.value) await openLaunchTarget();
    })
    .catch(() => {});
  await bootstrap();
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
    <div v-if="!session" class="login-theme"><ThemeControl /></div>
    <main v-if="session" class="main-content min-h-dvh">
      <header
        class="topbar mx-auto flex min-h-[72px] max-w-[1440px] items-center gap-4 px-5 min-[761px]:px-10"
      >
        <div class="brand-block">
          <RouterLink to="/me" class="brand" aria-label="Кстати — мой вишлист"
            >кстати<span class="brand-comma">,</span></RouterLink
          >
        </div>
        <nav
          class="main-nav ml-auto hidden items-center gap-1 min-[761px]:flex [&_a]:flex [&_a]:min-h-10 [&_a]:items-center [&_a]:gap-2 [&_a]:rounded [&_a]:px-4 [&_a]:text-sm [&_a.current]:bg-forest [&_a.current]:text-paper"
          aria-label="Основная навигация"
        >
          <RouterLink to="/me" :class="{ current: route.path === '/me' }"
            ><Bookmark :size="18" />Мой вишлист</RouterLink
          >
          <RouterLink to="/friends" :class="{ current: route.path !== '/me' }"
            ><Users :size="18" />Друзья</RouterLink
          >
        </nav>
        <div v-if="route.path !== '/friends'" class="appearance-control ml-auto min-[761px]:ml-0">
          <ThemeControl />
        </div>
        <div v-if="showAccountControls" class="topbar-actions flex items-center gap-2">
          <ThemeControl v-if="route.path !== '/friends'" /><button
            class="icon-button logout-button"
            aria-label="Выйти"
            :title="`Выйти · ${session.user.display_name}`"
            @click="logout"
          >
            <LogOut :size="19" />
          </button>
        </div>
      </header>
      <RouterView
        :key="`${session.user.id}:${session.community_id}:${invalidation}`"
        v-slot="{ Component }"
        ><Transition name="page" mode="out-in"><component :is="Component" /></Transition
      ></RouterView>
    </main>
    <main v-else class="login-page welcome-page">
      <div class="login-brand brand">кстати<span class="brand-comma">,</span></div>
      <div class="welcome-copy">
        <span class="text-[10px] tracking-[.18em] uppercase text-muted"
          >Для тебя и твоих людей</span
        >
        <h1 class="mt-5 font-editorial text-[clamp(42px,7vw,76px)] leading-[1.05] tracking-tight">
          Это тебе<br /><em>идеально подойдёт.</em>
        </h1>
        <p class="mt-5 max-w-sm text-sm leading-relaxed text-muted">
          Место для маленьких подсказок и больших желаний. Сохраняй то, что любишь, и находи подарки
          для своих.
        </p>
      </div>
      <div class="login-card welcome-card">
        <div class="login-art" aria-hidden="true">
          <Bookmark :size="28" :stroke-width="1.2" />
        </div>
        <h2 class="font-editorial text-2xl">Твой список начинается здесь</h2>
        <p>Вишлисты друзей, любимые магазины и сюрпризы — рядом.</p>
        <div v-if="!authReady" class="muted" role="status">Загрузка…</div>
        <template v-else
          ><button
            v-if="config.dev_login_enabled"
            class="button primary login-button"
            :disabled="busy"
            @click="login(true)"
          >
            {{ busy ? 'Входим…' : 'Войти в локальную версию' }}<ArrowUpRight :size="18" /></button
          ><button
            v-else-if="initData() && config.telegram_enabled"
            class="button primary"
            :disabled="busy"
            @click="login()"
          >
            {{ busy ? 'Проверяем доступ…' : 'Войти' }}
          </button>
          <p v-else-if="!error" class="inline-hint">Откройте приложение через бота.</p>
          <p v-if="config.dev_login_enabled" class="login-disclaimer">
            <ShieldCheck :size="14" />Локальная тестовая версия
          </p>
          <p v-if="error" class="inline-error" role="alert">{{ error }}</p>
          <button v-if="error" class="text-button" @click="bootstrap">
            Повторить подключение
          </button></template
        >
      </div>
    </main>
    <nav
      v-if="session"
      class="mobile-nav fixed bottom-[max(16px,env(safe-area-inset-bottom))] left-1/2 z-40 flex -translate-x-1/2 gap-1 rounded-full border border-line bg-paper p-1.5 shadow-lg min-[761px]:hidden dark:border-[#475349] dark:bg-[#202823] [&_a]:flex [&_a]:min-h-12 [&_a]:min-w-28 [&_a]:items-center [&_a]:justify-center [&_a]:gap-2 [&_a]:rounded-full [&_a]:px-4 [&_a]:text-xs [&_a.current]:bg-forest [&_a.current]:text-paper"
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
    <Transition name="toast"
      ><div v-if="notice" class="toast-message" role="status">
        <ShieldCheck :size="18" />{{ notice }}
      </div></Transition
    >
  </div>
</template>
