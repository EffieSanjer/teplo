<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Archive, ArrowLeft, Bookmark, ChevronDown, Gift, LoaderCircle, LockKeyhole, Plus, RefreshCw } from 'lucide-vue-next'
import { api, itemTitle, send, session, type Item, type User } from '../shared/api'
import { notify } from '../shared/notifications'
import ItemCard from './ItemCard.vue'
import ItemForm from './ItemForm.vue'
import ItemDetail from './ItemDetail.vue'
import FriendProfile from './FriendProfile.vue'
import CertificateCarousel from './CertificateCarousel.vue'
import Modal from '../shared/Modal.vue'
import ThemeControl from '../shared/ThemeControl.vue'
import type { CardOrigin } from '../shared/cardTransition'
import MasonryGrid from '../shared/MasonryGrid.vue'
import { avatarFallback, sampleAvatarPalette, portraitInk, type AvatarPalette } from '../shared/avatarPalette'
import { theme } from '../shared/theme'

const route = useRoute(), router = useRouter()
const own = computed(() => !route.params.id || route.params.id === session.value?.user.id)
const recipientId = computed(() => String(route.params.id || session.value?.user.id || ''))
const listType = computed(() => route.path.endsWith('/surprises') ? 'surprise' : 'wishlist')
const items = ref<Item[]>([]), profile = ref<User | null>(null), loading = ref(true), error = ref('')
const formOpen = ref(false), editing = ref<Item>(), detail = ref<Item>(), deleting = ref<Item>()
const detailOrigin = ref<CardOrigin>()
function openDetail(item: Item, origin: CardOrigin) { detailOrigin.value = origin; detail.value = item }
const initialType = ref<Item['item_type']>('idea')
const busy = ref(false), deleteError = ref('')
const avatarFailed = ref(false)
const avatarPalette = ref<AvatarPalette>()
const friendCounts = ref({ wishes: 0, surprises: 0 })
const avatarStyle = computed(() => ({
  '--contrast-ink': portraitInk((avatarPalette.value || avatarFallback(recipientId.value)).primary, theme.value === 'dark'),
  '--avatar-tone': (avatarPalette.value || avatarFallback(recipientId.value)).primary,
  '--avatar-secondary': (avatarPalette.value || avatarFallback(recipientId.value)).secondary,
}))
const ownName = computed(() => session.value?.user.display_name || '')
const ownInitials = computed(() => ownName.value.split(/\s+/).map(part => part[0]).slice(0, 2).join(''))
watch(() => session.value?.user.id, () => { avatarFailed.value = false; avatarPalette.value = undefined })
function avatarLoaded(event: Event) { avatarPalette.value = sampleAvatarPalette(event.target as HTMLImageElement) }
watchEffect((onCleanup) => {
  if (!own.value) return
  const tone = (avatarPalette.value || avatarFallback(recipientId.value)).primary
  document.documentElement.style.setProperty('--profile-canvas-tone', tone)
  document.documentElement.style.setProperty('--page-contrast-ink', portraitInk(tone, theme.value === 'dark'))
  onCleanup(() => {
    document.documentElement.style.removeProperty('--profile-canvas-tone')
    document.documentElement.style.removeProperty('--page-contrast-ink')
  })
})
const activeItems = computed(() => items.value.filter(i => !i.archived_at))
const wishes = computed(() => activeItems.value.filter(i => i.item_type !== 'certificate'))
const certificates = computed(() => activeItems.value.filter(i => i.item_type === 'certificate'))
const archivedItems = computed(() => items.value.filter(i => i.archived_at))
let generation = 0, lastRefresh = 0

async function load(quiet = false) {
  const current = ++generation
  if (own.value && listType.value === 'surprise') { await router.replace('/me'); return }
  const id = recipientId.value, type = listType.value
  // Keep the verified heading while switching this person's tabs. Never reuse
  // another recipient's profile or show the previous tab's records while loading.
   if (profile.value?.id !== id) { profile.value = null; friendCounts.value = { wishes: 0, surprises: 0 } }
  if (!quiet) { loading.value = true; items.value = []; detail.value = undefined; formOpen.value = false; deleting.value = undefined }
  error.value = ''
  try {
    const [user, data] = await Promise.all([api<User>(`/users/${id}`), api<Item[]>(`/users/${id}/items/${type}`)])
    if (current !== generation || !session.value) return
    profile.value = user; items.value = data; lastRefresh = Date.now()
    if (!own.value) {
      const count = (entries: Item[]) => entries.filter(item => !item.archived_at && item.item_type !== 'certificate').length
      const otherType = type === 'wishlist' ? 'surprise' : 'wishlist'
      friendCounts.value[type === 'wishlist' ? 'wishes' : 'surprises'] = count(data)
      if (otherType === 'wishlist' || user.can_surprise) {
        void api<Item[]>(`/users/${id}/items/${otherType}`).then(entries => {
          if (current === generation) friendCounts.value[otherType === 'wishlist' ? 'wishes' : 'surprises'] = count(entries)
        }).catch(() => { /* A secondary counter must not block the visible list. */ })
      }
    }
  } catch (e) { if (current === generation) { error.value = (e as Error).message; items.value = []; profile.value = null; detail.value = undefined; formOpen.value = false } }
  finally { if (current === generation) loading.value = false }
}
watch(() => route.fullPath, () => load(), { immediate: true })

