<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, watchEffect } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  Archive,
  ArrowLeft,
  Bookmark,
  Gift,
  LockKeyhole,
  Plus,
  RefreshCw,
} from 'lucide-vue-next';
import { api, itemTitle, send, session, type Item, type User } from '../shared/api';
import { notify } from '../shared/notifications';
import ItemCard from '../components/ItemCard.vue';
import ItemForm from '../components/ItemForm.vue';
import ItemDetail from '../components/ItemDetail.vue';
import FriendProfile from '../components/FriendProfile.vue';
import CertificateCarousel from '../components/CertificateCarousel.vue';
import Modal from '../components/Modal.vue';
import WishlistProfile from '../components/WishlistProfile.vue';
import type { CardOrigin } from '../shared/cardTransition';
import MasonryGrid from '../components/MasonryGrid.vue';
import {
  avatarFallback,
  sampleAvatarPalette,
  portraitInk,
  type AvatarPalette,
} from '../shared/avatarPalette';
import { theme } from '../shared/theme';
import { wishSeedFromQuery, type SharedDetails } from '../shared/sharedLink';
import { AppButton, ConfirmDialog, EmptyState, LoadingLabel, SkeletonGrid } from '../components/ui';

const route = useRoute(),
  router = useRouter();
const own = computed(() => !route.params.id || route.params.id === session.value?.user.id);
const recipientId = computed(() => String(route.params.id || session.value?.user.id || ''));
const listType = computed(() => (route.path.endsWith('/surprises') ? 'surprise' : 'wishlist'));
const items = ref<Item[]>([]),
  profile = ref<User | null>(null),
  loading = ref(true),
  error = ref('');
const formOpen = ref(false),
  editing = ref<Item>(),
  detail = ref<Item>(),
  deleting = ref<Item>();
const wishSeed = ref<SharedDetails>();
let sharedOpening = false;
const detailOrigin = ref<CardOrigin>();
function openDetail(item: Item, origin: CardOrigin) {
  detailOrigin.value = origin;
  detail.value = item;
}
const initialType = ref<Item['item_type']>('gift');
const busy = ref(false),
  deleteError = ref('');
const avatarPalette = ref<AvatarPalette>();
const friendCounts = ref({ wishes: 0, surprises: 0 });
const ownName = computed(() => session.value?.user.display_name || '');
watchEffect((onCleanup) => {
  if (!own.value) return;
  const id = recipientId.value;
  let active = true;
  const apply = (tones: AvatarPalette) => {
    document.documentElement.style.setProperty('--profile-canvas-tone', tones.primary);
    document.documentElement.style.setProperty('--profile-canvas-secondary', tones.secondary);
    document.documentElement.style.setProperty(
      '--page-contrast-ink',
      portraitInk(tones.primary, theme.value === 'dark'),
    );
  };
  apply(avatarPalette.value || avatarFallback(id));
  const image = new Image();
  image.onload = () => {
    const sampled = sampleAvatarPalette(image);
    if (!active) return;
    const tones = sampled || avatarFallback(id);
    avatarPalette.value = tones;
    apply(tones);
  };
  image.onerror = () => {
    if (!active) return;
    avatarPalette.value = avatarFallback(id);
    apply(avatarPalette.value);
  };
  image.src = `/api/v1/users/${encodeURIComponent(id)}/avatar`;
  onCleanup(() => {
    active = false;
    image.onload = null;
    image.onerror = null;
    document.documentElement.style.removeProperty('--profile-canvas-tone');
    document.documentElement.style.removeProperty('--profile-canvas-secondary');
    document.documentElement.style.removeProperty('--page-contrast-ink');
  });
});
const activeItems = computed(() => items.value.filter((i) => !i.archived_at));
const wishes = computed(() => activeItems.value.filter((i) => i.item_type !== 'certificate'));
const certificates = computed(() => activeItems.value.filter((i) => i.item_type === 'certificate'));
const archivedItems = computed(() => items.value.filter((i) => i.archived_at));
let generation = 0,
  lastRefresh = 0;

