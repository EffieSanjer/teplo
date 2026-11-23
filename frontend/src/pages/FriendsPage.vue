<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { Search, Users, UserPlus, UserMinus, X } from 'lucide-vue-next';
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api, send, session, type User } from '../shared/api';
import { launchDiagnostics, shareInvitation } from '../integrations/telegram';
import { notify } from '../shared/notifications';
import Modal from '../components/Modal.vue';
import FriendProfile from '../components/FriendProfile.vue';
import { invitationToken } from '../shared/invitation';

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
const enteringInvite = ref(false),
  inviteInput = ref(''),
  inviteInputError = ref('');

async function openPastedInvite() {
  const parsed = invitationToken(inviteInput.value);
  if (!parsed) {
    inviteInputError.value = 'Вставьте полную ссылку приглашения из Telegram.';
    return;
  }
  enteringInvite.value = false;
  inviteInput.value = '';
  inviteInputError.value = '';
  await router.replace({ path: '/friends', query: { invite: parsed } });
}

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
  if (busy.value) return;
  busy.value = true;
  actionError.value = '';
  try {
    await send('/friends/invitations', undefined, 'DELETE');
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

async function replaceInvite() {
  await closePreview();
  enteringInvite.value = true;
  inviteInputError.value = '';
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
    <div class="friends-layout">
      <aside class="friends-intro">
        <span class="circle-eyebrow">ЛИЧНОЕ ПРОСТРАНСТВО / ЛЮДИ</span>
        <header class="page-heading">
          <div class="heading-context">
            <div class="heading-title">
              <h1>Друзья</h1>
              <span v-if="!loading && !error" class="count">
                {{ users.length }}
              </span>
            </div>
          </div>
        </header>
        <p class="friends-intro-copy">
          Близкие люди.<br />Маленькие подсказки.<br />Подарки со смыслом.
        </p>

        <div class="friend-actions">
          <button
            class="button primary friend-invite-action"
            :disabled="busy"
            @click="createInvite"
          >
            <UserPlus :size="17" />
            Пригласить друга
          </button>
          <button
            class="text-button received-invite"
            @click="
              enteringInvite = true;
              inviteInputError = '';
            "
          >
            У меня есть приглашение
          </button>
        </div>
      </aside>
      <section class="friends-directory" aria-label="Список друзей" :aria-busy="loading">
        <header class="circle-directory-heading">
          <span class="circle-eyebrow">МОЙ КРУГ</span>
          <h2>Те, кого хочется радовать</h2>
        </header>
        <div v-if="users.length || query" class="friends-toolbar">
          <label class="search-input">
            <Search :size="17" aria-hidden="true" />
            <input
              v-model="query"
              type="search"
              aria-label="Найти друга"
              placeholder="Найти друга"
              maxlength="120"
            />
            <button
              v-if="query"
              class="search-clear"
              aria-label="Очистить поиск"
              @click="query = ''"
            >
              <X :size="16" />
            </button> </label
          ><span class="directory-count" role="status">{{ filtered.length }} в круге</span>
        </div>
        <div v-if="refreshError" class="friends-refresh-error" role="alert">
          <p>Не удалось обновить список. {{ refreshError }}</p>
          <button class="text-button" @click="load(true)">Повторить</button>
        </div>
        <div v-if="loading" class="loading-grid" role="status" aria-label="Загрузка друзей">
          <div v-for="n in 3" :key="n" class="skeleton friend-skeleton" aria-hidden="true" />
        </div>
        <div v-else-if="error" class="empty-state">
          <h2>Не удалось загрузить друзей</h2>
          <p role="alert">{{ error }}</p>
          <button class="button secondary" @click="load()">Повторить</button>
        </div>
        <div v-else-if="!filtered.length" class="empty-state">
          <Users :size="36" :stroke-width="1.3" />
          <h2>{{ query ? 'Никого не нашли' : 'Пока только вы' }}</h2>
          <p>
            {{
              query
                ? 'Попробуйте другое имя.'
                : 'Пригласите друга по ссылке. После подтверждения вы сможете видеть вишлисты друг друга — общая группа не нужна.'
            }}
          </p>
        </div>
        <div v-else class="friends-grid">
          <FriendProfile
            v-for="user in filtered"
            :key="user.id"
            :user="user"
            :to="`/users/${encodeURIComponent(user.id)}/wishlist`"
          >
            <button
              v-if="user.is_friend"
              class="friend-remove"
              :disabled="busy"
              :aria-label="`Удалить из друзей: ${user.display_name}`"
              @click="
                removing = user;
                actionError = '';
              "
            >
              <UserMinus :size="16" />
            </button>
          </FriendProfile>
        </div>
      </section>
    </div>
    <Modal v-if="inviting" title="Пригласить друга" @close="!busy && (inviting = false)">
      <div class="confirm-body">
        <p>
          Отправьте ссылку тому, с кем хотите делиться желаниями. После подтверждения вы оба
          получите доступ к вишлистам и фотографиям друг друга.
        </p>
        <p class="inline-hint">
          Ссылка для одного друга, действует 7 дней. Новое приглашение отменяет предыдущее.
          Отправляйте её только лично.
        </p>
        <p v-if="busy" role="status">
          {{ invitation ? 'Отзываем приглашение…' : 'Готовим приглашение…' }}
        </p>
        <template v-if="invitation">
          <label class="invite-link-label"
            >Ссылка-приглашение<input
              class="invite-link"
              :value="invitation.url"
              readonly
              @focus="($event.target as HTMLInputElement).select()"
          /></label>
          <div class="form-actions">
            <button class="button secondary" :disabled="busy" @click="copyLink">Скопировать</button>
            <button class="button primary" :disabled="busy" @click="shareLink">
              Отправить другу
            </button>
          </div>
          <button class="text-button" :disabled="busy" @click="revoke">Отозвать ссылку</button>
        </template>
        <p v-if="actionError" class="inline-error" role="alert">{{ actionError }}</p>
        <button
          v-if="actionError && !invitation"
          class="button secondary"
          :disabled="busy"
          @click="createInvite"
        >
          Попробовать ещё раз
        </button>
      </div>
    </Modal>
    <Modal v-if="token" title="Приглашение в друзья" @close="!busy && closePreview()">
      <div class="confirm-body">
        <p v-if="previewLoading" role="status">Проверяем приглашение…</p>
        <template v-if="preview"
          ><h3>{{ preview.inviter.display_name }}</h3>
          <p>
            {{
              preview.own
                ? 'Это ваше приглашение — отправьте ссылку другу.'
                : 'Предлагает делиться желаниями. После подтверждения вы сможете смотреть вишлисты и фотографии друг друга.'
            }}
          </p>
          <p class="inline-hint">
            Вы также сможете добавлять сюрпризы для друга. Этот список видят его подтверждённые
            друзья, но не он сам. Сюрпризы для вас останутся скрыты, групповые списки не
            открываются. Дружбу можно прекратить в любой момент.
          </p>
          <button v-if="!preview.own" class="button primary" :disabled="busy" @click="acceptInvite">
            {{ busy ? 'Добавляем…' : 'Добавить в друзья' }}
          </button>
        </template>
        <template v-if="previewError"
          ><p class="inline-error" role="alert">
            {{ previewError }}
          </p>
          <button class="button secondary" :disabled="busy" @click="replaceInvite">
            Вставить актуальную ссылку
          </button>
        </template>
        <button class="text-button" :disabled="busy" @click="closePreview">Не сейчас</button>
      </div>
    </Modal>
    <Modal v-if="enteringInvite" title="Открыть приглашение" @close="enteringInvite = false">
      <form class="confirm-body" @submit.prevent="openPastedInvite">
        <p>
          Вставьте ссылку, которую прислал друг. Сначала покажем, от кого приглашение, — добавление
          только после вашего подтверждения.
        </p>
        <label class="invite-link-label"
          >Ссылка приглашения<input
            v-model="inviteInput"
            class="invite-link"
            aria-label="Полученная ссылка приглашения"
            placeholder="https://t.me/…"
            maxlength="2048"
            autocomplete="off"
            autocapitalize="off"
            :spellcheck="false"
        /></label>
        <p v-if="inviteInputError" class="inline-error" role="alert">
          {{ inviteInputError }}
        </p>
        <div class="form-actions">
          <button class="button primary" type="submit">Проверить приглашение</button>
        </div>
        <details class="inline-hint">
          <summary>Диагностика открытия по ссылке</summary>
          <p>{{ launchDiagnostics() }}</p>
        </details>
      </form>
    </Modal>
    <Modal v-if="removing" title="Удалить из друзей?" @close="!busy && (removing = undefined)">
      <div class="confirm-body">
        <p>
          Вы и {{ removing.display_name }} больше не сможете смотреть вишлисты друг друга по дружбе
          или списки сюрпризов друг для друга. Уже просмотренные данные отозвать нельзя.
        </p>
        <p class="inline-hint">
          Созданные сюрпризы сохранятся для остальных друзей получателя. Если вы состоите в общей
          группе, доступ к её спискам сохранится.
        </p>
        <p v-if="actionError" class="inline-error" role="alert">{{ actionError }}</p>
        <div class="form-actions">
          <button class="button secondary" :disabled="busy" @click="removing = undefined">
            Оставить
          </button>
          <button class="button danger" :disabled="busy" @click="removeFriend">
            Удалить из друзей
          </button>
        </div>
      </div>
    </Modal>
  </div>
</template>
