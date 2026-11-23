<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue';
import { Gift, ImagePlus, Lightbulb, Link, LoaderCircle, Sparkles, X } from 'lucide-vue-next';
import Modal from './Modal.vue';
import {
  api,
  imageUrl,
  send,
  type Item,
  type ItemCreate,
  type ItemInput,
  type Metadata,
} from '../shared/api';
import { extractSharedDetails, type SharedDetails } from '../shared/sharedLink';
import WishImage from './WishImage.vue';
import { certificateStore, certificateStores } from '../shared/certificateStores';
import { itemTitle } from '../shared/api';

const props = defineProps<{
  item?: Item;
  recipientId: string;
  listType: 'wishlist' | 'surprise';
  initialType?: ItemInput['item_type'];
}>();
const emit = defineEmits<{ close: []; saved: [] }>();
const form = reactive({
  item_type: props.item?.item_type || props.initialType || ('idea' as ItemInput['item_type']),
  title: props.item?.title || '',
  description: props.item?.description || '',
  url: props.item?.url || '',
  price: props.item?.price?.toString() || '',
  currency: props.item?.currency || 'RUB',
  image_id: props.item?.image_id || (null as string | null),
  price_mode: props.item?.price_mode || ('approximate' as 'approximate' | 'from'),
  surprise_visibility: props.item?.surprise_visibility || ('friends' as 'friends' | 'private'),
});
const saving = ref(false),
  fetching = ref(false),
  uploading = ref(false);
const sourceError = ref(''),
  sourceHint = ref(''),
  photoError = ref(''),
  photoUrlError = ref(''),
  saveError = ref('');
const sourceFeedback = ref<HTMLElement>(),
  photoFeedback = ref<HTMLElement>(),
  photoUrlFeedback = ref<HTMLElement>(),
  saveFeedback = ref<HTMLElement>();
const fileInput = ref<HTMLInputElement>();
const photoUrl = ref('');
const iconImageId = ref(props.item?.image_is_icon ? props.item.image_id : null);
watch(
  () => form.item_type,
  (type) => {
    if (type !== 'certificate' && form.image_id && form.image_id === iconImageId.value) {
      form.image_id = null;
      iconImageId.value = null;
    }
  },
);
let lastAutoUrl = '';
let pendingSharedUrl = '';
let sharedDetails: SharedDetails | null = null;

// Mobile keyboards and webviews may insert shared text through input, not paste.
watch(
  () => form.url,
  (value) => {
    if (form.item_type === 'certificate') {
      form.title = certificateStore(value)?.name || '';
      form.image_id = null;
      iconImageId.value = null;
      lastAutoUrl = '';
    }
    const details = extractSharedDetails(value);
    if (!details || details.url === value.trim()) return;
    sharedDetails = details;
    form.url = details.url;
    pendingSharedUrl = details.url;
    autofillLink(true);
  },
  { flush: 'sync' },
);

watch(
  () => [form.url, form.item_type],
  (_, __, onCleanup) => {
    if (form.item_type !== 'certificate' || !form.url.trim()) return;
    const timer = setTimeout(() => autofillLink(), 700);
    onCleanup(() => clearTimeout(timer));
  },
  { immediate: true },
);

async function revealFeedback(target: typeof sourceFeedback) {
  await nextTick();
  if (target === sourceFeedback) {
    // Keep the title, source URL and its feedback together, not just the message.
    target.value?.closest('dialog')?.scrollTo({ top: 0, behavior: 'instant' });
    return;
  }
  target.value?.scrollIntoView?.({ block: 'nearest', behavior: 'instant' });
}

function scrollFocusedField(event: FocusEvent) {
  const target = event.target as HTMLElement | null;
  if (!target || !(target instanceof Element) || !target.matches('input, textarea, select')) return;
  window.setTimeout(() => {
    target.scrollIntoView?.({ block: 'center', behavior: 'smooth' });
  }, 300);
}

function pasteLink(event: ClipboardEvent) {
  sharedDetails = extractSharedDetails(event.clipboardData?.getData('text/plain') || '');
  if (!sharedDetails) return; // Keep ordinary paste and native URL validation for unsupported text.
  const { url } = sharedDetails;
  event.preventDefault();
  form.url = url;
  pendingSharedUrl = url;
  autofillLink(true);
}

