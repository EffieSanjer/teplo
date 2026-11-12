<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowUpRight, MessageCircle, Search, Users } from 'lucide-vue-next'
import { computed } from 'vue'
import { api, session, type User } from '../shared/api'
const users = ref<User[]>([]), loading = ref(true), error = ref(''), query = ref('')
const filtered = computed(() => users.value.filter(u => u.display_name.toLocaleLowerCase().includes(query.value.toLocaleLowerCase())))
let generation = 0, last = 0
async function load(quiet = false) {
  const current = ++generation
  if (!quiet) loading.value = true
  error.value = ''
  try { const result = await api<User[]>('/users'); if (current === generation && session.value) users.value = result; last = Date.now() }
  catch (e) { if (current === generation) { error.value = (e as Error).message; users.value = [] } }
  finally { if (current === generation) loading.value = false }
}
function refresh() { if (document.visibilityState === 'visible' && Date.now() - last > 15000) void load(true) }
onMounted(() => { void load(); window.addEventListener('focus', refresh); document.addEventListener('visibilitychange', refresh) })
onBeforeUnmount(() => { generation++; window.removeEventListener('focus', refresh); document.removeEventListener('visibilitychange', refresh) })
</script>

<template>
   <div class="page"><header class="page-heading"><div><div class="eyebrow"><span class="tiny-dot" />ХОРОШО, КОГДА ЕСТЬ СВОИ</div><h1>Друзья<span class="heading-dot">.</span></h1><p>Те, о ком вспоминаешь, когда находишь что-то классное.</p></div><div class="friends-symbol"><Users :size="32" :stroke-width="1.7" /></div></header>
    <section class="intro-banner"><div class="banner-icon"><MessageCircle :size="28" :stroke-width="1.7" /></div><div><h2>«Кажется, тебе понравится»</h2><p>Знакомое чувство? Загляните к другу и сохраните находку в сюрпризы. Повод найдётся потом.</p></div><ArrowUpRight class="banner-doodle" :size="60" :stroke-width="1.2" aria-hidden="true" /></section>
    <div class="friends-toolbar"><h2>Наша компания<span class="count">{{ users.length }}</span></h2><label class="search-input"><Search :size="17" /><input v-model="query" aria-label="Найти друга" placeholder="Найти друга" maxlength="120" /></label></div>
    <div v-if="loading" class="loading-grid"><div v-for="n in 3" :key="n" class="skeleton friend-skeleton" /></div>
    <div v-else-if="error" class="empty-state"><h2>Не удалось загрузить друзей</h2><p role="alert">{{ error }}</p><button class="button secondary" @click="load()">Повторить</button></div>
    <div v-else-if="!filtered.length" class="empty-state"><Users :size="36" :stroke-width="1.3" /><h2>{{ query ? 'Никого не нашли' : 'Ждём друзей' }}</h2><p>{{ query ? 'Попробуйте другое имя.' : 'Участники появятся после первого успешного входа в приложение.' }}</p></div>
    <div v-else class="friends-grid"><RouterLink v-for="(user, index) in filtered" :key="user.id" :to="`/users/${user.id}/wishlist`" class="friend-card"><div class="friend-avatar" :class="['art-blue', 'art-ink', 'art-orange'][index % 3]">{{ user.display_name.split(' ').map(n => n[0]).slice(0, 2).join('') }}</div><h3>{{ user.display_name }}</h3><p>Желания и идеи для сюрпризов</p><span>Заглянуть в вишлист<ArrowUpRight :size="16" /></span></RouterLink></div>
  </div>
</template>
