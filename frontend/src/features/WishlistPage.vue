<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Bookmark, Gift, LockKeyhole, Plus, RefreshCw, Store } from 'lucide-vue-next'
import { api, itemTitle, send, session, type Item, type User } from '../shared/api'
import { notify } from '../shared/notifications'
import ItemCard from './ItemCard.vue'
import ItemForm from './ItemForm.vue'
import ItemDetail from './ItemDetail.vue'
import Modal from '../shared/Modal.vue'
import MasonryGrid from '../shared/MasonryGrid.vue'

const route = useRoute(), router = useRouter()
const own = computed(() => !route.params.id || route.params.id === session.value?.user.id)
const recipientId = computed(() => String(route.params.id || session.value?.user.id || ''))
const listType = computed(() => route.path.endsWith('/surprises') ? 'surprise' : 'wishlist')
const items = ref<Item[]>([]), profile = ref<User | null>(null), loading = ref(true), error = ref('')
const formOpen = ref(false), editing = ref<Item>(), detail = ref<Item>(), deleting = ref<Item>()
const initialType = ref<Item['item_type']>('idea')
const busy = ref(false), deleteError = ref('')
const activeItems = computed(() => items.value.filter(i => !i.archived_at))
const wishes = computed(() => activeItems.value.filter(i => i.item_type !== 'certificate'))
const certificates = computed(() => activeItems.value.filter(i => i.item_type === 'certificate'))
const archivedItems = computed(() => items.value.filter(i => i.archived_at))
const galleryItems = computed(() => [...wishes.value, ...archivedItems.value])
let generation = 0, lastRefresh = 0

async function load(quiet = false) {
  const current = ++generation
  if (own.value && listType.value === 'surprise') { await router.replace('/me'); return }
  const id = recipientId.value, type = listType.value
  if (!quiet) { loading.value = true; items.value = []; profile.value = null; detail.value = undefined; formOpen.value = false }
  error.value = ''
  try {
    const [user, data] = await Promise.all([api<User>(`/users/${id}`), api<Item[]>(`/users/${id}/items/${type}`)])
    if (current !== generation || !session.value) return
    profile.value = user; items.value = data; lastRefresh = Date.now()
  } catch (e) { if (current === generation) { error.value = (e as Error).message; items.value = []; profile.value = null; detail.value = undefined; formOpen.value = false } }
  finally { if (current === generation) loading.value = false }
}
watch(() => route.fullPath, () => load(), { immediate: true })

