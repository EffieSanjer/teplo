<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowUpRight, Search, Users } from 'lucide-vue-next'
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
   <div class="page friends-page"><header class="page-heading"><div class="heading-context"><div class="heading-title"><h1>Друзья</h1><span v-if="!loading && !error" class="count">{{ users.length }}</span></div><p class="page-caption">Находки, в которых узнаёшь человека.</p></div></header>
    <div class="friends-toolbar"><label class="search-input"><Search :size="17" /><input v-model="query" aria-label="Найти друга" placeholder="Найти друга" maxlength="120" /></label></div>
    <div v-if="loading" class="loading-grid"><div v-for="n in 3" :key="n" class="skeleton friend-skeleton" /></div>
    <div v-else-if="error" class="empty-state"><h2>Не удалось загрузить друзей</h2><p role="alert">{{ error }}</p><button class="button secondary" @click="load()">Повторить</button></div>
    <div v-else-if="!filtered.length" class="empty-state"><Users :size="36" :stroke-width="1.3" /><h2>{{ query ? 'Никого не нашли' : 'Ждём друзей' }}</h2><p>{{ query ? 'Попробуйте другое имя.' : 'Участники появятся после первого успешного входа в приложение.' }}</p></div>
    <div v-else class="friends-grid"><RouterLink v-for="(user, index) in filtered" :key="user.id" :to="`/users/${user.id}/wishlist`" class="friend-card"><div class="friend-avatar" :class="['art-accent', 'art-ink', 'art-sand'][index % 3]">{{ user.display_name.split(' ').map(n => n[0]).slice(0, 2).join('') }}</div><h3>{{ user.display_name }}</h3><ArrowUpRight :size="18" aria-hidden="true" /></RouterLink></div>
  </div>
</template>
