<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Archive, ArrowLeft, ArrowUpRight, Bookmark, Gift, LockKeyhole, MessageCircle, Plus, RefreshCw, Store } from 'lucide-vue-next'
import { api, itemTitle, send, session, type Item, type User } from '../shared/api'
import { notify } from '../shared/notifications'
import ItemCard from './ItemCard.vue'
import ItemForm from './ItemForm.vue'
import ItemDetail from './ItemDetail.vue'
import Modal from '../shared/Modal.vue'

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
async function saved() { formOpen.value = false; notify('Запись сохранена'); await load(true) }
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
    <header class="page-heading"><div><div class="eyebrow"><span class="tiny-dot" />{{ own ? 'ХОРОШИЕ ИДЕИ НЕ ТЕРЯЮТСЯ' : 'УВИДЕЛ — ВСПОМНИЛ' }}</div><h1>{{ own ? 'Мой вишлист' : profile?.display_name || 'Вишлист друга' }}<span class="heading-dot">.</span></h1><p>{{ own ? 'То, что хочется. Чтобы друзья знали.' : 'Запомнить, что хочется другу. И однажды порадовать.' }}</p></div><button v-if="(own || listType === 'surprise') && !error && !loading" class="button primary add-button" @click="add"><Plus :size="18" />{{ listType === 'surprise' ? 'Добавить сюрприз' : 'Добавить желание' }}</button></header>
    <div v-if="!own" class="profile-tabs"><RouterLink :to="`/users/${recipientId}/wishlist`" :class="{ active: listType === 'wishlist' }"><Bookmark :size="17" />Вишлист</RouterLink><RouterLink :to="`/users/${recipientId}/surprises`" :class="{ active: listType === 'surprise' }"><Gift :size="17" />Сюрпризы<LockKeyhole :size="12" /></RouterLink></div>
    <section v-if="!loading && !error" class="intro-banner" :class="{ 'surprise-banner': listType === 'surprise' }"><div class="banner-icon"><LockKeyhole v-if="listType === 'surprise'" :size="27" :stroke-width="1.7" /><MessageCircle v-else :size="28" :stroke-width="1.7" /></div><div><h2>{{ listType === 'surprise' ? 'Тсс… здесь живут сюрпризы' : own ? 'Я думаю о тебе.' : 'Увидел и вспомнил о тебе' }}</h2><p>{{ listType === 'surprise' ? 'Кажется, тебе понравится. Сохраняйте находки здесь: их увидят друзья, но не получатель.' : own ? 'Иногда это значит: «Запомнил, что ты хотел». Сохраняйте желания — друзьям будет проще вас порадовать.' : 'Можно выбрать что-то из списка или сохранить свою находку в сюрпризы. Её увидят все друзья, кроме получателя.' }}</p></div><ArrowUpRight class="banner-doodle" :size="60" :stroke-width="1.2" aria-hidden="true" /></section>
    <div v-if="loading" class="loading-grid" aria-label="Загрузка"><div v-for="n in 3" :key="n" class="skeleton" /></div>
    <div v-else-if="error" class="empty-state"><RefreshCw :size="32" /><h2>Не получилось загрузить список</h2><p role="alert">{{ error }}</p><button class="button secondary" @click="load()">Попробовать ещё раз</button></div>
    <template v-else>
      <div class="section-heading"><h2>{{ listType === 'surprise' ? 'Секретные идеи' : own ? 'Мои желания' : 'Желания друга' }}<span class="count">{{ wishes.length }}</span></h2><span class="section-note">{{ listType === 'surprise' ? 'Только между нами' : 'На заметку друзьям' }}<Bookmark :size="14" /></span></div>
      <div v-if="!wishes.length" class="empty-state"><Gift :size="38" :stroke-width="1.2" /><h2>{{ archivedItems.length ? 'Все желания пока в архиве' : 'Здесь скоро появится что-то хорошее' }}</h2><p>{{ own ? 'Большая мечта или маленькая радость — начните с первого желания.' : listType === 'surprise' ? 'Станьте автором первого сюрприза. Получатель ничего не узнает.' : 'Ваш друг ещё не добавил пожелания. Загляните чуть позже.' }}</p><button v-if="own || listType === 'surprise'" class="button primary" @click="add"><Plus :size="17" />Добавить {{ listType === 'surprise' ? 'сюрприз' : 'желание' }}</button></div>
      <div v-else class="cards-grid"><ItemCard v-for="(item, index) in wishes" :key="item.id" :item="item" :index="index" @open="detail = $event" @edit="edit" @archive="archive" @delete="deleting = $event; deleteError = ''" /></div>
      <section class="certificates-section" aria-labelledby="certificates-heading"><div class="section-heading"><h2 id="certificates-heading"><Store :size="20" />Сертификаты<span class="count">{{ certificates.length }}</span></h2><button v-if="own || listType === 'surprise'" class="text-button" @click="addCertificate"><Plus :size="17" />Добавить магазин</button></div><p class="certificates-intro">{{ own ? 'Магазины, сертификату из которых вы будете рады.' : listType === 'surprise' ? 'Идеи сертификатов в подарок. Получатель этот раздел не видит.' : 'Магазины, в которые можно подарить сертификат.' }}</p><div v-if="certificates.length" class="cards-grid"><ItemCard v-for="(item, index) in certificates" :key="item.id" :item="item" :index="index" @open="detail = $event" @edit="edit" @archive="archive" @delete="deleting = $event; deleteError = ''" /></div><div v-else class="certificate-empty"><Store :size="23" /><p>{{ own || listType === 'surprise' ? 'Добавьте ссылку на магазин — попробуем подгрузить картинку сами.' : 'Друг пока не добавил магазины для сертификатов.' }}</p></div></section>
      <template v-if="archivedItems.length"><div class="section-heading archive-heading"><h2><Archive :size="17" />Немного истории<span class="count">{{ archivedItems.length }}</span></h2><span class="section-note">Архив желаний</span></div><div class="cards-grid"><ItemCard v-for="(item, index) in archivedItems" :key="item.id" :item="item" :index="index + activeItems.length" @edit="edit" @archive="archive" @delete="deleting = $event; deleteError = ''" /></div></template>
      <div v-if="own && activeItems.length" class="bottom-tip"><Bookmark :size="27" aria-hidden="true" /><p>Книга, поход в горы или что-то для нового хобби?<br /><strong>Не обязательно искать ссылку. Достаточно идеи.</strong></p><button class="text-button" @click="add">Добавить идею<ArrowUpRight :size="16" /></button></div>
    </template>
    <ItemForm v-if="formOpen" :item="editing" :initial-type="initialType" :recipient-id="recipientId" :list-type="listType" @close="formOpen = false" @saved="saved" />
    <ItemDetail v-if="detail" :item="detail" :own-profile="own" :busy="busy" @close="detail = undefined" @edit="edit" @copy="copy" />
    <Modal v-if="deleting" title="Удалить желание?" @close="!busy && (deleting = undefined)"><div class="confirm-body"><p>«{{ itemTitle(deleting) }}» будет удалено навсегда. Это действие нельзя отменить.</p><p v-if="deleteError" class="inline-error" role="alert">{{ deleteError }}</p><div class="form-actions"><button class="button secondary" :disabled="busy" @click="deleting = undefined">Оставить</button><button class="button danger" :disabled="busy" @click="remove">{{ busy ? 'Удаляем…' : 'Удалить навсегда' }}</button></div></div></Modal>
  </div>
</template>