function autofillLink(fromShare = false) {
  const url = form.url.trim();
  if (!url || url === lastAutoUrl || fetching.value || uploading.value || saving.value) return;
  try {
    const parsed = new URL(url);
    if (!['https:', 'http:'].includes(parsed.protocol)) return;
    const social = /(^|\.)(instagram\.com|pinterest\.[a-z.]+|pin\.it|t\.me|telegram\.me)$/.test(
      parsed.hostname,
    );
    const avito =
      ['avito.ru', 'www.avito.ru', 'm.avito.ru'].includes(parsed.hostname) &&
      !parsed.username &&
      !parsed.password;
    if (!fromShare && form.item_type !== 'certificate' && !social && !avito) return;
    lastAutoUrl = url;
    pendingSharedUrl = '';
    void metadata();
  } catch {
    /* Validation stays with the input; never fetch an incomplete URL. */
  }
}

async function upload(event: Event) {
  if (uploading.value || fetching.value || saving.value) return;
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  photoError.value = '';
  photoUrlError.value = '';
  if (file.size > 5242880) {
    photoError.value = 'Фото должно быть не больше 5 МБ';
    void revealFeedback(photoFeedback);
    return;
  }
  uploading.value = true;
  try {
    const data = new FormData();
    data.append('file', file);
    form.image_id = (await api<{ id: string }>('/media', { method: 'POST', body: data })).id;
  } catch (e) {
    photoError.value = (e as Error).message;
    void revealFeedback(photoFeedback);
  } finally {
    uploading.value = false;
    if (fileInput.value) fileInput.value.value = '';
  }
}

async function uploadFromUrl() {
  if (uploading.value || fetching.value || saving.value || !photoUrl.value.trim()) return;
  uploading.value = true;
  photoError.value = '';
  photoUrlError.value = '';
  try {
    const result = await send<{ id: string }>('/media/from-url', { url: photoUrl.value.trim() });
    form.image_id = result.id;
    photoUrl.value = '';
  } catch (e) {
    photoUrlError.value = (e as Error).message;
    void revealFeedback(photoUrlFeedback);
  } finally {
    uploading.value = false;
  }
}

async function metadata() {
  if (fetching.value || uploading.value || saving.value) return;
  fetching.value = true;
  sourceError.value = '';
  sourceHint.value = '';
  const details = extractSharedDetails(form.url);
  if (details && details.url !== form.url.trim()) {
    sharedDetails = details;
    form.url = details.url;
  }
  const snapshot = { ...form };
  const shared = sharedDetails?.url === snapshot.url ? sharedDetails : null;
  function applyDraft(draft: Partial<Metadata>, fromShare = false) {
    for (const key of ['title', 'price', 'image_id'] as const) {
      if (
        key === 'price' &&
        (snapshot.item_type === 'certificate' || form.item_type === 'certificate')
      )
        continue;
      if (
        ((!snapshot[key] && !form[key]) ||
          (snapshot.item_type === 'certificate' &&
            form.item_type === 'certificate' &&
            form[key] === snapshot[key])) &&
        draft[key] != null
      ) {
        if (key === 'image_id') {
          if (draft.image_is_icon && form.item_type !== 'certificate') continue;
          form.image_id = draft.image_id || null;
          iconImageId.value = draft.image_is_icon ? form.image_id : null;
        } else if (key === 'price') {
          if (form.currency === snapshot.currency) {
            form.price = String(draft.price);
            if (draft.currency) form.currency = draft.currency;
            if (fromShare && shared?.price_mode && form.price_mode === snapshot.price_mode)
              form.price_mode = shared.price_mode;
          }
        } else
          form[key] =
            (form.item_type === 'certificate' ? certificateStore(form.url)?.name : '') ||
            String(draft[key]);
      }
    }
  }
  try {
    const draft = await send<Metadata>('/metadata', {
      url: form.url,
      ...(form.item_type === 'certificate' ? { prefer_logo: true } : {}),
    });
    if (form.url !== snapshot.url) {
      sourceHint.value = 'Ссылка изменилась. Нажмите автозаполнение для новой ссылки.';
      return;
    }
    // Personal descriptions are user-authored, never imported from the store.
    // Fill only fields empty at request start AND still unchanged at response time.
    applyDraft(draft);
    if (shared) applyDraft(shared, true);
    // Do not announce where an imported photo came from or how it was selected.
    sourceHint.value =
      draft.warning && !form.image_id
        ? 'Не все данные удалось заполнить. Недостающее можно добавить вручную.'
        : '';
    if (sourceHint.value) void revealFeedback(sourceFeedback);
  } catch (e) {
    if (form.url === snapshot.url) {
      if (shared) applyDraft(shared, true);
      sourceError.value = `${(e as Error).message}. Сохранить запись можно и без автозаполнения.`;
      void revealFeedback(sourceFeedback);
    }
  } finally {
    fetching.value = false;
    if (pendingSharedUrl && pendingSharedUrl === form.url && form.url !== snapshot.url)
      autofillLink(true);
    else if (form.item_type === 'certificate' && form.url !== snapshot.url) autofillLink();
  }
}

