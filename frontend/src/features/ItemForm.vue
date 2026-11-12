<script setup lang="ts">
import { reactive, ref } from 'vue'
import { Gift, ImagePlus, Lightbulb, Link, LoaderCircle, Sparkles, Store, X } from 'lucide-vue-next'
import Modal from '../shared/Modal.vue'
import { api, imageUrl, send, type Item, type ItemCreate, type ItemInput, type Metadata } from '../shared/api'

const props = defineProps<{ item?: Item; recipientId: string; listType: 'wishlist' | 'surprise'; initialType?: ItemInput['item_type'] }>()
const emit = defineEmits<{ close: []; saved: [] }>()
const form = reactive({
  item_type: props.item?.item_type || props.initialType || 'idea' as ItemInput['item_type'],
  title: props.item?.title || '', description: props.item?.description || '', url: props.item?.url || '',
  price: props.item?.price?.toString() || '', currency: props.item?.currency || 'RUB', image_id: props.item?.image_id || null as string | null,
  price_mode: props.item?.price_mode || 'approximate' as 'approximate' | 'from',
})
const saving = ref(false), fetching = ref(false), uploading = ref(false), error = ref(''), hint = ref('')
const fileInput = ref<HTMLInputElement>()
const currencyTouched = ref(false)
const photoUrl = ref('')
let lastAutoUrl = ''

function autofillLink() {
  const url = form.url.trim()
  if (!url || url === lastAutoUrl || fetching.value || uploading.value || saving.value) return
  try {
    const parsed = new URL(url)
    if (!['https:', 'http:'].includes(parsed.protocol)) return
    const social = /(^|\.)(instagram\.com|pinterest\.[a-z.]+|pin\.it|t\.me|telegram\.me)$/.test(parsed.hostname)
    if (form.item_type !== 'certificate' && !social) return
    lastAutoUrl = url
    void metadata()
  } catch { /* Validation stays with the input; never fetch an incomplete URL. */ }
}

async function upload(event: Event) {
  if (uploading.value || fetching.value || saving.value) return
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (file.size > 5242880) { error.value = 'Фото должно быть не больше 5 МБ'; return }
  uploading.value = true; error.value = ''
  try {
    const data = new FormData(); data.append('file', file)
    form.image_id = (await api<{ id: string }>('/media', { method: 'POST', body: data })).id
  } catch (e) { error.value = (e as Error).message }
  finally { uploading.value = false; if (fileInput.value) fileInput.value.value = '' }
}

async function uploadFromUrl() {
  if (uploading.value || fetching.value || saving.value || !photoUrl.value.trim()) return
  uploading.value = true; error.value = ''; hint.value = ''
  try {
    const result = await send<{ id: string }>('/media/from-url', { url: photoUrl.value.trim() })
    form.image_id = result.id
    photoUrl.value = ''
    hint.value = 'Фотография загружена по ссылке. Сохраните желание, чтобы применить изменения.'
  } catch (e) { error.value = `${(e as Error).message}. Нужна прямая ссылка на изображение JPEG, PNG или WebP.` }
  finally { uploading.value = false }
}

async function metadata() {
  if (fetching.value || uploading.value || saving.value) return
  fetching.value = true; error.value = ''; hint.value = ''
  const snapshot = { ...form }
  try {
    const draft = await send<Metadata>('/metadata', { url: form.url })
    if (form.url !== snapshot.url) {
      hint.value = 'Ссылка изменилась. Нажмите автозаполнение для новой ссылки.'
      return
    }
    // Personal descriptions are user-authored, never imported from the store.
    // Fill only fields empty at request start AND still unchanged at response time.
    for (const key of ['title', 'price', 'image_id'] as const) {
      if (key === 'price' && snapshot.item_type === 'certificate') continue
      if (!snapshot[key] && !form[key] && draft[key] != null) {
        if (key === 'image_id') form.image_id = draft.image_id || null
        else if (key === 'price') {
          if (form.currency === snapshot.currency && (!currencyTouched.value || form.currency === draft.currency)) {
            form.price = String(draft.price); if (draft.currency) form.currency = draft.currency
          }
        }
        else form[key] = String(draft[key])
      }
    }
    hint.value = draft.warning || 'Заполнены только пустые поля. Проверьте данные перед сохранением.'
  } catch (e) { error.value = `${(e as Error).message}. Сохранить запись можно и без автозаполнения.` }
  finally { fetching.value = false }
}

