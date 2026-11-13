<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, Bookmark, LogOut, MessageCircle, ShieldCheck, Users } from 'lucide-vue-next'
import { ApiError, api, authReady, clearSession, invalidation, send, session, type Session } from './shared/api'
import { notice } from './shared/notifications'
import { backButton, initData, initTelegram } from './integrations/telegram'
import ThemeControl from './shared/ThemeControl.vue'

const config = ref({ dev_login_enabled: false, telegram_enabled: false }), error = ref(''), busy = ref(false)
const route = useRoute(), router = useRouter()
let cleanupBack = () => {}
watch(() => route.path, () => {
  cleanupBack(); cleanupBack = backButton(route.path !== '/me', () => { void router.push(route.path.startsWith('/users/') ? '/friends' : '/me') })
})
async function login(dev = false) {
  busy.value = true; error.value = ''
  try {
    clearSession()
    session.value = await send<Session>(dev ? '/auth/dev' : '/auth/telegram', dev ? undefined : { init_data: initData() })
    if (new URLSearchParams(initData()).get('start_param') === 'friends') await router.replace('/friends')
  } catch (e) { error.value = (e as Error).message }
  finally { busy.value = false }
}
async function bootstrap() {
  error.value = ''; busy.value = true
  try {
    config.value = await api('/auth/config')
    try { session.value = await api<Session>('/auth/session') }
    catch (e) {
      if (!(e instanceof ApiError) || e.status !== 401) throw e
      if (initData() && config.value.telegram_enabled) await login()
    }
  } catch (e) { error.value = (e as Error).message }
  finally { authReady.value = true; busy.value = false }
}
async function logout() {
  try { await send('/auth/logout') } finally { clearSession(); await router.replace('/me') }
}
onMounted(async () => {
  // Launch credentials are captured locally; an unreachable optional SDK must
  // not delay authentication or leave the initial screen waiting for it.
  void initTelegram().catch(() => {})
  await bootstrap()
})
</script>

<template>
  <div class="app-shell">
    <div v-if="!session" class="login-theme"><ThemeControl /></div>
    <main v-if="session" class="main-content">
      <header class="topbar">
        <div class="brand-block"><RouterLink to="/me" class="brand" aria-label="Кстати — мой вишлист">кстати<span class="brand-comma">,</span></RouterLink><p class="brand-description">Желания и находки для друзей</p></div>
        <nav class="main-nav" aria-label="Основная навигация">
          <RouterLink to="/me" :class="{ current: route.path === '/me' }"><Bookmark :size="18" />Мой вишлист</RouterLink>
          <RouterLink to="/friends" :class="{ current: route.path !== '/me' }"><Users :size="18" />Друзья</RouterLink>
        </nav>
        <div class="topbar-actions"><ThemeControl /><button class="icon-button logout-button" aria-label="Выйти" :title="`Выйти · ${session.user.display_name}`" @click="logout"><LogOut :size="19" /></button></div>
      </header>
      <RouterView :key="`${session.user.id}:${session.community_id}:${invalidation}`" />
    </main>
    <main v-else class="login-page"><div class="login-brand brand"><span class="brand-icon"><MessageCircle :size="25" /></span>кстати<span class="brand-comma">,</span></div><div class="login-card"><div class="login-art" aria-hidden="true"><MessageCircle :size="76" :stroke-width="1.5" /><Bookmark :size="34" class="login-art-bookmark" /></div><h1>Кстати, это тебе<br />идеально подойдёт<span class="heading-dot">.</span></h1><p>Свои желания и находки для друзей.</p><div v-if="!authReady" class="muted" role="status">Собираем находки…</div><template v-else><button v-if="config.dev_login_enabled" class="button primary login-button" :disabled="busy" @click="login(true)">{{ busy ? 'Входим…' : 'Войти в локальную версию' }}<ArrowUpRight :size="18" /></button><button v-else-if="initData() && config.telegram_enabled" class="button primary" :disabled="busy" @click="login()">{{ busy ? 'Проверяем доступ…' : 'Войти' }}</button><p v-else-if="!error" class="inline-hint">Откройте приложение через бота вашей компании.</p><p v-if="config.dev_login_enabled" class="login-disclaimer"><ShieldCheck :size="14" />Локальная тестовая версия</p><p v-if="error" class="inline-error" role="alert">{{ error }}</p><button v-if="error" class="text-button" @click="bootstrap">Повторить подключение</button></template></div><p class="login-footer">Не обязательно покупать. Иногда достаточно заметить.</p></main>
    <nav v-if="session" class="mobile-nav" aria-label="Навигация на телефоне"><RouterLink to="/me" :class="{ current: route.path === '/me' }"><Bookmark :size="20" />Вишлист</RouterLink><RouterLink to="/friends" :class="{ current: route.path !== '/me' }"><Users :size="20" />Друзья</RouterLink></nav>
    <Transition name="toast"><div v-if="notice" class="toast-message" role="status"><ShieldCheck :size="18" />{{ notice }}</div></Transition>
  </div>
</template>