function add() { initialType.value = 'idea'; editing.value = undefined; formOpen.value = true }
function addCertificate() { initialType.value = 'certificate'; editing.value = undefined; formOpen.value = true }
function edit(item: Item) { detail.value = undefined; editing.value = item; formOpen.value = true }
async function saved() {
  formOpen.value = false
  notify(listType.value === 'surprise' && !editing.value ? 'Сохранено для того самого «это точно твоё»' : 'Запись сохранена')
  await load(true)
}
async function archive(item: Item) {
  try { await send(`/items/${item.id}/archive`, { archived: !item.archived_at }); notify(item.archived_at ? 'Желание снова в списке' : 'Желание перенесено в архив'); await load(true) }
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
  <div class="page wishlist-page">
    <RouterLink v-if="!own" to="/friends" class="back-link"><ArrowLeft :size="15" />Все друзья</RouterLink>
    <header class="page-heading"><div class="heading-context"><div class="heading-title"><h1>{{ own ? 'Мой вишлист' : profile?.display_name || 'Вишлист друга' }}</h1><span v-if="!loading && !error" class="count" :aria-label="`Активных записей: ${activeItems.length}`">{{ activeItems.length }}</span></div><p v-if="own" class="page-caption">То, в чём друзья узнают вас.</p></div><button v-if="(own || listType === 'surprise') && !error && !loading" class="button primary add-button" :aria-label="listType === 'surprise' ? 'Добавить сюрприз' : 'Добавить желание'" @click="add"><Plus :size="18" /><span>Добавить</span></button></header>
    <div v-if="!own" class="profile-tabs"><RouterLink :to="`/users/${recipientId}/wishlist`" :class="{ active: listType === 'wishlist' }"><Bookmark :size="17" />Вишлист</RouterLink><RouterLink v-if="profile?.can_surprise" :to="`/users/${recipientId}/surprises`" :class="{ active: listType === 'surprise' }"><Gift :size="17" />Сюрпризы<LockKeyhole :size="12" /></RouterLink></div>
    <p v-if="!own && profile?.is_friend && listType === 'surprise'" class="inline-hint">Этот список видят подтверждённые друзья получателя, в том числе добавленные позже. Получатель его не видит. Групповые сюрпризы хранятся отдельно.</p>
    <div v-if="!loading && !error && !own && listType === 'surprise'" class="list-note"><LockKeyhole :size="16" aria-hidden="true" /><div><p class="surprise-whisper">Тсс… здесь живут сюрпризы для того самого «это точно твоё».</p><p>Видят друзья, но не получатель.</p></div></div>
    <div v-if="loading" class="loading-grid" aria-label="Загрузка"><div v-for="n in 4" :key="n" class="skeleton" /></div>
    <div v-else-if="error" class="empty-state"><RefreshCw :size="32" /><h2>Не получилось загрузить список</h2><p role="alert">{{ error }}</p><button class="button secondary" @click="load()">Попробовать ещё раз</button></div>
    <template v-else>
      <h2 class="visually-hidden">{{ listType === 'surprise' ? 'Секретные идеи' : own ? 'Мои желания' : 'Желания друга' }}</h2>
      <div v-if="!galleryItems.length && !certificates.length" class="empty-state"><Gift :size="38" :stroke-width="1.2" /><h2>Пока нет желаний</h2><p>{{ own ? 'Добавьте вещь, впечатление или идею.' : listType === 'surprise' ? 'Добавьте первую находку. Получатель её не увидит.' : 'Друг ещё не добавил пожелания.' }}</p><button v-if="own || listType === 'surprise'" class="button primary" @click="add"><Plus :size="17" />Добавить {{ listType === 'surprise' ? 'сюрприз' : 'желание' }}</button></div>
      <MasonryGrid v-if="galleryItems.length"><ItemCard v-for="(item, index) in galleryItems" :key="item.id" :item="item" :index="index" @open="detail = $event" @edit="edit" @archive="archive" @delete="deleting = $event; deleteError = ''" /></MasonryGrid>
      <section class="certificates-section" aria-labelledby="certificates-heading"><div class="section-heading"><h2 id="certificates-heading"><Store :size="18" />Сертификаты<span class="count">{{ certificates.length }}</span></h2><button v-if="own || listType === 'surprise'" class="text-button" @click="addCertificate"><Plus :size="17" /><span>Добавить магазин</span></button></div><div v-if="certificates.length" class="certificate-rail" tabindex="0" role="group" aria-label="Магазины для сертификатов, горизонтальная лента"><ItemCard v-for="(item, index) in certificates" :key="item.id" :item="item" :index="index" @open="detail = $event" @edit="edit" @archive="archive" @delete="deleting = $event; deleteError = ''" /></div><p v-else class="certificate-empty">{{ own || listType === 'surprise' ? 'Любимые магазины для подарочных карт' : 'Магазины пока не добавлены' }}</p></section>
    </template>
    <ItemForm v-if="formOpen" :item="editing" :initial-type="initialType" :recipient-id="recipientId" :list-type="listType" @close="formOpen = false" @saved="saved" />
    <ItemDetail v-if="detail" :item="detail" :own-profile="own" :can-surprise="Boolean(profile?.can_surprise)" :busy="busy" @close="detail = undefined" @edit="edit" @copy="copy" />
    <Modal v-if="deleting" title="Удалить желание?" @close="!busy && (deleting = undefined)"><div class="confirm-body"><p>«{{ itemTitle(deleting) }}» будет удалено навсегда. Это действие нельзя отменить.</p><p v-if="deleteError" class="inline-error" role="alert">{{ deleteError }}</p><div class="form-actions"><button class="button secondary" :disabled="busy" @click="deleting = undefined">Оставить</button><button class="button danger" :disabled="busy" @click="remove">{{ busy ? 'Удаляем…' : 'Удалить навсегда' }}</button></div></div></Modal>
  </div>
</template>