function add() { initialType.value = 'idea'; editing.value = undefined; formOpen.value = true }
function addCertificate() { initialType.value = 'certificate'; editing.value = undefined; formOpen.value = true }
function edit(item: Item) { detail.value = undefined; editing.value = item; formOpen.value = true }
async function saved() {
  formOpen.value = false
  notify('Запись сохранена')
  await load(true)
}
async function archive(item: Item) {
   try { await send(`/items/${item.id}/archive`, { archived: !item.archived_at }); detail.value = undefined; notify(item.archived_at ? 'Желание снова в списке' : 'Желание перенесено в архив'); await load(true) }
  catch (e) { notify((e as Error).message) }
}
async function remove() {
  if (!deleting.value) return
  busy.value = true; deleteError.value = ''
  try { await send(`/items/${deleting.value.id}`, undefined, 'DELETE'); deleting.value = undefined; notify('Запись удалена'); await load(true) }
  catch (e) { deleteError.value = (e as Error).message }
  finally { busy.value = false }
}
async function copy(item: Item) {
  busy.value = true
  try { await send(`/items/${item.id}/surprise`); detail.value = undefined; notify('Сюрприз создан. Исходное желание не изменилось'); await router.push(`/users/${recipientId.value}/surprises`) }
  catch (e) { notify((e as Error).message) }
  finally { busy.value = false }
}
function refresh() {
  if (document.visibilityState === 'visible' && Date.now() - lastRefresh > 15000 && !formOpen.value && !detail.value) void load(true)
}
onMounted(() => { window.addEventListener('focus', refresh); document.addEventListener('visibilitychange', refresh) })
onBeforeUnmount(() => { generation++; window.removeEventListener('focus', refresh); document.removeEventListener('visibilitychange', refresh) })
</script>

