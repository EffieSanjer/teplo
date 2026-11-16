<script setup lang="ts">
import { computed, ref, watch, watchEffect } from 'vue'
import { type User } from '../shared/api'
import { certificateColor, type CertificateColor } from '../shared/certificateColor'
import { avatarFallback, sampleAvatarPalette, portraitInk, type AvatarPalette } from '../shared/avatarPalette'
import { theme } from '../shared/theme'

const props = defineProps<{ user: User; prominent?: boolean; to?: string }>()
const tone = ref<CertificateColor | null>(null), failed = ref(false)
const palette = ref<AvatarPalette>()
watchEffect((onCleanup) => {
  if (!props.prominent) return
  document.documentElement.style.setProperty('--profile-canvas-tone', (palette.value || avatarFallback(props.user.id)).primary)
  document.documentElement.style.setProperty('--page-contrast-ink', portraitInk((palette.value || avatarFallback(props.user.id)).primary, theme.value === 'dark'))
  onCleanup(() => {
    document.documentElement.style.removeProperty('--profile-canvas-tone')
    document.documentElement.style.removeProperty('--page-contrast-ink')
  })
})
const avatar = computed(() => `/api/v1/users/${encodeURIComponent(props.user.id)}/avatar`)
const initials = computed(() => props.user.display_name.split(/\s+/).map(name => name[0]).slice(0, 2).join(''))
const fallback = computed(() => {
  const hash = Array.from(props.user.id).reduce((value, char) => value + char.charCodeAt(0), 0)
  return ['#788271', '#ad7267', '#9c8b7a', '#6f807a'][hash % 4]
})
const style = computed(() => ({
  '--contrast-ink': portraitInk((palette.value || avatarFallback(props.user.id)).primary, theme.value === 'dark'),
  '--friend-tone': tone.value?.background || fallback.value, '--friend-ink': tone.value?.ink || '#ffffff',
  '--avatar-tone': (palette.value || avatarFallback(props.user.id)).primary,
  '--avatar-secondary': (palette.value || avatarFallback(props.user.id)).secondary,
  '--friend-photo': !failed.value ? `url('${avatar.value}')` : 'none',
}))
watch(() => props.user.id, () => { failed.value = false; tone.value = null; palette.value = undefined })
function photoLoaded(event: Event) {
  palette.value = sampleAvatarPalette(event.target as HTMLImageElement)
  try {
    const canvas = document.createElement('canvas')
    canvas.width = 32; canvas.height = 32
    const context = canvas.getContext('2d', { willReadFrequently: true })
    if (!context) return
    context.drawImage(event.target as HTMLImageElement, 0, 0, 32, 32)
    tone.value = certificateColor(context.getImageData(0, 0, 32, 32).data)
  } catch { /* Keep the palette fallback when canvas is unavailable. */ }
}
</script>

<template>
  <section class="friend-profile" :class="{ prominent }" :style="style">
    <div v-if="prominent" class="friend-profile-backdrop" aria-hidden="true" />
    <div v-if="prominent" class="profile-editorial-copy"><p>Заметить желание.<br />Угадать с подарком.</p><span>Вишлист друга</span></div>
    <div v-if="$slots.heading" class="friend-profile-heading"><slot name="heading" /></div>
    <RouterLink v-if="to" :to="to" class="friend-profile-link" :aria-label="`Вишлист: ${user.display_name}`" />
    <div v-if="prominent" class="profile-stat profile-stat-left"><slot name="stats-left" /></div>
    <div class="profile-avatar"><img v-if="!failed" :src="avatar" alt="" loading="lazy" @load="photoLoaded" @error="failed = true" /><span v-else>{{ initials }}</span></div>
    <div v-if="prominent" class="profile-stat profile-stat-right"><slot name="stats-right" /></div>
    <component :is="prominent ? 'h1' : 'h3'">{{ user.display_name }}</component>
    <p class="friend-profile-caption">Желания и находки</p>
    <div class="friend-profile-actions"><slot /></div>
  </section>
</template>

<style scoped src="../styles/scoped/friend-profile.css"></style>
