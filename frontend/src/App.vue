<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowUpRight, Bookmark, Gift, LogOut, MessageCircle, ShieldCheck, Users } from 'lucide-vue-next'
import { api, authReady, clearSession, invalidation, send, session, type Session } from './shared/api'
import { notice } from './shared/notifications'
import { backButton, initData, initTelegram } from './integrations/telegram'

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
    catch { if (initData() && config.value.telegram_enabled) await login() }
  } catch (e) { error.value = (e as Error).message }
  finally { authReady.value = true; busy.value = false }
}
async function logout() {
  try { await send('/auth/logout') } finally { clearSession(); await router.replace('/me') }
}
onMounted(async () => { await initTelegram(); await bootstrap() })
</script>

<template>
  <div class="app-shell">
    <aside v-if="session" class="sidebar">
      <RouterLink to="/me" class="brand"><span class="brand-icon"><Gift :size="23" :stroke-width="1.8" /></span>тепло</RouterLink>
      <p class="brand-caption">ВИШЛИСТЫ ДЛЯ СВОИХ</p>
      <nav class="main-nav" aria-label="Основная навигация">
        <RouterLink to="/me" :class="{ current: route.path === '/me' }"><Bookmark :size="19" />Мой вишлист<span class="nav-dot" /></RouterLink>
        <RouterLink to="/friends" :class="{ current: route.path !== '/me' }"><Users :size="19" />Друзья<ArrowUpRight :size="15" class="nav-arrow" /></RouterLink>
      </nav>
      <div class="sidebar-note"><MessageCircle :size="26" aria-hidden="true" /><p>Увидел —<br />вспомнил<br /><strong>о тебе.</strong></p><span class="note-line" /><small>Для хорошего подарка<br />не обязательно ждать повод.</small></div>
      <div class="sidebar-bottom"><span class="private-label"><ShieldCheck :size="14" />Только для нашей компании</span><div class="account"><span class="account-avatar">{{ session.user.display_name[0] }}</span><div><strong>{{ session.user.display_name }}</strong><span>На одной волне</span></div><button class="icon-button" aria-label="Выйти" title="Выйти" @click="logout"><LogOut :size="17" /></button></div></div>
    </aside>
    <main v-if="session" class="main-content"><div class="topbar"><span>Я думаю о тебе — и сохраняю хорошие идеи</span><span class="topbar-right"><span class="online-dot" />Среди своих<Users :size="16" /></span></div><RouterView :key="`${session.user.id}:${session.community_id}:${invalidation}`" /><footer class="page-footer"><span>Увидел. Вспомнил. Порадовал.</span><span>Для вас и ваших друзей <Users :size="14" /></span></footer></main>
    <main v-else class="login-page"><div class="login-brand brand"><span class="brand-icon"><Gift :size="25" /></span>тепло</div><div class="login-card"><div class="login-art" aria-hidden="true"><MessageCircle :size="76" :stroke-width="1.5" /><Bookmark :size="34" class="login-art-bookmark" /></div><div class="eyebrow">УВИДЕЛ — ВСПОМНИЛ</div><h1>Я думаю<br />о тебе<span class="heading-dot">.</span></h1><p>Здесь собирается то, что хочется запомнить и однажды подарить. Ваши желания, находки для друзей и сюрпризы без повода.</p><div v-if="!authReady" class="muted" role="status">Открываем дверь…</div><template v-else><button v-if="config.dev_login_enabled" class="button primary login-button" :disabled="busy" @click="login(true)">{{ busy ? 'Входим…' : 'Войти в локальную версию' }}<ArrowUpRight :size="18" /></button><button v-else-if="initData() && config.telegram_enabled" class="button primary" :disabled="busy" @click="login()">{{ busy ? 'Проверяем доступ…' : 'Войти через Telegram' }}</button><p v-else-if="!error" class="inline-hint">Откройте приложение через Telegram-бота вашей компании.</p><p v-if="config.dev_login_enabled" class="login-disclaimer"><ShieldCheck :size="14" />Тестовый вход. Данные остаются на этом компьютере.</p><p v-if="error" class="inline-error" role="alert">{{ error }}</p><button v-if="error" class="text-button" @click="bootstrap">Повторить подключение</button></template></div><p class="login-footer">Не про идеальный подарок. Про внимание к своим.</p></main>
    <nav v-if="session" class="mobile-nav" aria-label="Навигация на телефоне"><RouterLink to="/me" :class="{ current: route.path === '/me' }"><Bookmark :size="21" />Мой вишлист</RouterLink><RouterLink to="/friends" :class="{ current: route.path !== '/me' }"><Users :size="21" />Друзья</RouterLink><button @click="logout"><LogOut :size="20" />Выйти</button></nav>
    <Transition name="toast"><div v-if="notice" class="toast-message" role="status"><ShieldCheck :size="18" />{{ notice }}</div></Transition>
  </div>
</template>
