<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowUpRight, Search, Users, UserPlus, UserMinus } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, send, session, type User } from '../shared/api'
import { shareInvitation } from '../integrations/telegram'
import { notify } from '../shared/notifications'
import Modal from '../shared/Modal.vue'
const route = useRoute(), router = useRouter()
const users = ref<User[]>([]), loading = ref(true), error = ref(''), query = ref('')
const invitation = ref<{ url: string; expires_at: string }>(), inviting = ref(false), busy = ref(false), actionError = ref('')
const preview = ref<{ inviter: User; own: boolean }>(), previewError = ref(''), previewLoading = ref(false)
const removing = ref<User>()
const token = computed(() => typeof route.query.invite === 'string' ? route.query.invite : '')
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
async function createInvite() {
  inviting.value = true; busy.value = true; actionError.value = ''; invitation.value = undefined
  try { invitation.value = await send('/friends/invitations') }
  catch (e) { actionError.value = (e as Error).message }
  finally { busy.value = false }
}
async function revoke() {
  busy.value = true; actionError.value = ''
  try { await send('/friends/invitations', undefined, 'DELETE'); invitation.value = undefined; inviting.value = false; notify('Приглашение отозвано') }
  catch (e) { actionError.value = (e as Error).message }
  finally { busy.value = false }
}
async function copyLink() {
  if (!invitation.value) return
  try { await navigator.clipboard.writeText(invitation.value.url); notify('Ссылка скопирована') }
  catch { actionError.value = 'Не удалось скопировать автоматически. Выделите ссылку и скопируйте её вручную.' }
}
let previewGeneration = 0
watch(token, async value => {
  const current = ++previewGeneration
  preview.value = undefined; previewError.value = ''; previewLoading.value = Boolean(value)
  if (!value) return
  if (!/^[A-Za-z0-9_-]{43}$/.test(value)) { previewError.value = 'Приглашение недействительно'; previewLoading.value = false; return }
  try {
    const result = await api<{ inviter: User; own: boolean }>(`/friends/invitations/${encodeURIComponent(value)}`)
    if (current === previewGeneration) preview.value = result
  } catch (e) { if (current === previewGeneration) previewError.value = (e as Error).message }
  finally { if (current === previewGeneration) previewLoading.value = false }
}, { immediate: true })
async function closePreview() { await router.replace({ path: '/friends', query: {} }) }
async function acceptInvite() {
  busy.value = true; previewError.value = ''
  try { await send('/friends/accept', { token: token.value }); await closePreview(); notify('Вы теперь друзья'); await load(true) }
  catch (e) { previewError.value = (e as Error).message }
  finally { busy.value = false }
}
async function removeFriend() {
  if (!removing.value) return
  busy.value = true; actionError.value = ''
  try { await send(`/friends/${removing.value.id}`, undefined, 'DELETE'); removing.value = undefined; notify('Дружба прекращена'); await load(true) }
  catch (e) { actionError.value = (e as Error).message }
  finally { busy.value = false }
}
onMounted(() => { void load(); window.addEventListener('focus', refresh); document.addEventListener('visibilitychange', refresh) })
onBeforeUnmount(() => { generation++; previewGeneration++; window.removeEventListener('focus', refresh); document.removeEventListener('visibilitychange', refresh) })
</script>