async function load(quiet = false) {
  const current = ++generation;
  if (own.value && listType.value === 'surprise') {
    await router.replace('/me');
    return;
  }
  const id = recipientId.value,
    type = listType.value;
  // Keep the verified heading while switching this person's tabs. Never reuse
  // another recipient's profile or show the previous tab's records while loading.
  if (profile.value?.id !== id) {
    profile.value = null;
    friendCounts.value = { wishes: 0, surprises: 0 };
  }
  if (!quiet) {
    loading.value = true;
    items.value = [];
    detail.value = undefined;
    if (!sharedOpening) formOpen.value = false;
    deleting.value = undefined;
  }
  error.value = '';
  try {
    const [user, data] = await Promise.all([
      api<User>(`/users/${id}`),
      api<Item[]>(`/users/${id}/items/${type}`),
    ]);
    if (current !== generation || !session.value) return;
    profile.value = user;
    items.value = data;
    lastRefresh = Date.now();
    const seed = own.value && type === 'wishlist' ? wishSeedFromQuery(route.query) : null;
    if (seed) {
      wishSeed.value = seed;
      initialType.value = 'gift';
      editing.value = undefined;
      detail.value = undefined;
      formOpen.value = true;
      sharedOpening = true;
      const nextQuery = { ...route.query };
      delete nextQuery.url;
      delete nextQuery.title;
      delete nextQuery.price;
      delete nextQuery.currency;
      delete nextQuery.image_id;
      void router.replace({ path: route.path, query: nextQuery });
    } else if (sharedOpening) sharedOpening = false;
    if (!own.value) {
      const count = (entries: Item[]) =>
        entries.filter((item) => !item.archived_at && item.item_type !== 'certificate').length;
      const otherType = type === 'wishlist' ? 'surprise' : 'wishlist';
      friendCounts.value[type === 'wishlist' ? 'wishes' : 'surprises'] = count(data);
      if (otherType === 'wishlist' || user.can_surprise) {
        void api<Item[]>(`/users/${id}/items/${otherType}`)
          .then((entries) => {
            if (current === generation)
              friendCounts.value[otherType === 'wishlist' ? 'wishes' : 'surprises'] =
                count(entries);
          })
          .catch(() => {
            /* A secondary counter must not block the visible list. */
          });
      }
    }
  } catch (e) {
    if (current === generation) {
      error.value = (e as Error).message;
      items.value = [];
      profile.value = null;
      detail.value = undefined;
      formOpen.value = false;
    }
  } finally {
    if (current === generation) loading.value = false;
  }
}
watch(
  () => route.fullPath,
  () => load(),
  { immediate: true },
);