async function save() {
  if (saving.value || uploading.value || fetching.value) return
  saving.value = true; error.value = ''
  try {
    const payload: ItemInput = { item_type: form.item_type, title: form.title || null, description: form.description || null,
      url: form.url || null, image_id: form.image_id, price: form.price || null, currency: form.price ? form.currency : null,
      price_mode: form.price_mode }
    if (props.item) await send(`/items/${props.item.id}`, payload, 'PUT')
    else await send('/items', { ...payload, recipient_id: props.recipientId, list_type: props.listType } satisfies ItemCreate)
    emit('saved')
  } catch (e) { error.value = (e as Error).message }
  finally { saving.value = false }
}
</script>

<template>
  <Modal :title="item ? 'Редактировать желание' : form.item_type === 'certificate' ? 'Магазин для сертификата' : listType === 'surprise' ? 'Маленький сюрприз' : 'Новое желание'" @close="!saving && emit('close')">
    <form class="item-form" @submit.prevent="save">
      <p class="form-intro">{{ listType === 'surprise' ? 'Этот подарок увидят друзья, но не получатель. Секрет останется секретом.' : 'Сохраните то, что порадует вас. Друзьям будет проще выбрать подарок.' }}</p>
      <div class="type-switch"><button type="button" :class="{ selected: form.item_type === 'idea' }" :aria-pressed="form.item_type === 'idea'" @click="form.item_type = 'idea'"><Lightbulb :size="18" /><span>Идея<small>Пожелание</small></span></button><button type="button" :class="{ selected: form.item_type === 'gift' }" :aria-pressed="form.item_type === 'gift'" @click="form.item_type = 'gift'"><Gift :size="18" /><span>Подарок<small>Вещь или пост</small></span></button><button type="button" :class="{ selected: form.item_type === 'certificate' }" :aria-pressed="form.item_type === 'certificate'" @click="form.item_type = 'certificate'; autofillLink()"><Store :size="18" /><span>Сертификат<small>Любимый магазин</small></span></button></div>
      <section class="photo-section" aria-labelledby="photo-section-title">
        <div class="photo-section-heading"><h3 id="photo-section-title">{{ form.item_type === 'certificate' ? 'Фото магазина' : 'Фотография' }}</h3><span>необязательно</span></div>
        <div class="upload-area" :class="{ 'has-photo': form.image_id }"><img v-if="form.image_id" :src="imageUrl(form.image_id)" alt="Фотография подарка" /><button v-if="form.image_id" type="button" class="icon-button remove-image" :disabled="uploading || fetching || saving" aria-label="Убрать фото" @click="form.image_id = null"><X :size="16" /></button><button type="button" class="upload-button" :disabled="uploading || fetching || saving" @click="fileInput?.click()"><LoaderCircle v-if="uploading" :size="30" class="spin" /><ImagePlus v-else :size="30" /><span>{{ uploading ? 'Загружаем…' : form.image_id ? 'Заменить фотографию' : 'Добавить фотографию' }}<small>Выбрать файл · JPEG, PNG, WebP · до 5 МБ</small></span></button><input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="upload" /></div>
        <details class="photo-url-details"><summary>Или загрузить фото по прямой ссылке</summary><div class="photo-url-area">
          <label for="photo-url">Или загрузите фото по ссылке</label>
          <div class="photo-url-row"><input id="photo-url" v-model="photoUrl" type="text" inputmode="url" maxlength="2048" placeholder="https://сайт.ru/photo.jpg" aria-describedby="photo-url-hint" :disabled="uploading || saving" @keydown.enter.prevent="uploadFromUrl" /><button type="button" class="button secondary" :disabled="!photoUrl.trim() || uploading || fetching || saving" @click="uploadFromUrl"><LoaderCircle v-if="uploading" :size="16" class="spin" /><Link v-else :size="16" />Загрузить фото</button></div>
          <p id="photo-url-hint" class="description-hint">Прямая ссылка на JPEG, PNG или WebP, не на страницу товара. До 5 МБ и 16 Мп. Новое фото заменит текущее только после успешной загрузки.</p>
        </div></details>
      </section>
      <label>{{ form.item_type === 'certificate' ? 'Ссылка на магазин' : 'Ссылка' }} <span>{{ form.item_type !== 'idea' ? '*' : 'необязательно' }}</span><div class="input-with-icon"><Link :size="17" /><input v-model="form.url" type="url" placeholder="https://магазин.ru/тот-самый-подарок" :required="form.item_type !== 'idea'" maxlength="2048" aria-describedby="source-link-hint" @blur="autofillLink" /></div></label>
      <p id="source-link-hint" class="description-hint source-link-hint">{{ form.item_type === 'certificate' ? 'Вставьте ссылку и перейдите к следующему полю — попробуем загрузить название и фото. Номинал сертификата укажите сами.' : 'Подойдёт магазин, пост Instagram, пин Pinterest (включая pin.it) или публичное сообщение Telegram. Для соцсетей попробуем подгрузить фото автоматически; закрытые посты могут быть недоступны.' }}</p>
      <button v-if="form.url" type="button" class="metadata-button" :disabled="fetching || uploading || saving" @click="metadata"><LoaderCircle v-if="fetching" :size="15" class="spin" /><Sparkles v-else :size="15" />{{ fetching ? 'Ищем подробности…' : 'Подтянуть название, цену и фото' }}</button>
      <label>Название <span>{{ form.item_type === 'idea' ? '*' : 'необязательно' }}</span><input v-model="form.title" placeholder="Например, что-нибудь для рисования" :required="form.item_type === 'idea'" maxlength="200" /></label>
      <div class="personal-description">
        <label>Личное описание <span>необязательно</span><textarea v-model="form.description" rows="3" maxlength="5000" aria-describedby="personal-description-hint" placeholder="Напишите от себя: почему хочется этот подарок, какой цвет или размер выбрать…" /></label>
        <p id="personal-description-hint" class="description-hint">Ваши пожелания и подсказки для друзей, а не описание товара из магазина. По ссылке это поле не заполняется.</p>
      </div>
      <fieldset class="price-mode"><legend>{{ form.item_type === 'certificate' ? 'Номинал сертификата' : 'Цена' }}</legend><label><input v-model="form.price_mode" type="radio" value="approximate" name="price-mode" />Примерно</label><label><input v-model="form.price_mode" type="radio" value="from" name="price-mode" />От суммы</label></fieldset>
      <div class="form-row"><label>{{ form.price_mode === 'from' ? 'От суммы' : 'Примерная цена' }} <span>необязательно</span><input :value="form.price" @input="form.price = ($event.target as HTMLInputElement).value" type="number" min="0" max="999999999999.99" step="0.01" placeholder="Без ограничений" /></label><label class="currency-label">Валюта<select v-model="form.currency" @change="currencyTouched = true"><option>RUB</option><option>USD</option><option>EUR</option><option>GEL</option><option>KZT</option><option>BYN</option></select></label></div>
      <p v-if="hint" class="inline-hint" role="status">{{ hint }}</p><p v-if="error" class="inline-error" role="alert">{{ error }}</p>
      <div class="form-actions"><button type="button" class="button secondary" :disabled="saving" @click="emit('close')">Отмена</button><button class="button primary" :disabled="saving || uploading || fetching"><LoaderCircle v-if="saving" :size="17" class="spin" />{{ saving ? 'Сохраняем…' : item ? 'Сохранить изменения' : form.item_type === 'certificate' ? 'Добавить магазин' : 'Добавить желание' }}</button></div>
    </form>
  </Modal>
</template>

<style scoped>
.photo-url-area { margin-bottom: 17px; }
.photo-url-area label { margin-bottom: 7px; }
.photo-url-row { display: flex; gap: 8px; margin-bottom: 6px; }
.photo-url-row input { flex: 1; min-width: 0; }
.photo-url-row button { flex-shrink: 0; }
@media (max-width: 440px) { .photo-url-row { flex-direction: column; } }
.upload-area > img { object-fit: contain; object-position: center; flex-shrink: 0; }
.personal-description { margin-bottom: 17px; }
.personal-description label { margin-bottom: 6px; }
.description-hint { font-size: 12px; font-weight: 400; line-height: 1.7; color: var(--muted); }
</style>
