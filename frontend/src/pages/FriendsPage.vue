<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { Search, Users, UserPlus, UserMinus, X } from 'lucide-vue-next';
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api, send, session, type User } from '../shared/api';
import { shareInvitation } from '../integrations/telegram';
import { notify } from '../shared/notifications';
import Modal from '../components/Modal.vue';
import FriendProfile from '../components/FriendProfile.vue';
import { invitationToken } from '../shared/invitation';
import {
  AppButton,
  ConfirmDialog,
  EmptyState,
  FieldMessage,
  FormActions,
  FormField,
  LoadingLabel,
  SkeletonGrid,
} from '../components/ui';

const route = useRoute(),
  router = useRouter();
const users = ref<User[]>([]),
  loading = ref(true),
  error = ref(''),
  query = ref('');
const invitation = ref<{ url: string; expires_at: string }>(),
  inviting = ref(false),
  busy = ref(false),
  actionError = ref('');
const preview = ref<{ inviter: User; own: boolean }>(),
  previewError = ref(''),
  previewLoading = ref(false);
const removing = ref<User>();

const token = computed(() => (typeof route.query.invite === 'string' ? route.query.invite : ''));
const filtered = computed(() =>
  users.value.filter((u) =>
    u.display_name.toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase()),
  ),
);
const refreshError = ref('');
let generation = 0,
  last = 0;

async function load(quiet = false) {
  const current = ++generation;
  if (!quiet) loading.value = true;
  if (!quiet) error.value = '';
  refreshError.value = '';
  try {
    const result = await api<User[]>('/users');
    if (current === generation && session.value) {
      users.value = result;
      error.value = '';
      last = Date.now();
    }
  } catch (e) {
    if (current === generation) {
      if (quiet && !error.value) refreshError.value = (e as Error).message;
      else error.value = (e as Error).message;
    }
  } finally {
    if (current === generation) loading.value = false;
  }
}

function refresh() {
  if (document.visibilityState === 'visible' && Date.now() - last > 15000) void load(true);
}