<template>
   <div class="page friends-page"><header class="page-heading"><div class="heading-context"><div class="heading-title"><h1>Друзья</h1><span v-if="!loading && !error" class="count">{{ users.length }}</span></div><p class="page-caption">Находки, в которых узнаёшь человека.</p></div></header>
    <div class="friends-toolbar"><label class="search-input"><Search :size="17" /><input v-model="query" aria-label="Найти друга" placeholder="Найти друга" maxlength="120" /></label><button class="button primary" :disabled="busy" @click="createInvite"><UserPlus :size="17" />Пригласить друга</button></div>
    <div v-if="loading" class="loading-grid"><div v-for="n in 3" :key="n" class="skeleton friend-skeleton" /></div>
    <div v-else-if="error" class="empty-state"><h2>Не удалось загрузить друзей</h2><p role="alert">{{ error }}</p><button class="button secondary" @click="load()">Повторить</button></div>
    <div v-else-if="!filtered.length" class="empty-state"><Users :size="36" :stroke-width="1.3" /><h2>{{ query ? 'Никого не нашли' : 'Пока только вы' }}</h2><p>{{ query ? 'Попробуйте другое имя.' : 'Пригласите друга по ссылке. После подтверждения вы сможете видеть вишлисты друг друга — общая группа не нужна.' }}</p></div>
    <div v-else class="friends-grid"><div v-for="(user, index) in filtered" :key="user.id" class="friend-entry"><RouterLink :to="`/users/${user.id}/wishlist`" class="friend-card"><div class="friend-avatar" :class="['art-accent', 'art-ink', 'art-sand'][index % 3]">{{ user.display_name.split(' ').map(n => n[0]).slice(0, 2).join('') }}</div><h3>{{ user.display_name }}</h3><ArrowUpRight :size="18" aria-hidden="true" /></RouterLink><button v-if="user.is_friend" class="text-button remove-friend" :aria-label="`Удалить из друзей: ${user.display_name}`" @click="removing = user; actionError = ''"><UserMinus :size="15" />Удалить из друзей</button></div></div>
    <Modal v-if="inviting" title="Пригласить друга" @close="!busy && (inviting = false)"><div class="confirm-body"><p>Отправьте ссылку тому, с кем хотите делиться желаниями. После подтверждения вы оба получите доступ к вишлистам и фотографиям друг друга.</p><p class="inline-hint">Ссылка для одного друга, действует 7 дней. Новое приглашение отменяет предыдущее. Отправляйте её только лично.</p><p v-if="busy" role="status">Готовим приглашение…</p><template v-if="invitation"><label class="invite-link-label">Ссылка-приглашение<input class="invite-link" :value="invitation.url" readonly @focus="($event.target as HTMLInputElement).select()" /></label><div class="form-actions"><button class="button secondary" @click="copyLink">Скопировать</button><button class="button primary" @click="shareInvitation(invitation.url)">Отправить другу</button></div><button class="text-button" :disabled="busy" @click="revoke">Отозвать ссылку</button></template><p v-if="actionError" class="inline-error" role="alert">{{ actionError }}</p></div></Modal>
    <Modal v-if="token" title="Приглашение в друзья" @close="!busy && closePreview()"><div class="confirm-body"><p v-if="previewLoading" role="status">Проверяем приглашение…</p><template v-if="preview"><h3>{{ preview.inviter.display_name }}</h3><p>{{ preview.own ? 'Это ваше приглашение — отправьте ссылку другу.' : 'Предлагает делиться желаниями. После подтверждения вы сможете смотреть вишлисты и фотографии друг друга.' }}</p><p class="inline-hint">Вы также сможете добавлять сюрпризы для друга. Этот список видят его подтверждённые друзья, но не он сам. Сюрпризы для вас останутся скрыты, групповые списки не открываются. Дружбу можно прекратить в любой момент.</p><button v-if="!preview.own" class="button primary" :disabled="busy" @click="acceptInvite">{{ busy ? 'Добавляем…' : 'Добавить в друзья' }}</button></template><p v-if="previewError" class="inline-error" role="alert">{{ previewError }}</p><button class="text-button" :disabled="busy" @click="closePreview">Не сейчас</button></div></Modal>
    <Modal v-if="removing" title="Удалить из друзей?" @close="!busy && (removing = undefined)"><div class="confirm-body"><p>Вы и {{ removing.display_name }} больше не сможете смотреть вишлисты друг друга по дружбе или списки сюрпризов друг для друга. Уже просмотренные данные отозвать нельзя.</p><p class="inline-hint">Созданные сюрпризы сохранятся для остальных друзей получателя. Если вы состоите в общей группе, доступ к её спискам сохранится.</p><p v-if="actionError" class="inline-error" role="alert">{{ actionError }}</p><div class="form-actions"><button class="button secondary" :disabled="busy" @click="removing = undefined">Оставить</button><button class="button danger" :disabled="busy" @click="removeFriend">Удалить из друзей</button></div></div></Modal>
  </div>
</template>
