<script setup lang="ts">
import { ref } from 'vue';
import {
  Archive,
  ArrowLeft,
  MoreHorizontal,
  Check,
  ChevronDown,
  Gift,
  Heart,
  Layers,
  Link,
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-vue-next';
import {
  AppButton,
  Avatar,
  ConfirmDialog,
  EmptyState,
  FieldMessage,
  FormActions,
  FormField,
  LoadingLabel,
  PriceField,
  SkeletonGrid,
  Spinner,
  ToastMessage,
} from '../components/ui';

const search = ref('');
const url = ref('');
const note = ref('');
const country = ref('russia');
const priceValue = ref('1500');
const priceMode = ref<'exact' | 'approximate' | 'from'>('exact');
const pressed = ref(false);
const expanded = ref(false);
const showToast = ref(false);
const confirmKind = ref<'danger' | 'safe'>();
const busy = ref(false);
</script>

<template>
  <div class="mx-auto max-w-[1100px] px-5 py-8 min-[761px]:px-10">
    <header class="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <span class="flex items-center gap-2 text-xs text-muted">
          <Layers :size="14" /> Дизайн-система
        </span>
        <h1 class="mt-2 font-editorial text-3xl tracking-tight">Атомарные компоненты</h1>
        <p class="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Все примитивы интерфейса собраны на одной странице: кнопки, поля, состояния загрузки,
          пустые состояния, аватары и диалоги. Изменения в компонентах сразу видны здесь.
        </p>
      </div>
      <RouterLink
        to="/me"
        class="inline-flex min-h-10 items-center gap-2 rounded border border-line px-4 text-sm"
      >
        <Check :size="16" />Вернуться к вишлисту
      </RouterLink>
    </header>

    <section class="ui-section">
      <h2>AppButton — кнопки</h2>
      <p>Один компонент для всех действий: вариант задаёт стиль, остальное — параметры.</p>
      <div class="ui-row">
        <AppButton variant="primary"><Plus :size="17" />Добавить</AppButton>
        <AppButton variant="secondary"><Search :size="17" />Найти</AppButton>
        <AppButton variant="danger"><Trash2 :size="17" />Удалить</AppButton>
        <AppButton variant="text">Текстовая</AppButton>
        <AppButton variant="icon" label="Понравилось"><Heart :size="18" /></AppButton>
        <AppButton variant="custom" class="rounded border border-dashed border-line px-3 py-2">
          Custom
        </AppButton>
        <AppButton variant="primary" loading loading-text="Сохраняем…" />
      </div>
      <div class="ui-row">
        <AppButton variant="secondary" :pressed="pressed" @click="pressed = !pressed">
          pressed: {{ pressed }}
        </AppButton>
        <AppButton variant="secondary" :expanded="expanded" @click="expanded = !expanded">
          expanded: {{ expanded }}
        </AppButton>
        <div class="relative inline-flex size-8 items-center justify-center rounded bg-forest/10">
          <AppButton variant="clear" label="Очистить"><X :size="15" /></AppButton>
        </div>
        <details class="inline-block">
          <AppButton as="summary" variant="secondary">
            <ChevronDown :size="16" />summary
          </AppButton>
          <p class="mt-2 text-xs text-muted">Содержимое details</p>
        </details>
      </div>
    </section>

    <section class="ui-section">
      <h2>Полупрозрачные кнопки — сертификаты и желания</h2>
      <p>Круглые кнопки навигации — 40 px с областью нажатия 48 px; кнопки действий — с мягкой рамкой.</p>
      <div class="ui-row rounded-[24px] bg-gradient-to-br from-[#658464] to-[#171f19] p-5">
        <AppButton variant="glass-icon" label="Назад"><ArrowLeft :size="20" /></AppButton>
        <AppButton variant="glass-icon" label="Управление"><MoreHorizontal :size="20" /></AppButton>
        <AppButton variant="glass-icon" label="Закрыть"><X :size="18" /></AppButton>
        <AppButton variant="glass">Открыть ссылку<Link :size="18" /></AppButton>
        <AppButton variant="glass-secondary"><Heart :size="16" />Очень хочу</AppButton>
      </div>
    </section>

    <section class="ui-section">
      <h2>FormField, PriceField — поля</h2>
      <p>Иконка, очистка, undertext и тип контрола задаются параметрами.</p>
      <div class="ui-grid">
        <FormField
          v-model="search"
          label="Поиск с иконкой и очисткой"
          placeholder="Введите имя"
          :icon="Search"
          clearable
          clear-label="Очистить поиск"
          hint="Подсказка под полем"
        >
          <template #clear-icon><X :size="14" /></template>
        </FormField>
        <FormField
          :model-value="url"
          label="Поле с ошибкой"
          type="url"
          placeholder="https://…"
          :icon="Link"
          error="Введите корректную ссылку"
        />
        <FormField
          v-model="note"
          label="Многострочное поле"
          as="textarea"
          :rows="3"
          placeholder="Заметка…"
          :hint="`Символов: ${note.length}`"
        />
        <FormField v-model="country" label="Select" as="select" control-class="w-full">
          <template #options>
            <option value="russia">Россия</option>
            <option value="other">Другая страна</option>
          </template>
        </FormField>
      </div>
      <div class="ui-grid mt-5">
        <PriceField v-model="priceValue" :mode="priceMode" @update:mode="priceMode = $event" />
        <div>
          <span class="text-sm font-semibold">FieldMessage</span>
          <FieldMessage class="inline-hint">Обычная подсказка</FieldMessage>
          <FieldMessage kind="error" role="alert">Сообщение об ошибке</FieldMessage>
        </div>
      </div>
      <FormActions class="!static mt-5">
        <AppButton variant="secondary">Отмена</AppButton>
        <AppButton variant="primary">Сохранить</AppButton>
      </FormActions>
    </section>

    <section class="ui-section">
      <h2>Обратная связь</h2>
      <p>Спиннеры, подписи загрузки, скелетоны и пустые состояния.</p>
      <div class="ui-row">
        <Spinner :size="16" />
        <Spinner :size="28" />
        <LoadingLabel label="Загружаем данные…" />
        <LoadingLabel label="Ошибка загрузки" role="alert" />
      </div>
      <div class="ui-grid mt-5">
        <div>
          <span class="text-sm font-semibold">SkeletonGrid — карточки</span>
          <SkeletonGrid :count="2" label="Загрузка карточек" />
        </div>
        <div>
          <span class="text-sm font-semibold">SkeletonGrid — друзья</span>
          <SkeletonGrid :count="3" variant="friends" />
        </div>
      </div>
      <div class="ui-grid mt-5">
        <EmptyState title="Пока пусто" description="Здесь появятся ваши записи." :icon="Gift">
          <AppButton variant="primary"><Plus :size="16" />Добавить</AppButton>
        </EmptyState>
        <EmptyState
          title="Ничего не найдено"
          description="Попробуйте другой запрос."
          :icon="Search"
          alert
        />
      </div>
      <div class="ui-row mt-5">
        <AppButton variant="secondary" @click="showToast = !showToast">
          {{ showToast ? 'Скрыть' : 'Показать' }} toast
        </AppButton>
        <ToastMessage v-if="showToast" message="Изменения сохранены" />
      </div>
    </section>

    <section class="ui-section">
      <h2>Avatar — аватар</h2>
      <p>Фото пользователя и fallback из инициалов, если картинка недоступна.</p>
      <div class="ui-row">
        <Avatar name="Аня Смирнова" user-id="11111111-1111-4111-8111-111111111111" />
        <Avatar name="Мария Петрова" user-id="not-a-real-user" :count="1" />
        <Avatar name="Ольга" user-id="another-missing-user" class="size-20 text-2xl" />
      </div>
    </section>

    <section class="ui-section">
      <h2>ConfirmDialog — подтверждение</h2>
      <p>Общий диалог для опасных и обычных действий.</p>
      <div class="ui-row">
        <AppButton variant="danger" @click="confirmKind = 'danger'">
          <Trash2 :size="17" />Опасное действие
        </AppButton>
        <AppButton variant="primary" @click="confirmKind = 'safe'">
          <Archive :size="17" />Обычное действие
        </AppButton>
        <AppButton variant="secondary" :loading="busy" @click="busy = !busy">
          Состояние busy
        </AppButton>
      </div>
      <ConfirmDialog
        v-if="confirmKind"
        :title="confirmKind === 'danger' ? 'Удалить запись?' : 'В архив?'"
        description="Это демонстрация общего диалога подтверждения с подсказкой и ошибкой."
        hint="Действие можно отменить в демо в любой момент."
        error="Пример сообщения об ошибке"
        confirm-text="Подтвердить"
        :danger="confirmKind === 'danger'"
        :busy="busy"
        @close="confirmKind = undefined"
        @confirm="confirmKind = undefined"
      />
    </section>
  </div>
</template>

<style scoped>
@reference "../styles/index.css";

.ui-section {
  @apply mb-6 rounded-lg border border-line bg-paper p-5;
}
.ui-section h2 {
  @apply font-editorial text-xl;
}
.ui-section p {
  @apply mb-4 mt-1 text-xs leading-relaxed text-muted;
}
.ui-row {
  @apply flex flex-wrap items-center gap-3;
}
.ui-grid {
  @apply grid gap-5 min-[641px]:grid-cols-2;
}
</style>
