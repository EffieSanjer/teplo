<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import { Gift, ImagePlus, Lightbulb, Link, LoaderCircle, Sparkles, Store, X } from 'lucide-vue-next'
import Modal from '../shared/Modal.vue'
import { api, imageUrl, send, type Item, type ItemCreate, type ItemInput, type Metadata } from '../shared/api'
import { extractSharedDetails, type SharedDetails } from '../shared/sharedLink'
import WishImage from '../shared/WishImage.vue'

const props = defineProps<{ item?: Item; recipientId: string; listType: 'wishlist' | 'surprise'; initialType?: ItemInput['item_type'] }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const form = reactive({
  item_type: props.item?.item_type || props.initialType || 'idea' as ItemInput['item_type'],
  title: props.item?.title || '', description: props.item?.description || '', url: props.item?.url || '',
  price: props.item?.price?.toString() || '', currency: props.item?.currency || 'RUB', image_id: props.item?.image_id || null as string | null,
  price_mode: props.item?.price_mode || 'approximate' as 'approximate' | 'from',
})
const saving = ref(false), fetching = ref(false), uploading = ref(false)
const sourceError = ref(''), sourceHint = ref(''), photoError = ref(''), photoUrlError = ref(''), saveError = ref('')
const sourceFeedback = ref<HTMLElement>(), photoFeedback = ref<HTMLElement>(), photoUrlFeedback = ref<HTMLElement>(), saveFeedback = ref<HTMLElement>()
const fileInput = ref<HTMLInputElement>()
const currencyTouched = ref(false)
const photoUrl = ref('')
const iconImageId = ref(props.item?.image_is_icon ? props.item.image_id : null)
watch(() => form.item_type, type => {
  if (type !== 'certificate' && form.image_id && form.image_id === iconImageId.value) {
    form.image_id = null
    iconImageId.value = null
  }
})
let lastAutoUrl = ''
let pendingSharedUrl = ''
let sharedDetails: SharedDetails | null = null

watch(() => [form.url, form.item_type], (_, __, onCleanup) => {
  if (form.item_type !== 'certificate' || !form.url.trim()) return
  const timer = setTimeout(() => autofillLink(), 700)
  onCleanup(() => clearTimeout(timer))
}, { immediate: true })

async function revealFeedback(target: typeof sourceFeedback) {
  await nextTick()
  if (target === sourceFeedback) {
    // Keep the title, source URL and its feedback together, not just the message.
    target.value?.closest('dialog')?.scrollTo({ top: 0, behavior: 'instant' })
    return
  }
  target.value?.scrollIntoView?.({ block: 'nearest', behavior: 'instant' })
}

function pasteLink(event: ClipboardEvent) {
  sharedDetails = extractSharedDetails(event.clipboardData?.getData('text/plain') || '')
  if (!sharedDetails) return // Keep ordinary paste and native URL validation for unsupported text.
  const { url } = sharedDetails
  event.preventDefault()
  form.url = url
  pendingSharedUrl = url
  autofillLink(true)
}

function autofillLink(fromShare = false) {
  const url = form.url.trim()
  if (!url || url === lastAutoUrl || fetching.value || uploading.value || saving.value) return
  try {
    const parsed = new URL(url)
    if (!['https:', 'http:'].includes(parsed.protocol)) return
    const social = /(^|\.)(instagram\.com|pinterest\.[a-z.]+|pin\.it|t\.me|telegram\.me)$/.test(parsed.hostname)
    if (!fromShare && form.item_type !== 'certificate' && !social) return
    lastAutoUrl = url
    pendingSharedUrl = ''
    void metadata()
  } catch { /* Validation stays with the input; never fetch an incomplete URL. */ }
}

