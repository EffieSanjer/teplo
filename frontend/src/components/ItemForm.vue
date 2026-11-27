<script setup lang="ts">
import {
  computed,
  nextTick,
  onMounted,
  reactive,
  ref,
  watch,
  type ComponentPublicInstance,
} from 'vue';
import {
  ArrowLeft,
  Gift,
  Heart,
  ImagePlus,
  Lightbulb,
  Link,
  Pencil,
  Sparkles,
  Ticket,
  Trash2,
  X,
} from 'lucide-vue-next';
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
import { AppButton, FieldMessage, FormActions, FormField, PriceField } from './ui';

const props = defineProps<{
  item?: Item;
  recipientId: string;
  listType: 'wishlist' | 'surprise';
  initialType?: ItemInput['item_type'];
  seed?: SharedDetails;
}>();
const emit = defineEmits<{ close: []; saved: [] }>();
const fieldSections = computed(() =>
  form.item_type === 'gift' || form.item_type === 'ticket'
    ? ['source', 'identity']
    : ['identity', 'source'],
);
const form = reactive({
  item_type: props.item?.item_type || props.initialType || ('gift' as ItemInput['item_type']),
  title: props.item?.title || props.seed?.title || '',
  description: props.item?.description || '',
  url: props.item?.url || props.seed?.url || '',
  price: props.item?.price?.toString() || props.seed?.price || '',
  currency: props.item?.currency || props.seed?.currency || 'RUB',
  image_id: props.item?.image_id || props.seed?.image_id || (null as string | null),
  price_mode: props.item?.price_mode || ('exact' as 'exact' | 'approximate' | 'from'),
  surprise_visibility: props.item?.surprise_visibility || ('friends' as 'friends' | 'private'),
});
const draft = ref(form);
const saving = ref(false),
  fetching = ref(false),
  uploading = ref(false);
const mostWanted = ref(props.item?.most_wanted || false);
const sourcePlaceholder = computed(() =>
  form.item_type === 'ticket'
    ? 'https://афиша…/событие'
    : form.item_type === 'certificate'
      ? 'https://пример.ru/сертификат'
      : 'https://пример.ru/тот-самый-подарок',
);
const sourceError = ref(''),
  sourceHint = ref(''),
  photoError = ref(''),
  photoUrlError = ref(''),
  saveError = ref('');
const sourceFeedback = ref<ComponentPublicInstance>(),
  photoFeedback = ref<ComponentPublicInstance>(),
  saveFeedback = ref<ComponentPublicInstance>();
const fileInput = ref<HTMLInputElement>();
const photoUrl = ref('');
const photoUrlOpen = ref(false);
const photoUrlInput = ref<InstanceType<typeof FormField>>();
const photoUrlToggle = ref<InstanceType<typeof AppButton>>();
const focusedField = ref('');
const descriptionLength = computed(() => [...form.description].length);
const descriptionLimit = computed(() => (form.item_type === 'certificate' ? 100 : 500));
const descriptionOverLimit = computed(() => descriptionLength.value > descriptionLimit.value);
const customStoreTitle = computed(() =>
  form.item_type === 'certificate' && !certificateStore(form.url) && form.title.trim()
    ? form.title.split(/\s*(?:--|—|–|\|)\s*|\s+-\s+/)[0]?.trim() || form.title.trim()
    : '',
);
const noteInput = ref<InstanceType<typeof FormField>>();
const formTitle = computed(() =>
  props.item
    ? 'Редактировать желание'
    : form.item_type === 'certificate'
      ? 'Сертификат'
      : form.item_type === 'ticket'
        ? 'Билет на событие'
        : props.listType === 'surprise'
          ? 'Маленький сюрприз'
          : 'Новое желание',
);

function resizeNote() {
  const field = noteInput.value?.control as HTMLTextAreaElement | undefined;
  if (!field) return;
  field.style.height = 'auto';
  field.style.height = `${field.scrollHeight}px`;
}

watch(
  () => form.description,
  () => void nextTick(resizeNote),
);
onMounted(() => void nextTick(() => requestAnimationFrame(resizeNote)));
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
let sharedDetails: SharedDetails | null = props.item || !props.seed?.url
  ? null
  : {
      url: props.seed.url,
      title: props.seed.title,
      price: props.seed.price,
      currency: props.seed.currency,
      image_id: props.seed.image_id,
    };

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