function closeForm() {
  formOpen.value = false;
  wishSeed.value = undefined;
}
function add() {
  wishSeed.value = undefined;
  initialType.value = 'gift';
  editing.value = undefined;
  formOpen.value = true;
}
function addCertificate() {
  initialType.value = 'certificate';
  editing.value = undefined;
  formOpen.value = true;
}
function edit(item: Item) {
  detail.value = undefined;
  editing.value = item;
  formOpen.value = true;
}
async function saved() {
  formOpen.value = false;
  wishSeed.value = undefined;
  notify('Запись сохранена');
  await load(true);
}
async function archive(item: Item) {
  try {
    await send(`/items/${item.id}/archive`, { archived: !item.archived_at });
    detail.value = undefined;
    notify(item.archived_at ? 'Желание снова в списке' : 'Желание перенесено в архив');
    await load(true);
  } catch (e) {
    notify((e as Error).message);
  }
}
async function remove() {
  if (!deleting.value) return;
  busy.value = true;
  deleteError.value = '';
  try {
    await send(`/items/${deleting.value.id}`, undefined, 'DELETE');
    deleting.value = undefined;
    notify('Запись удалена');
    await load(true);
  } catch (e) {
    deleteError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function priority(item: Item) {
  if (busy.value) return;
  busy.value = true;
  try {
    const updated = await send<Item>(`/items/${item.id}/priority`, {
      most_wanted: !item.most_wanted,
    });
    detail.value = updated;
    items.value = items.value.map((entry) => (entry.id === updated.id ? updated : entry));
  } catch (e) {
    notify((e as Error).message);
  } finally {
    busy.value = false;
  }
}
async function reserve(item: Item) {
  if (busy.value) return;
  busy.value = true;
  try {
    const updated = await send<Item>(`/items/${item.id}/reservation`, {
      reserved: !item.reservation?.reserved_by_me,
    });
    detail.value = updated;
    items.value = items.value.map((entry) => (entry.id === updated.id ? updated : entry));
    notify(updated.reservation ? 'Подарок забронирован. Владелец не увидит бронь' : 'Бронь снята');
  } catch (e) {
    notify((e as Error).message);
    await load(true);
    detail.value = items.value.find((entry) => entry.id === item.id);
  } finally {
    busy.value = false;
  }
}
function refresh() {
  if (
    document.visibilityState === 'visible' &&
    Date.now() - lastRefresh > 15000 &&
    !formOpen.value &&
    !detail.value
  )
    void load(true);
}
onMounted(() => {
  window.addEventListener('focus', refresh);
  document.addEventListener('visibilitychange', refresh);
});
onBeforeUnmount(() => {
  generation++;
  window.removeEventListener('focus', refresh);
  document.removeEventListener('visibilitychange', refresh);
});
</script>

<template>
  <div class="page wishlist-page pb-28" :class="{ 'own-wishlist': own, 'friend-wishlist': !own }">
    <WishlistProfile v-if="own" :name="ownName" :user-id="recipientId" @add="add" />
    <FriendProfile
      v-else-if="profile"
      :key="profile.id"
      :user="profile"
      prominent
      :wish-count="friendCounts.wishes"
      :surprise-count="friendCounts.surprises"
    >
      <RouterLink
        :to="`/users/${recipientId}/wishlist`"
        :class="{ active: listType === 'wishlist' }"
        ><Bookmark :size="16" />Вишлист</RouterLink
      >
      <RouterLink
        v-if="profile.can_surprise"
        :to="`/users/${recipientId}/surprises`"
        :class="{ active: listType === 'surprise' }"
        ><Gift :size="16" />Сюрпризы</RouterLink
      >
    </FriendProfile>
    <div class="wishlist-layout">
      <section class="collection-board min-w-0" aria-label="Коллекция желаний">
        <div class="wishlist-content min-w-0 w-full" :aria-busy="loading">
          <Transition name="list-content" mode="out-in">
            <div
              v-if="loading"
              key="loading"
              class="list-loading"
              role="status"
              aria-label="Загрузка списка"
            >
              <LoadingLabel label="Загрузка…" />
              <SkeletonGrid :count="4" />
            </div>
            <EmptyState
              v-else-if="error"
              key="error"
              title="Не получилось загрузить список"
              :description="error"
              :icon="RefreshCw"
              :icon-size="32"
              alert
            >
              <AppButton variant="secondary" @click="load()">Попробовать ещё раз</AppButton>
            </EmptyState>
            <div v-else :key="`${recipientId}-${listType}`" class="list-content">
              <h2 class="visually-hidden">
                {{
                  listType === 'surprise' ? 'Секретные идеи' : own ? 'Мои желания' : 'Желания друга'
                }}
              </h2>
              <div v-if="!own && listType === 'surprise'" class="friend-list-tools">
                <p class="friend-secret-note">
                  <LockKeyhole :size="15" aria-hidden="true" />
                  Только между вами — сюрприз останется тайной.
                </p>
                <AppButton
                  v-if="!error"
                  variant="custom"
                  class="friend-add-surprise"
                  label="Добавить сюрприз"
                  @click="add"
                >
                  <Plus :size="18" />
                </AppButton>
              </div>
              <CertificateCarousel
                v-if="listType !== 'surprise'"
                :items="certificates"
                :can-add="own"
                @add="addCertificate"
                @open="openDetail"
              />
              <MasonryGrid v-if="wishes.length" class="collection-grid">
                <ItemCard
                  v-for="(item, index) in wishes"
                  :key="item.id"
                  :item="item"
                  :index="index"
                  @open="openDetail"
                />
              </MasonryGrid>
              <EmptyState
                v-if="!wishes.length && (listType === 'surprise' || !certificates.length)"
                class="collection-empty"
                title="Здесь скоро появится первое желание"
                :description="
                  own
                    ? 'Сохраните мысль, место, впечатление или вещь, к которой хочется вернуться.'
                    : listType === 'surprise'
                      ? 'Добавьте первую находку. Получатель её не увидит.'
                      : 'Друг ещё не добавил пожелания.'
                "
                :icon="Gift"
                :icon-size="38"
                :icon-width="1.2"
              >
                <AppButton v-if="own || listType === 'surprise'" variant="primary" @click="add">
                  <Plus :size="17" />Добавить {{ listType === 'surprise' ? 'сюрприз' : 'желание' }}
                </AppButton>
              </EmptyState>
              <details v-if="archivedItems.length" class="collection-archive" open>
                <AppButton as="summary" variant="custom">
                  <Archive :size="16" /><span>Архив</span
                  ><span class="count">{{ archivedItems.length }}</span>
                </AppButton>
                <MasonryGrid class="collection-grid"
                  ><ItemCard
                    v-for="(item, index) in archivedItems"
                    :key="item.id"
                    :item="item"
                    :index="index"
                    @open="openDetail"
                /></MasonryGrid>
              </details>
            </div>
          </Transition>
        </div>
      </section>
    </div>
    <ItemForm
      v-if="formOpen"
      :item="editing"
      :initial-type="initialType"
      :seed="wishSeed"
      :recipient-id="recipientId"
      :list-type="listType"
      @close="closeForm"
      @saved="saved"
    />
    <ItemDetail
      v-if="detail"
      :item="detail"
      :origin="detailOrigin"
      :own-profile="own"
      :busy="busy"
      @close="detail = undefined"
      @edit="edit"
      @priority="priority"
      @reserve="reserve"
      @archive="archive"
      @delete="
        deleting = $event;
        deleteError = '';
        detail = undefined;
      "
    />
    <ConfirmDialog
      v-if="deleting"
      title="Удалить желание?"
      :description="`«${itemTitle(deleting)}» будет удалено навсегда. Это действие нельзя отменить.`"
      :error="deleteError"
      :busy="busy"
      confirm-text="Удалить навсегда"
      busy-text="Удаляем…"
      @close="deleting = undefined"
      @confirm="remove"
    />
  </div>
</template>