async function upload(event: Event) {
  if (uploading.value || fetching.value || saving.value) return
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  photoError.value = ''; photoUrlError.value = ''
  if (file.size > 5242880) {
    photoError.value = 'Фото должно быть не больше 5 МБ'
    void revealFeedback(photoFeedback)
    return
  }
  uploading.value = true
  try {
    const data = new FormData(); data.append('file', file)
    form.image_id = (await api<{ id: string }>('/media', { method: 'POST', body: data })).id
  } catch (e) { photoError.value = (e as Error).message; void revealFeedback(photoFeedback) }
  finally { uploading.value = false; if (fileInput.value) fileInput.value.value = '' }
}

async function uploadFromUrl() {
  if (uploading.value || fetching.value || saving.value || !photoUrl.value.trim()) return
  uploading.value = true; photoError.value = ''; photoUrlError.value = ''
  try {
    const result = await send<{ id: string }>('/media/from-url', { url: photoUrl.value.trim() })
    form.image_id = result.id
    photoUrl.value = ''
  } catch (e) {
    photoUrlError.value = (e as Error).message
    void revealFeedback(photoUrlFeedback)
  }
  finally { uploading.value = false }
}

async function metadata() {
  if (fetching.value || uploading.value || saving.value) return
  fetching.value = true; sourceError.value = ''; sourceHint.value = ''
  const snapshot = { ...form }
  const shared = sharedDetails?.url === snapshot.url ? sharedDetails : null
  function applyDraft(draft: Partial<Metadata>, fromShare = false) {
    for (const key of ['title', 'price', 'image_id'] as const) {
      if (key === 'price' && (snapshot.item_type === 'certificate' || form.item_type === 'certificate')) continue
      if (!snapshot[key] && !form[key] && draft[key] != null) {
        if (key === 'image_id') {
          if (draft.image_is_icon && form.item_type !== 'certificate') continue
          form.image_id = draft.image_id || null
          iconImageId.value = draft.image_is_icon ? form.image_id : null
        }
        else if (key === 'price') {
          if (form.currency === snapshot.currency && (!currencyTouched.value || form.currency === draft.currency)) {
            form.price = String(draft.price); if (draft.currency) form.currency = draft.currency
            if (fromShare && shared?.price_mode && form.price_mode === snapshot.price_mode) form.price_mode = shared.price_mode
          }
        }
        else form[key] = String(draft[key])
      }
    }
  }
  try {
    const draft = await send<Metadata>('/metadata', { url: form.url, ...(form.item_type === 'certificate' ? { prefer_logo: true } : {}) })
    if (form.url !== snapshot.url) {
      sourceHint.value = 'Ссылка изменилась. Нажмите автозаполнение для новой ссылки.'
      return
    }
    // Personal descriptions are user-authored, never imported from the store.
    // Fill only fields empty at request start AND still unchanged at response time.
    applyDraft(draft)
    if (shared) applyDraft(shared, true)
    // Do not announce where an imported photo came from or how it was selected.
    sourceHint.value = draft.warning && !form.image_id
      ? 'Не все данные удалось заполнить. Недостающее можно добавить вручную.' : ''
    if (sourceHint.value) void revealFeedback(sourceFeedback)
  } catch (e) {
    if (form.url === snapshot.url) {
      if (shared) applyDraft(shared, true)
      sourceError.value = `${(e as Error).message}. Сохранить запись можно и без автозаполнения.`
      void revealFeedback(sourceFeedback)
    }
  }
  finally {
    fetching.value = false
    if (pendingSharedUrl && pendingSharedUrl === form.url && form.url !== snapshot.url) autofillLink(true)
    else if (form.item_type === 'certificate' && form.url !== snapshot.url) autofillLink()
  }
}

async function save() {
  if (saving.value || uploading.value || fetching.value) return
  saving.value = true; saveError.value = ''
  try {
    // Hide certificate pricing without discarding amounts already stored on older records.
    const price = form.item_type === 'certificate'
      ? (props.item?.item_type === 'certificate' ? props.item.price : null) : form.price || null
    const currency = price != null
      ? (form.item_type === 'certificate' ? props.item?.currency : form.currency) : null
    const payload: ItemInput = { item_type: form.item_type, title: form.title || null, description: form.description || null,
      url: form.url || null, image_id: form.image_id, price, currency: currency || null,
      price_mode: form.price_mode }
    if (props.item) await send(`/items/${props.item.id}`, payload, 'PUT')
    else await send('/items', { ...payload, recipient_id: props.recipientId, list_type: props.listType } satisfies ItemCreate)
    emit('saved')
  } catch (e) { saveError.value = (e as Error).message; void revealFeedback(saveFeedback) }
  finally { saving.value = false }
}
</script>