type FeedbackRef = { value: unknown };

function feedbackElement(target: FeedbackRef) {
  const value = target.value as HTMLElement | ComponentPublicInstance | undefined;
  if (!value) return undefined;
  return '$el' in value ? (value.$el as HTMLElement) : value;
}

async function revealFeedback(target: FeedbackRef) {
  await nextTick();
  if (target === sourceFeedback) {
    // Keep the title, source URL and its feedback together, not just the message.
    feedbackElement(target)?.closest('dialog')?.scrollTo({ top: 0, behavior: 'instant' });
    return;
  }
  feedbackElement(target)?.scrollIntoView?.({ block: 'nearest', behavior: 'instant' });
}

function scrollFocusedField(event: FocusEvent) {
  const target = event.target as HTMLElement | null;
  if (!target || !(target instanceof Element) || !target.matches('input, textarea, select')) return;
  window.setTimeout(() => {
    target.scrollIntoView?.({ block: 'center', behavior: 'smooth' });
  }, 300);
}

function pasteLink(event: ClipboardEvent) {
  event.preventDefault();
  const text = (event.clipboardData?.getData('text/plain') || '').trim();
  sharedDetails = extractSharedDetails(text);
  const url = sharedDetails?.url || text;
  if (!isWebUrl(url)) {
    sourceError.value = 'Вставьте ссылку, которая начинается с https:// или http://';
    return;
  }
  sourceError.value = '';
  form.url = url;
  pendingSharedUrl = url;
  autofillLink(true);
}

function isWebUrl(value: string) {
  try {
    const url = new URL(value);
    return /^https?:\/\/[^\s\\]+$/i.test(value) && !!url.hostname && !url.username && !url.password;
  } catch {
    return false;
  }
}

function updateSource(value: string) {
  form.url = value;
  sourceError.value = '';
}

function onPhotoUrlKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault();
    void uploadFromUrl();
  }
}

function pastePhotoUrl(event: ClipboardEvent) {
  event.preventDefault();
  const text = event.clipboardData?.getData('text/plain') || '';
  const url = extractSharedDetails(text)?.url || text.match(/https?:\/\/[^\s]+/)?.[0];
  if (!url || !isWebUrl(url)) {
    photoUrlError.value = 'Вставьте ссылку на изображение, начиная с https://';
    return;
  }
  photoUrl.value = url;
  void uploadFromUrl();
}

function togglePhotoUrl(open = !photoUrlOpen.value) {
  photoUrlOpen.value = open;
  photoUrlError.value = '';
  if (open) void nextTick(() => photoUrlInput.value?.focus());
  else void nextTick(() => (photoUrlToggle.value?.$el as HTMLButtonElement | undefined)?.focus());
}

function selectStore(host: string) {
  form.url = host ? `https://${host}/` : '';
  sourceError.value = '';
  sourceHint.value = '';
  lastAutoUrl = form.url;
  const store = certificateStore(form.url);
  form.title = store?.name || '';
  form.image_id = null;
  iconImageId.value = null;
}

function setVisibility(value: string) {
  form.surprise_visibility = value === 'private' ? 'private' : 'friends';
}

function onSourceBlur() {
  focusedField.value = '';
  if (form.url.trim() && !isWebUrl(form.url.trim())) {
    sourceError.value = 'Укажите ссылку целиком: https://example.com';
    return;
  }
  autofillLink();
}

function choosePhoto() {
  if (uploading.value || fetching.value || saving.value) return;
  fileInput.value?.click();
}

function removePhoto() {
  if (uploading.value || fetching.value || saving.value) return;
  form.image_id = null;
  iconImageId.value = null;
  photoUrl.value = '';
  photoUrlOpen.value = false;
  photoError.value = '';
  photoUrlError.value = '';
}

function onAreaClick(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (target.closest('button, input, textarea, select, a, .photo-url-details')) return;
  choosePhoto();
}

onMounted(() => {
  if (sharedDetails) autofillLink(true);
});