async function createInvite() {
  if (busy.value) return;
  inviting.value = true;
  busy.value = true;
  actionError.value = '';
  invitation.value = undefined;
  try {
    invitation.value = await send('/friends/invitations');
  } catch (e) {
    actionError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}

async function revoke() {
  if (busy.value || !invitation.value) return;
  const token = invitationToken(invitation.value.url);
  if (!token) {
    actionError.value = 'Не удалось отозвать эту ссылку. Создайте новую.';
    return;
  }
  busy.value = true;
  actionError.value = '';
  try {
    await send(`/friends/invitations/${encodeURIComponent(token)}`, undefined, 'DELETE');
    invitation.value = undefined;
    inviting.value = false;
    notify('Приглашение отозвано');
  } catch (e) {
    actionError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}

async function copyLink() {
  if (!invitation.value) return;
  actionError.value = '';
  try {
    await navigator.clipboard.writeText(invitation.value.url);
    notify('Ссылка скопирована');
  } catch {
    actionError.value =
      'Не удалось скопировать автоматически. Выделите ссылку и скопируйте её вручную.';
  }
}

function shareLink() {
  if (!invitation.value || busy.value) return;
  actionError.value = '';
  try {
    shareInvitation(invitation.value.url);
  } catch {
    actionError.value = 'Не удалось открыть отправку. Скопируйте ссылку и отправьте её другу.';
  }
}

let previewGeneration = 0;
watch(
  token,
  async (value) => {
    const current = ++previewGeneration;
    preview.value = undefined;
    previewError.value = '';
    previewLoading.value = Boolean(value);
    if (!value) return;
    if (!/^[A-Za-z0-9_-]{43}$/.test(value)) {
      previewError.value = 'Приглашение недействительно';
      previewLoading.value = false;
      return;
    }
    try {
      const result = await api<{
        inviter: User;
        own: boolean;
      }>(`/friends/invitations/${encodeURIComponent(value)}`);
      if (current === previewGeneration) preview.value = result;
    } catch (e) {
      if (current === previewGeneration) previewError.value = (e as Error).message;
    } finally {
      if (current === previewGeneration) previewLoading.value = false;
    }
  },
  { immediate: true },
);

async function closePreview() {
  await router.replace({
    path: '/friends',
    query: { ...route.query, invite: undefined },
  });
}

async function acceptInvite() {
  if (busy.value || previewLoading.value || !preview.value || preview.value.own) return;
  const acceptedToken = token.value;
  busy.value = true;
  previewError.value = '';
  try {
    await send('/friends/accept', { token: acceptedToken });
    if (token.value === acceptedToken) await closePreview();
    notify('Вы теперь друзья');
    await load(true);
  } catch (e) {
    if (token.value === acceptedToken) previewError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}

async function removeFriend() {
  if (!removing.value || busy.value) return;
  busy.value = true;
  actionError.value = '';
  try {
    await send(`/friends/${removing.value.id}`, undefined, 'DELETE');
    removing.value = undefined;
    notify('Дружба прекращена');
    await load(true);
  } catch (e) {
    actionError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}

onMounted(() => {
  void load();
  window.addEventListener('focus', refresh);
  document.addEventListener('visibilitychange', refresh);
});
onBeforeUnmount(() => {
  generation++;
  previewGeneration++;
  window.removeEventListener('focus', refresh);
  document.removeEventListener('visibilitychange', refresh);
});
</script>

<template>
  <div class="page friends-page pb-28">
    <section class="friends-hero" aria-label="Друзья">
      <img
        class="friends-hero-image"
        alt=""
        width="1280"
        height="720"
        decoding="async"
        fetchpriority="high"
        sizes="100vw"
        src="/friends-hero-mobile.jpg"
        srcset="/friends-hero-mobile.jpg 768w, /friends-hero.jpg 1280w"
      />
      <div class="friends-hero-shade" aria-hidden="true" />
      <div class="friends-hero-content">
        <div class="friends-hero-copy">
          <h1 class="friends-hero-title">
            Друзья
            <span
              v-if="!loading && !error"
              class="friends-hero-count"
              role="status"
            >{{ users.length }}</span>
          </h1>
          <p class="friends-hero-lead">Делитесь желаниями без общей группы.</p>
        </div>
        <div class="friends-hero-actions">
          <AppButton
            variant="custom"
            class="friend-invite-action"
            :disabled="busy"
            @click="createInvite"
          >
            <UserPlus :size="17" />
            Пригласить друга
          </AppButton>
        </div>
      </div>
    </section>
    <div class="friends-layout">
      <section class="friends-directory" aria-label="Список друзей" :aria-busy="loading">
        <div class="friends-toolbar">
          <FormField
            v-model="query"
            class="search-input"
            type="search"
            :icon="Search"
            aria-label="Найти друга"
            placeholder="Найти друга"
            :maxlength="120"
            clearable
            clear-label="Очистить поиск"
            clear-variant="custom"
            clear-class="search-clear"
          >
            <template #clear-icon><X :size="16" /></template>
          </FormField>
          <span v-if="query" class="directory-count" role="status">{{ filtered.length }} найдено</span>
        </div>
        <div v-if="refreshError" class="friends-refresh-error" role="alert">
          <FieldMessage kind="error">Не удалось обновить список. {{ refreshError }}</FieldMessage>
          <AppButton variant="text" @click="load(true)">Повторить</AppButton>
        </div>
        <SkeletonGrid v-if="loading" :count="3" variant="friends" label="Загрузка друзей" />
        <EmptyState
          v-else-if="error"
          title="Не удалось загрузить друзей"
          :description="error"
          alert
        >
          <AppButton variant="secondary" @click="load()">Повторить</AppButton>
        </EmptyState>
        <EmptyState
          v-else-if="!filtered.length"
          :title="query ? 'Никого не нашли' : 'Пока только вы'"
          :description="query ? 'Попробуйте другое имя.' : 'Пригласите друга по ссылке.'"
          :icon="Users"
          :icon-size="36"
          :icon-width="1.3"
        />
        <div v-else class="friends-grid">
          <FriendProfile
            v-for="user in filtered"
            :key="user.id"
            :user="user"
            :to="`/users/${encodeURIComponent(user.id)}/wishlist`"
          >
            <AppButton
              v-if="user.is_friend"
              variant="custom"
              class="friend-remove"
              :disabled="busy"
              :label="`Удалить из друзей: ${user.display_name}`"
              @click="
                removing = user;
                actionError = '';
              "
            >
              <UserMinus :size="16" />
            </AppButton>
          </FriendProfile>
        </div>
      </section>
    </div>
    <Modal
      v-if="inviting"
      class="invite-modal"
      title="Пригласить друга"
      @close="!busy && (inviting = false)"
    >
      <div class="invite-modal-body">
        <p class="invite-modal-lead">Отправьте личную ссылку другу. Действует 7 дней.</p>
        <LoadingLabel
          v-if="busy"
          :label="invitation ? 'Отзываем приглашение…' : 'Готовим приглашение…'"
          role="status"
        />
        <template v-if="invitation">
          <FormField
            class="invite-link-label"
            label="Ссылка-приглашение"
            :model-value="invitation.url"
            control-class="invite-link"
            readonly
            @focus="($event.target as HTMLInputElement).select()"
          />
          <FormActions>
            <AppButton variant="secondary" :disabled="busy" @click="copyLink">
              Скопировать
            </AppButton>
            <AppButton variant="primary" :disabled="busy" @click="shareLink">
              Отправить другу
            </AppButton>
          </FormActions>
          <AppButton variant="text" :disabled="busy" @click="revoke"> Отозвать ссылку </AppButton>
        </template>
        <FieldMessage v-if="actionError" class="inline-error" kind="error" role="alert">
          {{ actionError }}
        </FieldMessage>
        <AppButton
          v-if="actionError && !invitation"
          variant="secondary"
          :disabled="busy"
          @click="createInvite"
        >
          Попробовать ещё раз
        </AppButton>
      </div>
    </Modal>
    <Modal
      v-if="token"
      class="invite-modal"
      title="Приглашение в друзья"
      @close="!busy && closePreview()"
    >
      <div class="invite-modal-body">
        <LoadingLabel v-if="previewLoading" label="Проверяем приглашение…" role="status" />
        <template v-if="preview">
          <h3 class="invite-modal-name">{{ preview.inviter.display_name }}</h3>
          <p class="invite-modal-lead">
            {{
              preview.own
                ? 'Это ваше приглашение — отправьте ссылку другу.'
                : 'После подтверждения откроются вишлисты друг друга.'
            }}
          </p>
          <AppButton
            v-if="!preview.own"
            variant="primary"
            :disabled="busy"
            :loading="busy"
            loading-text="Добавляем…"
            @click="acceptInvite"
          >
            {{ busy ? 'Добавляем…' : 'Добавить в друзья' }}
          </AppButton>
        </template>
        <template v-if="previewError">
          <FieldMessage class="inline-error" kind="error" role="alert">
            {{ previewError }}
          </FieldMessage>
        </template>
        <AppButton variant="text" :disabled="busy" @click="closePreview">Не сейчас</AppButton>
      </div>
    </Modal>
    <ConfirmDialog
      v-if="removing"
      title="Удалить из друзей?"
      :description="`Вы и ${removing.display_name} больше не сможете смотреть вишлисты друг друга по дружбе или списки сюрпризов друг для друга. Уже просмотренные данные отозвать нельзя.`"
      hint="Созданные сюрпризы сохранятся для остальных друзей получателя. Если вы состоите в общей группе, доступ к её спискам сохранится."
      :error="actionError"
      :busy="busy"
      confirm-text="Удалить из друзей"
      @close="removing = undefined"
      @confirm="removeFriend"
    />
  </div>
</template>