<template>
  <div class="page wishlist-page" :class="{ 'own-wishlist': own }">
    <div class="wishlist-layout">
    <aside class="wishlist-sidebar" aria-label="Профиль вишлиста">
    <FriendProfile v-if="!own && profile" :key="profile.id" :user="profile" prominent>
      <template #heading><RouterLink to="/friends" class="back-link" aria-label="Вернуться к друзьям"><ArrowLeft :size="20" /></RouterLink><RouterLink to="/me" class="brand" aria-label="Кстати — мой вишлист">кстати<span class="brand-comma">,</span></RouterLink></template>
      <template #stats-left><strong>{{ friendCounts.wishes }}</strong><span>желания</span></template>
      <template #stats-right><strong>{{ friendCounts.surprises }}</strong><span>сюрпризы</span></template>
      <RouterLink :to="`/users/${recipientId}/wishlist`" :class="{ active: listType === 'wishlist' }"><Bookmark :size="16" />Вишлист</RouterLink><RouterLink v-if="profile.can_surprise" :to="`/users/${recipientId}/surprises`" :class="{ active: listType === 'surprise' }"><Gift :size="16" />Сюрпризы</RouterLink>
    </FriendProfile>
    <header v-if="own" class="personal-intro" :class="{ 'has-profile-photo': !avatarFailed }" :style="{ ...avatarStyle, ...(!avatarFailed ? { '--profile-photo': `url('/api/v1/users/${encodeURIComponent(recipientId)}/avatar')` } : {}) }">
      <div class="profile-topbar"><RouterLink to="/me" class="brand" aria-label="Кстати — мой вишлист">кстати<span class="brand-comma">,</span></RouterLink><ThemeControl /></div>
      <div class="profile-editorial-copy"><p>Маленькие подсказки.<br />Хорошие подарки.</p><span>Ваш личный вишлист</span></div>
      <div class="personal-panel" :class="{ 'has-avatar-cover': !avatarFailed }" :style="!avatarFailed ? { '--avatar-cover': `url('/api/v1/users/${encodeURIComponent(recipientId)}/avatar')` } : undefined">
      <div class="personal-identity">
        <div class="profile-stat"><strong>{{ loading ? '—' : wishes.length }}</strong><span>желания</span></div>
        <div class="personal-avatar"><img v-if="!avatarFailed" :src="`/api/v1/users/${encodeURIComponent(recipientId)}/avatar`" alt="" @load="avatarLoaded" @error="avatarFailed = true" /><span v-else>{{ ownInitials }}</span></div>
        <div class="profile-stat"><strong>{{ loading ? '—' : certificates.length }}</strong><span>сертификаты</span></div>
      </div>
      <div class="personal-name"><p>{{ ownName }}</p></div>
      <div class="personal-heading"><div><h1>Вишлист</h1><p>Вещи · Идеи · Впечатления</p></div></div>
      <button v-if="!error" class="button primary personal-add" :disabled="loading" aria-label="Добавить желание" @click="add"><Plus :size="18" /><span>Добавить желание</span></button>
      </div>
      <button v-if="!error" class="profile-cover-add icon-button" :disabled="loading" aria-label="Добавить желание" @click="add"><Plus :size="26" /></button>
    </header>
    </aside>
    <section class="collection-board" aria-label="Коллекция желаний">
    <header v-if="!own && !profile" class="page-heading"><div class="heading-context"><div class="heading-title"><h1 v-if="loading" class="profile-name-skeleton" aria-label="Загрузка профиля"><span class="skeleton" /></h1><h1 v-else>Вишлист друга</h1></div></div></header>
    <div class="wishlist-content" :aria-busy="loading">
    <Transition name="list-content" mode="out-in">
    <div v-if="loading" key="loading" class="list-loading" role="status" aria-label="Загрузка списка"><p class="loading-label"><LoaderCircle class="spin" :size="16" aria-hidden="true" />Загрузка…</p><div class="loading-grid" aria-hidden="true"><div v-for="n in 4" :key="n" class="skeleton" /></div></div>
    <div v-else-if="error" key="error" class="empty-state"><RefreshCw :size="32" /><h2>Не получилось загрузить список</h2><p role="alert">{{ error }}</p><button class="button secondary" @click="load()">Попробовать ещё раз</button></div>
    <div v-else :key="`${recipientId}-${listType}`" class="list-content">
      <div v-if="!own && listType === 'surprise'" class="list-note"><LockKeyhole :size="16" aria-hidden="true" /><p>Получатель не видит этот список.</p></div>
      <h2 class="visually-hidden">{{ listType === 'surprise' ? 'Секретные идеи' : own ? 'Мои желания' : 'Желания друга' }}</h2>
       <div class="collection-heading"><div v-if="!own"><span class="collection-eyebrow">{{ listType === 'surprise' ? 'ТОЛЬКО ДЛЯ ДРУЗЕЙ' : 'ЛИЧНАЯ КОЛЛЕКЦИЯ' }}</span><h2>{{ listType === 'surprise' ? 'Секретные идеи' : 'Желания' }}<span>{{ wishes.length }}</span></h2></div><button v-if="(own || listType === 'surprise') && !error" class="collection-add icon-button" :aria-label="listType === 'surprise' ? 'Добавить сюрприз' : 'Добавить желание'" @click="add"><Plus :size="20" /></button></div>
      <CertificateCarousel :items="certificates" :can-add="own || listType === 'surprise'" @add="addCertificate" @open="openDetail" />
      <MasonryGrid class="collection-grid">
      <ItemCard v-for="(item, index) in wishes" :key="item.id" :item="item" :index="index" @open="openDetail" />
      </MasonryGrid>
      <div v-if="!wishes.length && !certificates.length" class="empty-state collection-empty"><Gift :size="38" :stroke-width="1.2" /><h2>Пока нет желаний</h2><p>{{ own ? 'Добавьте вещь, впечатление или идею.' : listType === 'surprise' ? 'Добавьте первую находку. Получатель её не увидит.' : 'Друг ещё не добавил пожелания.' }}</p><button v-if="own || listType === 'surprise'" class="button primary" @click="add"><Plus :size="17" />Добавить {{ listType === 'surprise' ? 'сюрприз' : 'желание' }}</button></div>
      <details v-if="archivedItems.length" class="collection-archive"><summary><Archive :size="16" /><span>Архив</span><span class="count">{{ archivedItems.length }}</span><ChevronDown :size="16" /></summary><MasonryGrid class="collection-grid"><ItemCard v-for="(item, index) in archivedItems" :key="item.id" :item="item" :index="index" @open="openDetail" /></MasonryGrid></details>
    </div>
    </Transition>
    </div>
    </section>
    </div>
    <ItemForm v-if="formOpen" :item="editing" :initial-type="initialType" :recipient-id="recipientId" :list-type="listType" @close="formOpen = false" @saved="saved" />
    <ItemDetail v-if="detail" :item="detail" :origin="detailOrigin" :own-profile="own" :can-surprise="Boolean(profile?.can_surprise)" :busy="busy" @close="detail = undefined" @edit="edit" @copy="copy" @archive="archive" @delete="deleting = $event; deleteError = ''; detail = undefined" />
    <Modal v-if="deleting" title="Удалить желание?" @close="!busy && (deleting = undefined)"><div class="confirm-body"><p>«{{ itemTitle(deleting) }}» будет удалено навсегда. Это действие нельзя отменить.</p><p v-if="deleteError" class="inline-error" role="alert">{{ deleteError }}</p><div class="form-actions"><button class="button secondary" :disabled="busy" @click="deleting = undefined">Оставить</button><button class="button danger" :disabled="busy" @click="remove">{{ busy ? 'Удаляем…' : 'Удалить навсегда' }}</button></div></div></Modal>
  </div>
</template>