function autofillLink(fromShare = false) {
  const url = form.url.trim();
  if (!url || url === lastAutoUrl || fetching.value || uploading.value || saving.value) return;
  try {
    const parsed = new URL(url);
    if (!['https:', 'http:'].includes(parsed.protocol)) return;
    const host = parsed.hostname.toLowerCase();
    const social = /(^|\.)(instagram\.com|pinterest\.[a-z.]+|pin\.it|t\.me|telegram\.me)$/.test(
      host,
    );
    const avito =
      ['avito.ru', 'www.avito.ru', 'm.avito.ru'].includes(host) &&
      !parsed.username &&
      !parsed.password;
    // Marketplace pages often need an explicit fetch; blur should still try them.
    const marketplace =
      /(^|\.)(wildberries\.(ru|by|kz)|wb\.ru|ozon\.ru|lamoda\.ru|market\.yandex\.ru|megamarket\.ru|dns-shop\.ru|mvideo\.ru|citilink\.ru)$/.test(
        host,
      ) &&
      !parsed.username &&
      !parsed.password;
    if (!fromShare && form.item_type !== 'certificate' && !social && !avito && !marketplace)
      return;
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
  if (fileInput.value) fileInput.value.value = '';
  photoError.value = '';
  photoUrlError.value = '';
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    photoError.value = 'Выберите изображение JPEG, PNG или WebP';
    void revealFeedback(photoFeedback);
    return;
  }
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
  if (!isWebUrl(photoUrl.value.trim())) {
    photoUrlError.value = 'Укажите ссылку на изображение целиком: https://example.com/photo.jpg';
    return;
  }
  uploading.value = true;
  photoError.value = '';
  photoUrlError.value = '';
  try {
    const result = await send<{ id: string }>('/media/from-url', { url: photoUrl.value.trim() });
    form.image_id = result.id;
    photoUrl.value = '';
    photoUrlOpen.value = false;
  } catch (e) {
    photoUrlError.value = (e as Error).message;
    void revealFeedback(photoUrlInput);
  } finally {
    uploading.value = false;
  }
}

