<script setup lang="ts">
import { ArrowUpRight, Gift, Lightbulb, LockKeyhole, Store } from 'lucide-vue-next'
import Modal from '../shared/Modal.vue'
import { formatPrice, imageUrl, itemTitle, type Item } from '../shared/api'
import { openExternal } from '../integrations/telegram'
defineProps<{ item: Item; ownProfile: boolean; busy: boolean }>()
const emit = defineEmits<{ close: []; edit: [item: Item]; copy: [item: Item] }>()
</script>

<template>
  <Modal :title="itemTitle(item)" @close="emit('close')">
    <div class="detail-art" :class="item.image_id ? 'art-photo' : 'art-paper'"><img v-if="item.image_id" :src="imageUrl(item.image_id)" :alt="itemTitle(item)" /><Store v-else-if="item.item_type === 'certificate'" :size="85" :stroke-width="1.4" /><Gift v-else :size="85" :stroke-width="1.4" /></div>
    <div class="detail-body"><span class="eyebrow"><Store v-if="item.item_type === 'certificate'" :size="14" /><Lightbulb v-else-if="item.item_type === 'idea'" :size="14" /><Gift v-else :size="14" />{{ item.item_type === 'certificate' ? 'Магазин для сертификата' : item.item_type === 'idea' ? 'Идея для подарка' : 'Конкретный подарок' }}</span><p class="detail-price">{{ item.item_type === 'certificate' && item.price == null ? 'Любой номинал' : formatPrice(item) }}</p><p v-if="item.price != null" class="muted small">{{ item.price_mode === 'from' ? 'Сумма — нижний ориентир для подарка' : 'Цена — ориентир, а не обещание магазина' }}</p><p class="detail-description">{{ item.description || (item.item_type === 'certificate' ? 'Сертификат в этот магазин — тоже хорошая идея для подарка.' : 'Иногда достаточно маленькой подсказки, чтобы порадовать друга.') }}</p><p v-if="item.list_type === 'surprise'" class="privacy-note"><LockKeyhole :size="16" />Сюрприз от {{ item.author_name }}. Получатель его не видит.</p><div class="detail-actions"><button v-if="item.url" class="button primary" @click="openExternal(item.url)">{{ item.item_type === 'certificate' ? 'Открыть магазин' : 'Открыть ссылку' }}<ArrowUpRight :size="17" /></button><button v-if="item.can_manage" class="button secondary" @click="emit('edit', item)">Редактировать</button><button v-if="!ownProfile && item.list_type === 'wishlist'" class="button secondary" :disabled="busy" @click="emit('copy', item)"><Gift :size="17" />{{ busy ? 'Добавляем…' : 'Создать сюрприз' }}</button></div></div>
  </Modal>
</template>

<style scoped>
.detail-art img { object-position: center; min-width: 0; min-height: 0; }
</style>