async function save() {
  if (saving.value || uploading.value || fetching.value) return;
  saving.value = true;
  saveError.value = '';
  try {
    // Hide certificate pricing without discarding amounts already stored on older records.
    const price =
      form.item_type === 'certificate'
        ? props.item?.item_type === 'certificate'
          ? props.item.price
          : null
        : form.price || null;
    const currency =
      price != null
        ? form.item_type === 'certificate'
          ? props.item?.currency
          : form.currency
        : null;
    if (form.item_type === 'certificate' && [...form.description].length > 100) {
      throw new Error('Заметка к сертификату — не больше 100 символов');
    }
    if (form.item_type !== 'certificate' && [...form.description.trim()].length > 500) {
      throw new Error('Заметка к желанию — не больше 500 символов');
    }
    const payload: ItemInput = {
      item_type: form.item_type,
      title: form.title || null,
      description: form.description || null,
      url: form.url || null,
      image_id: form.image_id,
      price,
      currency: currency || null,
      price_mode: form.price_mode,
      surprise_visibility: props.listType === 'surprise' ? form.surprise_visibility : 'friends',
    };
    if (props.item) await send(`/items/${props.item.id}`, payload, 'PUT');
    else
      await send('/items', {
        ...payload,
        recipient_id: props.recipientId,
        list_type: props.listType,
      } satisfies ItemCreate);
    emit('saved');
  } catch (e) {
    saveError.value = (e as Error).message;
    void revealFeedback(saveFeedback);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Modal
    :title="
      item
        ? 'Редактировать желание'
        : form.item_type === 'certificate'
          ? 'Магазин для сертификата'
          : listType === 'surprise'
            ? 'Маленький сюрприз'
            : 'Новое желание'
    "
    @close="!saving && emit('close')"
  >
    <form class="item-form" @submit.prevent="save" @focusin="scrollFocusedField">
      <div v-if="form.item_type !== 'certificate'" class="type-switch">
        <button
          type="button"
          :class="{ selected: form.item_type === 'idea' }"
          :aria-pressed="form.item_type === 'idea'"
          @click="form.item_type = 'idea'"
        >
          <Lightbulb :size="18" /><span>Идея<small>Мысль или впечатление</small></span></button
        ><button
          type="button"
          :class="{ selected: form.item_type === 'gift' }"
          :aria-pressed="form.item_type === 'gift'"
          @click="form.item_type = 'gift'"
        >
          <Gift :size="18" /><span>По ссылке<small>Вещь или находка</small></span>
        </button>
      </div>
      <p class="form-intro">
        {{
          form.item_type === 'idea'
            ? 'Запишите пожелание или подсказку — конкретную вещь выбирать не обязательно.'
            : form.item_type === 'certificate'
              ? 'Добавьте любимый магазин — друзья смогут выбрать сертификат сами.'
              : 'Сохраните конкретную вещь или пост. По ссылке попробуем найти название и фото.'
        }}
        <span v-if="listType === 'surprise'"> Получатель сюрприз не увидит.</span>
      </p>
      <label v-if="listType === 'surprise'" class="mb-5 block">
        Кто видит сюрприз
        <select v-model="form.surprise_visibility" class="mt-2 w-full">
          <option value="friends">Всем друзьям</option>
          <option value="private">Только мне</option>
        </select>
        <small class="description-hint">Получатель не увидит сюрприз при любом выборе.</small>
      </label>
      <div
        class="wish-editor-layout"
        :class="{ 'certificate-editor': form.item_type === 'certificate' }"
      >
        <div class="wish-editor-fields">
          <section
            v-if="form.item_type !== 'certificate'"
            class="form-section identity-section"
            aria-label="Карточка желания"
          >
            <label
              >Название <span>{{ form.item_type === 'idea' ? '*' : 'необязательно' }}</span><input
                v-model="form.title"
                placeholder="Например, что-нибудь для рисования"
                :required="form.item_type === 'idea'"
                maxlength="200"
            /></label>
          </section>
          <section
            class="form-section source-section"
            :class="{ 'has-error': sourceError }"
            aria-label="Ссылка и автозаполнение"
          >
            <label v-if="form.item_type === 'certificate'" class="mb-4">
              Популярные магазины
              <select
                class="mt-2 w-full"
                aria-label="Выбрать популярный магазин"
                :value="certificateStore(form.url)?.host || ''"
                :disabled="uploading || saving"
                @change="
                  form.url = ($event.target as HTMLSelectElement).value
                    ? `https://${($event.target as HTMLSelectElement).value}/`
                    : ''
                "
              >
                <option value="">Свой магазин — вставьте ссылку ниже</option>
                <option v-for="store in certificateStores" :key="store.host" :value="store.host">
                  {{ store.name }} — {{ store.note }}
                </option>
              </select>
            </label>
            <label
              >{{ form.item_type === 'certificate' ? 'Ссылка на магазин' : 'Ссылка' }}
              <span>{{ form.item_type !== 'idea' ? '*' : 'необязательно' }}</span>
              <div class="input-with-icon">
                <Link :size="17" /><input
                  v-model="form.url"
                  type="url"
                  placeholder="https://магазин.ru/тот-самый-подарок"
                  :required="form.item_type !== 'idea'"
                  maxlength="2048"
                  aria-describedby="source-link-hint"
                  :aria-invalid="!!sourceError"
                  :disabled="uploading || saving"
                  @paste="pasteLink"
                  @blur="autofillLink()"
                /></div
            ></label>
            <p
              id="source-link-hint"
              ref="sourceFeedback"
              class="description-hint source-link-hint"
              :class="{ 'field-error': sourceError }"
              :role="sourceError ? 'alert' : sourceHint ? 'status' : undefined"
            >
              {{
                sourceError ||
                sourceHint ||
                (form.item_type === 'certificate'
                  ? 'Ссылка на сайт магазина.'
                  : 'Вставьте из «Поделиться», можно вместе с текстом.')
              }}
            </p>
            <button
              v-if="form.url"
              type="button"
              class="metadata-button"
              :disabled="fetching || uploading || saving"
              @click="metadata"
            >
              <LoaderCircle v-if="fetching" :size="15" class="spin" /><Sparkles
                v-else
                :size="15"
              />{{
                fetching
                  ? 'Ищем подробности…'
                  : form.item_type === 'certificate'
                    ? 'Обновить иконку и название'
                    : 'Подтянуть название, цену и фото'
              }}
            </button>
          </section>
        </div>
        <div
          v-if="form.item_type === 'certificate' && form.url"
          class="flex items-center gap-3 rounded border border-line p-3"
        >
          <WishImage
            v-if="form.image_id"
            :src="imageUrl(form.image_id)"
            :is-icon="true"
            alt=""
            class="size-10 object-contain"
          />
          <Gift v-else :size="24" aria-hidden="true" />
          <span class="text-sm">{{ form.title || itemTitle({ title: null, url: form.url }) }}</span>
        </div>
        <section
          v-else-if="form.item_type !== 'certificate'"
          class="photo-section"
          aria-label="Фотография"
        >
          <span class="editor-section-label">ОБЛОЖКА ЖЕЛАНИЯ</span>
          <div class="upload-area" :class="{ 'has-photo': form.image_id }">
            <WishImage
              v-if="form.image_id"
              :src="imageUrl(form.image_id)"
              :is-icon="form.image_id === iconImageId"
              alt="Фотография подарка"
            /><button
              type="button"
              class="upload-button"
              :disabled="uploading || fetching || saving"
              @click="fileInput?.click()"
            >
              <LoaderCircle v-if="uploading" :size="22" class="spin" /><ImagePlus
                v-else-if="!form.image_id"
                :size="22"
              /><span
                >{{ uploading ? 'Загружаем…' : form.image_id ? 'Заменить фото' : 'Добавить фото'
                }}<small
                  ref="photoFeedback"
                  :class="{ 'field-error': photoError }"
                  :role="photoError ? 'alert' : undefined"
                  >{{
                    photoError ||
                    (form.image_id ? 'Выбрать другой файл · до 5 МБ' : 'Необязательно · до 5 МБ')
                  }}</small
                ></span
              ></button
            ><button
              v-if="form.image_id"
              type="button"
              class="icon-button remove-image"
              :disabled="uploading || fetching || saving"
              aria-label="Убрать фото"
              @click="form.image_id = null"
            >
              <X :size="16" /></button
            ><input
              ref="fileInput"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              hidden
              @change="upload"
            />
          </div>
          <details class="photo-url-details">
            <summary>Или загрузить фото по прямой ссылке</summary>
            <div class="photo-url-area">
              <label for="photo-url">Или загрузите фото по ссылке</label>
              <div class="photo-url-row">
                <input
                  id="photo-url"
                  v-model="photoUrl"
                  type="text"
                  inputmode="url"
                  maxlength="2048"
                  placeholder="https://сайт.ru/photo.jpg"
                  aria-describedby="photo-url-hint"
                  :aria-invalid="!!photoUrlError"
                  :disabled="uploading || saving"
                  @keydown.enter.prevent="uploadFromUrl"
                /><button
                  type="button"
                  class="button secondary"
                  :disabled="!photoUrl.trim() || uploading || fetching || saving"
                  @click="uploadFromUrl"
                >
                  <LoaderCircle v-if="uploading" :size="16" class="spin" /><Link
                    v-else
                    :size="16"
                  />Загрузить фото
                </button>
              </div>
              <p
                id="photo-url-hint"
                ref="photoUrlFeedback"
                class="description-hint"
                :class="{ 'field-error': photoUrlError }"
                :role="photoUrlError ? 'alert' : undefined"
              >
                {{ photoUrlError || 'JPEG, PNG или WebP · до 5 МБ' }}
              </p>
            </div>
          </details>
        </section>
        <section class="form-section details-section" aria-label="Дополнительные сведения">
          <div class="personal-description">
            <label
              >Заметка <span>необязательно</span
              ><textarea
                v-model="form.description"
                rows="2"
                :maxlength="form.item_type === 'certificate' ? 100 : 500"
                aria-describedby="personal-description-hint"
                :placeholder="
                  listType === 'surprise'
                    ? 'Почему это точно в его или её вкусе?'
                    : 'Цвет, размер или почему вам этого хочется…'
                "
              />
            </label>
            <p id="personal-description-hint" class="description-hint">
              {{
                form.item_type === 'certificate'
                  ? `${[...form.description].length} / 100`
                  : `${[...form.description].length} / 500 · Только ваши слова`
              }}
            </p>
          </div>
          <div v-if="form.item_type !== 'certificate'" class="price-field">
            <label for="item-price">Цена <span>необязательно</span></label>
            <div class="price-input-row">
              <button
                type="button"
                class="price-from"
                :aria-pressed="form.price_mode === 'from'"
                aria-label="Цена от указанной суммы"
                @click="form.price_mode = form.price_mode === 'from' ? 'approximate' : 'from'"
              >
                {{ form.price_mode === 'from' ? '✓ Цена от' : 'Цена от' }}
              </button>
              <input
                id="item-price"
                :value="form.price"
                @input="form.price = ($event.target as HTMLInputElement).value"
                type="number"
                min="0"
                max="999999999999.99"
                step="0.01"
                placeholder="Сумма"
              />
            </div>
          </div>
        </section>
      </div>
      <div ref="saveFeedback" class="form-feedback">
        <p v-if="saveError" class="inline-error" role="alert">{{ saveError }}</p>
      </div>
      <div class="form-actions">
        <button type="button" class="button secondary" :disabled="saving" @click="emit('close')">
          Отмена</button
        ><button class="button primary" :disabled="saving || uploading || fetching">
          <LoaderCircle v-if="saving" :size="17" class="spin" />{{
            saving
              ? 'Сохраняем…'
              : item
                ? 'Сохранить изменения'
                : form.item_type === 'certificate'
                  ? 'Добавить магазин'
                  : 'Добавить желание'
          }}
        </button>
      </div>
    </form>
  </Modal>
</template>