async function metadata() {
  if (fetching.value || uploading.value || saving.value) return;
  if (!isWebUrl(form.url.trim())) {
    sourceError.value = 'Укажите ссылку целиком: https://example.com';
    return;
  }
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
  if (form.url.trim() && !isWebUrl(form.url.trim())) {
    sourceError.value = 'Укажите ссылку целиком: https://example.com';
    return;
  }
  saving.value = true;
  saveError.value = '';
  try {
    if (form.item_type === 'certificate' && form.url.trim()) {
      const storeHost = (url: string) => {
        try {
          return certificateStore(url)?.host || new URL(url).hostname.toLowerCase().replace(/^www\./, '');
        } catch {
          return '';
        }
      };
      const existing = await api<Item[]>(`/users/${props.recipientId}/items/${props.listType}`);
      if (existing.some((item) => item.id !== props.item?.id && !item.archived_at && item.item_type === 'certificate' && storeHost(item.url || '') === storeHost(form.url.trim()))) {
        sourceError.value = 'Этот сертификат уже добавлен в список';
        return;
      }
    }
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
    if (descriptionOverLimit.value) {
      throw new Error(
        form.item_type === 'certificate'
          ? 'Заметка к сертификату — не больше 100 символов'
          : 'Заметка к желанию — не больше 500 символов',
      );
    }
    const payload: ItemInput = {
      item_type: form.item_type,
      title: form.title || null,
      description: form.description || null,
      url: form.url.trim() || null,
      image_id: form.image_id,
      price,
      currency: currency || null,
      price_mode: form.price_mode,
      surprise_visibility: props.listType === 'surprise' ? form.surprise_visibility : 'friends',
    };
    const saved = props.item
      ? await send<Item>(`/items/${props.item.id}`, payload, 'PUT')
      : await send<Item>('/items', {
        ...payload,
        recipient_id: props.recipientId,
        list_type: props.listType,
      } satisfies ItemCreate);
    if (props.listType === 'wishlist' && mostWanted.value !== (props.item?.most_wanted || false)) {
      await send(`/items/${props.item?.id || saved.id}/priority`, { most_wanted: mostWanted.value });
    }
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
  <Modal bare :title="formTitle" @close="!saving && emit('close')">
    <form class="item-form relative px-4 pb-4" @submit.prevent="save" @focusin="scrollFocusedField">
      <header class="wish-form-header photo-header">
        <AppButton
          variant="icon"
          class="form-back"
          label="Назад"
          :disabled="saving"
          @click="!saving && emit('close')"
        >
          <ArrowLeft :size="18" />
        </AppButton>
      </header>
      <section
        v-if="form.item_type !== 'certificate'"
        class="photo-section"
        aria-label="Фотография"
      >
        <div
          class="upload-area"
          :class="{ 'has-photo': form.image_id }"
          :aria-busy="uploading"
          @click="onAreaClick"
        >
          <WishImage
            v-if="form.image_id"
            :src="imageUrl(form.image_id, 800)"
            :is-icon="form.image_id === iconImageId"
            alt="Фотография подарка"
          /><AppButton
            v-if="!form.image_id"
            variant="custom"
            class="upload-button"
            :disabled="fetching || saving"
            :loading="uploading"
            :icon-size="26"
            @click="choosePhoto"
          >
            <span v-if="!uploading" class="upload-icon"><ImagePlus :size="26" /></span>
            <span>{{ uploading ? 'Загружаем…' : 'Добавить фото' }}</span>
          </AppButton>
          <p v-if="!form.image_id" class="upload-hint">
            Необязательно · JPEG, PNG или WebP · до 5 МБ
          </p>
          <p v-if="form.image_id && uploading" class="photo-progress" role="status">
            Загружаем фото…
          </p>
          <FieldMessage
            v-if="photoError"
            ref="photoFeedback"
            class="photo-error"
            kind="error"
            role="alert"
          >
            {{ photoError }}
          </FieldMessage>
          <div v-if="form.image_id" class="photo-actions">
            <AppButton
              variant="icon"
              class="photo-edit"
              :disabled="uploading || fetching || saving"
              label="Изменить картинку"
              @click="choosePhoto"
            >
              <Pencil :size="18" />
            </AppButton>
            <AppButton
              variant="icon"
              class="photo-delete"
              :disabled="uploading || fetching || saving"
              label="Удалить картинку"
              @click="removePhoto"
            >
              <Trash2 :size="18" />
            </AppButton>
          </div>
          <input
            ref="fileInput"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            hidden
            @change="upload"
          />
        </div>
        <div class="photo-url-details" :class="{ open: photoUrlOpen }" @click.stop>
          <AppButton
            ref="photoUrlToggle"
            variant="custom"
            class="photo-url-toggle"
            aria-controls="photo-url"
            :expanded="photoUrlOpen"
            :label="photoUrlOpen ? 'Свернуть поле ссылки' : 'Вставить ссылку на фото'"
            :disabled="uploading || fetching || saving"
            @click.stop="togglePhotoUrl()"
          >
            <Transition name="photo-link-icon" mode="out-in">
              <X v-if="photoUrlOpen" key="close" :size="18" />
              <Link v-else key="link" :size="18" />
            </Transition>
          </AppButton>
          <div class="photo-url-field">
            <FormField
              id="photo-url"
              ref="photoUrlInput"
              v-model="photoUrl"
                type="url"
              inputmode="url"
              :maxlength="2048"
              placeholder="Вставьте ссылку на фото"
              aria-label="Ссылка на фото"
              hint-id="photo-url-hint"
              hint-class="photo-url-error"
              :error="photoUrlError"
              :invalid="!!photoUrlError"
              :disabled="!photoUrlOpen || uploading || saving"
              :focused="focusedField === 'photoUrl'"
                :control-attrs="{
                  tabindex: photoUrlOpen ? 0 : -1,
                  autocapitalize: 'none',
                  spellcheck: false,
                }"
              @focus="focusedField = 'photoUrl'"
              @blur="focusedField = ''"
              @paste="pastePhotoUrl"
              @keydown="onPhotoUrlKeydown"
            >
              <template #clear-icon><X :size="14" /></template>
            </FormField>
          </div>
        </div>
      </section>
      <section v-if="form.item_type === 'certificate'" class="certificate-store-panel" aria-label="Популярные сертификаты">
        <div class="certificate-store-intro">
          <WishImage
            v-if="form.image_id && !certificateStore(form.url)"
            :src="imageUrl(form.image_id, 800)"
            :is-icon="true"
            alt="Иконка сертификата"
            class="mx-auto mb-4 size-16 rounded-2xl object-contain"
          />
          <h3>{{ customStoreTitle || 'Подарок на ваш вкус' }}</h3>
          <p v-if="!customStoreTitle">Выберите вариант или добавьте свой по ссылке</p>
        </div>
        <div class="certificate-store-carousel" role="group" aria-label="Выбрать сертификат">
          <AppButton
            v-for="store in certificateStores"
            :key="store.host"
            variant="custom"
            class="certificate-store-tile"
            :class="{ selected: certificateStore(form.url)?.host === store.host }"
            :pressed="certificateStore(form.url)?.host === store.host"
            :disabled="uploading || fetching || saving"
            @click="selectStore(store.host)"
          >
            <img :src="store.icon" alt="" />
            <span>{{ store.name }}</span>
          </AppButton>
        </div>
      </section>
      <div v-if="form.item_type !== 'certificate'" class="type-switch">
        <AppButton
          variant="custom"
          :class="{ selected: form.item_type === 'idea' }"
          :pressed="form.item_type === 'idea'"
          @click="form.item_type = 'idea'"
        >
          <Lightbulb :size="18" /><span>Идея</span></AppButton
        ><AppButton
          variant="custom"
          :class="{ selected: form.item_type === 'gift' }"
          :pressed="form.item_type === 'gift'"
          @click="form.item_type = 'gift'"
        >
          <Gift :size="18" /><span>Подарок</span></AppButton
        ><AppButton
          variant="custom"
          :class="{ selected: form.item_type === 'ticket' }"
          :pressed="form.item_type === 'ticket'"
          @click="form.item_type = 'ticket'"
        >
          <Ticket :size="18" /><span>Билет</span>
        </AppButton>
      </div>
      <p v-if="form.item_type !== 'certificate'" class="form-intro">
        {{
          form.item_type === 'idea'
            ? 'Запишите пожелание или подсказку — конкретную вещь выбирать не обязательно.'
            : form.item_type === 'ticket'
              ? 'Сохраните билет на концерт, спектакль или другое событие. По ссылке попробуем найти название и афишу.'
              : 'Сохраните конкретную вещь или пост. По ссылке попробуем найти название и фото.'
        }}
        <span v-if="listType === 'surprise'"> Получатель сюрприз не увидит.</span>
      </p>
      <fieldset v-if="listType === 'surprise'" class="surprise-visibility mb-5">
        <legend class="mb-2 text-sm font-medium">Кто видит сюрприз</legend>
        <div class="visibility-options" role="group" aria-label="Кто видит сюрприз">
          <AppButton variant="custom" :pressed="form.surprise_visibility === 'friends'" :disabled="saving" @click="setVisibility('friends')">Всем друзьям</AppButton>
          <AppButton variant="custom" :pressed="form.surprise_visibility === 'private'" :disabled="saving" @click="setVisibility('private')">Только мне</AppButton>
        </div>
      </fieldset>
      <div
        class="wish-editor-layout"
        :class="{ 'certificate-editor': form.item_type === 'certificate' }"
      >
        <div class="wish-editor-fields">
          <template
            v-for="section in fieldSections"
            :key="section"
          >
            <section
              v-if="section === 'identity' && form.item_type !== 'certificate'"
              class="form-section identity-section"
              aria-label="Карточка желания"
            >
              <FormField
                :model-value="form.title"
                :placeholder="
                  form.item_type === 'ticket'
                    ? 'Например, концерт или спектакль'
                    : form.item_type === 'gift'
                      ? 'Например, керамическая чашка'
                      : 'Например, что-нибудь для рисования'
                "
                @update:model-value="form.title = $event"
                :required="form.item_type === 'idea'"
                :maxlength="100"
                clearable
                clear-label="Очистить название"
                :focused="focusedField === 'title'"
                @focus="focusedField = 'title'"
                @blur="focusedField = ''"
              >
                <template #label>Название <span v-if="form.item_type === 'idea'">*</span></template>
                <template #clear-icon><X :size="15" /></template>
              </FormField>
            </section>
            <section
              v-if="section === 'source'"
              class="form-section source-section"
              :class="{ 'has-error': sourceError }"
              aria-label="Ссылка и автозаполнение"
            >
              <FormField
                :model-value="form.url"
                type="url"
                inputmode="url"
                :control-attrs="{
                  pattern: 'https?://[^\\s\\\\]+',
                  autocapitalize: 'none',
                  spellcheck: false,
                }"
                @update:model-value="updateSource"
                :placeholder="sourcePlaceholder"
                :required="form.item_type !== 'idea'"
                :maxlength="2048"
                :error="sourceError"
                :hint="
                  sourceHint ||
                  (form.item_type === 'certificate'
                    ? 'Ссылка на сертификат или впечатление.'
                    : form.url.trim() ? '' : 'Вставьте из «Поделиться», можно вместе с текстом.')
                "
                :message-role="sourceError ? 'alert' : sourceHint ? 'status' : 'none'"
                hint-id="source-link-hint"
                :hint-class="
                  sourceError
                    ? 'description-hint source-link-hint field-error'
                    : 'description-hint source-link-hint'
                "
                :invalid="!!sourceError"
                :disabled="uploading || saving"
                :focused="focusedField === 'url'"
                clearable
                clear-label="Очистить ссылку"
                @paste="pasteLink"
                @focus="focusedField = 'url'"
                @blur="onSourceBlur"
              >
                <template #label
                  >Ссылка
                  <span v-if="form.item_type !== 'idea'">*</span></template
                >
                <template #clear-icon><X :size="15" /></template>
              </FormField>
              <AppButton
                v-if="form.url && !(form.item_type === 'certificate' && certificateStore(form.url))"
                variant="custom"
                class="metadata-button"
                :disabled="uploading || saving"
                :loading="fetching"
                :icon-size="15"
                @click="metadata"
              >
                <Sparkles v-if="!fetching" :size="15" />{{
                  fetching
                    ? 'Ищем подробности…'
                    : form.item_type === 'certificate'
                      ? 'Обновить иконку и название'
                      : form.item_type === 'ticket'
                        ? 'Подтянуть название и афишу'
                        : 'Подтянуть название, цену и фото'
                }}
              </AppButton>
            </section>
          </template>
        </div>
        <section class="form-section details-section" aria-label="Дополнительные сведения">
          <AppButton
            v-if="listType === 'wishlist' && draft.item_type !== 'certificate'"
            variant="custom"
            class="most-wanted-toggle"
            :class="{ selected: mostWanted }"
            :pressed="mostWanted"
            :disabled="saving"
            @click="mostWanted = !mostWanted"
          >
            <Heart :size="19" :fill="mostWanted ? 'currentColor' : 'none'" />
            Очень хочу!
          </AppButton>
          <div class="personal-description">
            <FormField
              ref="noteInput"
              :model-value="draft.description"
              as="textarea"
              @update:model-value="draft.description = $event"
              label="Заметка"
              :rows="2"
              control-class="auto-grow"
              :placeholder="
                listType === 'surprise'
                  ? 'Почему это точно в его или её вкусе?'
                  : 'Цвет, размер или почему вам этого хочется…'
              "
              :hint="`Ваши слова · ${descriptionLength} / ${descriptionLimit}`"
              :error="descriptionOverLimit ? `Не больше ${descriptionLimit} символов · ${descriptionLength} / ${descriptionLimit}` : ''"
              :invalid="descriptionOverLimit"
              hint-id="personal-description-hint"
              :hint-class="['description-hint', { 'field-error': descriptionOverLimit }]"
              :message-role="descriptionOverLimit ? 'alert' : 'none'"
              :focused="focusedField === 'description'"
              clearable
              clear-label="Очистить заметку"
              @input="resizeNote"
              @focus="focusedField = 'description'"
              @blur="focusedField = ''"
            >
              <template #clear-icon><X :size="15" /></template>
            </FormField>
          </div>
          <PriceField
            v-if="draft.item_type !== 'certificate'"
            :model-value="draft.price"
            :mode="draft.price_mode"
            @update:model-value="draft.price = $event"
            @update:mode="draft.price_mode = $event"
          />
        </section>
      </div>
      <FieldMessage
        v-if="saveError"
        ref="saveFeedback"
        class="inline-error"
        kind="error"
        role="alert"
      >
        {{ saveError }}
      </FieldMessage>
      <FormActions>
        <AppButton variant="secondary" class="form-cancel" :disabled="saving" @click="emit('close')">
          Отмена
        </AppButton>
        <AppButton
          variant="primary"
          class="flex-1"
          type="submit"
          :disabled="uploading || fetching"
          :loading="saving"
        >
          {{
            saving
              ? 'Сохраняем…'
              : item
                ? 'Сохранить изменения'
                : draft.item_type === 'certificate'
                  ? 'Добавить сертификат'
                  : draft.item_type === 'ticket'
                    ? 'Добавить билет'
                    : 'Добавить желание'
          }}
        </AppButton>
      </FormActions>
    </form>
  </Modal>
</template>