<template>
  <Modal :title="item ? 'Редактировать желание' : form.item_type === 'certificate' ? 'Магазин для сертификата' : listType === 'surprise' ? 'Маленький сюрприз' : 'Новое желание'" @close="!saving && emit('close')">
    <form class="item-form" @submit.prevent="save">
      <p class="form-intro">{{ listType === 'surprise' ? 'Маленькая подсказка для друзей. Получатель её не увидит.' : 'Сохраните то, что хочется. Остальное можно добавить потом.' }}</p>
      <div class="type-switch"><button type="button" :class="{ selected: form.item_type === 'idea' }" :aria-pressed="form.item_type === 'idea'" @click="form.item_type = 'idea'"><Lightbulb :size="18" /><span>Идея<small>Пожелание</small></span></button><button type="button" :class="{ selected: form.item_type === 'gift' }" :aria-pressed="form.item_type === 'gift'" @click="form.item_type = 'gift'"><Gift :size="18" /><span>Подарок<small>Вещь или пост</small></span></button><button type="button" :class="{ selected: form.item_type === 'certificate' }" :aria-pressed="form.item_type === 'certificate'" @click="form.item_type = 'certificate'; autofillLink()"><Store :size="18" /><span>Сертификат<small>Любимый магазин</small></span></button></div>
      <section class="form-section identity-section" aria-label="Карточка желания">
        <label>Название <span>{{ form.item_type === 'idea' ? '*' : 'необязательно' }}</span><input v-model="form.title" placeholder="Например, что-нибудь для рисования" :required="form.item_type === 'idea'" maxlength="200" /></label>
      </section>
      <section class="form-section source-section" :class="{ 'has-error': sourceError }" aria-label="Ссылка и автозаполнение">
        <label>{{ form.item_type === 'certificate' ? 'Ссылка на магазин' : 'Ссылка' }} <span>{{ form.item_type !== 'idea' ? '*' : 'необязательно' }}</span><div class="input-with-icon"><Link :size="17" /><input v-model="form.url" type="url" placeholder="https://магазин.ru/тот-самый-подарок" :required="form.item_type !== 'idea'" maxlength="2048" aria-describedby="source-link-hint" :aria-invalid="!!sourceError" :disabled="uploading || saving" @paste="pasteLink" @blur="autofillLink()" /></div></label>
        <p id="source-link-hint" ref="sourceFeedback" class="description-hint source-link-hint" :class="{ 'field-error': sourceError }" :role="sourceError ? 'alert' : sourceHint ? 'status' : undefined">{{ sourceError || sourceHint || (form.item_type === 'certificate' ? 'Ссылка на сайт магазина.' : 'Вставьте из «Поделиться», можно вместе с текстом.') }}</p>
        <button v-if="form.url" type="button" class="metadata-button" :disabled="fetching || uploading || saving" @click="metadata"><LoaderCircle v-if="fetching" :size="15" class="spin" /><Sparkles v-else :size="15" />{{ fetching ? 'Ищем подробности…' : form.item_type === 'certificate' ? 'Обновить название и фото' : 'Подтянуть название, цену и фото' }}</button>
      </section>
      <section class="photo-section" aria-label="Фотография">
        <div class="upload-area" :class="{ 'has-photo': form.image_id }"><WishImage v-if="form.image_id" :src="imageUrl(form.image_id)" :is-icon="form.image_id === iconImageId" alt="Фотография подарка" /><button type="button" class="upload-button" :disabled="uploading || fetching || saving" @click="fileInput?.click()"><LoaderCircle v-if="uploading" :size="22" class="spin" /><ImagePlus v-else-if="!form.image_id" :size="22" /><span>{{ uploading ? 'Загружаем…' : form.image_id ? 'Заменить фото' : form.item_type === 'certificate' ? 'Добавить фото магазина' : 'Добавить фото' }}<small ref="photoFeedback" :class="{ 'field-error': photoError }" :role="photoError ? 'alert' : undefined">{{ photoError || (form.image_id ? 'Выбрать другой файл · до 5 МБ' : 'Необязательно · до 5 МБ') }}</small></span></button><button v-if="form.image_id" type="button" class="icon-button remove-image" :disabled="uploading || fetching || saving" aria-label="Убрать фото" @click="form.image_id = null"><X :size="16" /></button><input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="upload" /></div>
        <details class="photo-url-details"><summary>Или загрузить фото по прямой ссылке</summary><div class="photo-url-area">
          <label for="photo-url">Или загрузите фото по ссылке</label>
          <div class="photo-url-row"><input id="photo-url" v-model="photoUrl" type="text" inputmode="url" maxlength="2048" placeholder="https://сайт.ru/photo.jpg" aria-describedby="photo-url-hint" :aria-invalid="!!photoUrlError" :disabled="uploading || saving" @keydown.enter.prevent="uploadFromUrl" /><button type="button" class="button secondary" :disabled="!photoUrl.trim() || uploading || fetching || saving" @click="uploadFromUrl"><LoaderCircle v-if="uploading" :size="16" class="spin" /><Link v-else :size="16" />Загрузить фото</button></div>
          <p id="photo-url-hint" ref="photoUrlFeedback" class="description-hint" :class="{ 'field-error': photoUrlError }" :role="photoUrlError ? 'alert' : undefined">{{ photoUrlError || 'JPEG, PNG или WebP · до 5 МБ' }}</p>
        </div></details>
      </section>
      <section class="form-section details-section" aria-label="Дополнительные сведения">
      <div class="personal-description">
        <label>Заметка <span>необязательно</span><textarea v-model="form.description" rows="2" maxlength="5000" aria-describedby="personal-description-hint" :placeholder="listType === 'surprise' ? 'Почему это точно в его или её вкусе?' : 'Что друзьям стоит о вас знать?'" /></label>
        <p id="personal-description-hint" class="description-hint">Только ваши слова — по ссылке не заполняется.</p>
      </div>
      <div v-if="form.item_type !== 'certificate'" class="price-field">
        <label for="item-price">Цена <span>необязательно</span></label>
        <div class="price-input-row">
          <button type="button" class="price-from" :aria-pressed="form.price_mode === 'from'" aria-label="Цена от указанной суммы" @click="form.price_mode = form.price_mode === 'from' ? 'approximate' : 'from'">От</button>
          <input id="item-price" :value="form.price" @input="form.price = ($event.target as HTMLInputElement).value" type="number" min="0" max="999999999999.99" step="0.01" placeholder="Сумма" />
          <select v-model="form.currency" aria-label="Валюта" @change="currencyTouched = true"><option>RUB</option><option>USD</option><option>EUR</option><option>GEL</option><option>KZT</option><option>BYN</option></select>
        </div>
      </div>
      </section>
      <div ref="saveFeedback" class="form-feedback"><p v-if="saveError" class="inline-error" role="alert">{{ saveError }}</p></div>
      <div class="form-actions"><button type="button" class="button secondary" :disabled="saving" @click="emit('close')">Отмена</button><button class="button primary" :disabled="saving || uploading || fetching"><LoaderCircle v-if="saving" :size="17" class="spin" />{{ saving ? 'Сохраняем…' : item ? 'Сохранить изменения' : form.item_type === 'certificate' ? 'Добавить магазин' : 'Добавить желание' }}</button></div>
    </form>
  </Modal>
</template>

<style scoped src="../styles/scoped/item-form.css"></style>
