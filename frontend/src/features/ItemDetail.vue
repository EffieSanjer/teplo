<script setup lang="ts">
import { ArrowUpRight, Gift, Lightbulb, LockKeyhole, Store } from 'lucide-vue-next'
import Modal from '../shared/Modal.vue'
import { formatPrice, imageUrl, itemTitle, type Item } from '../shared/api'
import { openExternal } from '../integrations/telegram'
import WishImage from '../shared/WishImage.vue'
import WishArtwork from '../shared/WishArtwork.vue'
defineProps<{ item: Item; ownProfile: boolean; busy: boolean }>()
const emit = defineEmits<{ close: []; edit: [item: Item]; copy: [item: Item] }>()
</script>

<template>
  <Modal :title="itemTitle(item)" @close="emit('close')">
    <div class="detail-art" :class="item.image_id ? 'art-photo' : 'art-designed'"><WishImage v-if="item.image_id" :src="imageUrl(item.image_id)" :is-icon="item.image_is_icon" :alt="itemTitle(item)" /><WishArtwork v-else :seed="item.id" :type="item.item_type" /></div>
    <div class="detail-body"><span class="eyebrow"><Store v-if="item.item_type === 'certificate'" :size="14" /><Lightbulb v-else-if="item.item_type === 'idea'" :size="14" /><Gift v-else :size="14" />{{ item.item_type === 'certificate' ? 'Магазин для сертификата' : item.item_type === 'idea' ? 'Идея для подарка' : 'Конкретный подарок' }}</span><p v-if="item.item_type !== 'certificate'" class="detail-price">{{ formatPrice(item) }}</p><p class="detail-description">{{ item.description || (item.item_type === 'certificate' ? 'Сертификат в этот магазин — тоже хорошая идея для подарка.' : 'Иногда достаточно маленькой подсказки, чтобы порадовать друга.') }}</p><p v-if="item.list_type === 'surprise'" class="privacy-note"><LockKeyhole :size="16" />Сюрприз от {{ item.author_name }}. Получатель его не видит.</p><div class="detail-actions"><button v-if="item.url" class="button primary" @click="openExternal(item.url)">{{ item.item_type === 'certificate' ? 'Открыть магазин' : 'Открыть ссылку' }}<ArrowUpRight :size="17" /></button><button v-if="item.can_manage" class="button secondary" @click="emit('edit', item)">Редактировать</button><button v-if="!ownProfile && item.list_type === 'wishlist'" class="button secondary" :disabled="busy" @click="emit('copy', item)"><Gift :size="17" />{{ busy ? 'Добавляем…' : 'Создать сюрприз' }}</button></div></div>
  </Modal>
</template>

<style scoped>
.detail-art img { object-position: center; min-width: 0; min-height: 0; }
.detail-art:has(.site-icon) { height: 128px; }
</style>
