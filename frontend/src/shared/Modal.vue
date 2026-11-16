<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'
import type { CardOrigin } from './cardTransition'
const props = defineProps<{ title: string; variant?: 'item-detail'; photoRatio?: number; photoTone?: string; hasPhoto?: boolean; sheetHeight?: number; origin?: CardOrigin; surfaceStyle?: Record<string, string> }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement>()
let previous: HTMLElement | null = null
let previousOverflow = ''
const animations: Animation[] = []
let photoArt: HTMLElement | null = null
let contentObserver: ResizeObserver | undefined
function revealFromCard() {
  const modal = dialog.value, source = props.origin
  // Inset light-theme dialogs use a quiet reveal, not a moving photo handoff.
  if (document.documentElement.dataset.theme !== 'dark') return
  if (!modal || !source || typeof modal.animate !== 'function' || matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const target = modal.getBoundingClientRect()
  const styles = getComputedStyle(modal)
  const cardRadius = styles.getPropertyValue('--radius-card').trim() || '20px'
  const modalRadius = styles.borderTopLeftRadius || '0px'
  const timing = { duration: 420, easing: 'cubic-bezier(.22,.78,.18,1)' }
  const inset = `${Math.max(0, source.top - target.top)}px ${Math.max(0, target.right - source.left - source.width)}px ${Math.max(0, target.bottom - source.top - source.height)}px ${Math.max(0, source.left - target.left)}px round ${cardRadius}`
  animations.push(modal.animate([
    { clipPath: `inset(${inset})`, backgroundColor: source.background || getComputedStyle(modal).backgroundColor },
    { clipPath: `inset(0px 0px 0px 0px round ${modalRadius})`, backgroundColor: styles.backgroundColor },
  ], timing))
  for (const element of modal.querySelectorAll<HTMLElement>('.detail-body, .modal-header')) {
    animations.push(element.animate([
      { opacity: 0, transform: 'translateY(8px)' },
      { opacity: 1, transform: 'none' },
    ], { duration: 220, delay: 180, fill: 'backwards', easing: 'ease-out' }))
  }
  const detailPhoto = modal.querySelector<HTMLImageElement>('.detail-art img:not(.site-icon)')
  if (!source.photo || !detailPhoto) return
  const photoTarget = detailPhoto.getBoundingClientRect()
  if (!photoTarget.width || !photoTarget.height) return
  // Animate the actual image in its final layout. A fixed clone inside this
  // container-query dialog uses a different coordinate system and jumps on handoff.
  photoArt = detailPhoto.closest<HTMLElement>('.detail-art')
  photoArt?.classList.add('photo-revealing')
  const animation = detailPhoto.animate([
    { transformOrigin: '0 0', transform: `translate(${source.photo.left - photoTarget.left}px, ${source.photo.top - photoTarget.top}px) scale(${source.photo.width / photoTarget.width})`, borderRadius: cardRadius },
    { transformOrigin: '0 0', transform: 'none', borderRadius: getComputedStyle(detailPhoto).borderTopLeftRadius },
  ], timing)
  animations.push(animation)
  const finish = () => {
    photoArt?.classList.remove('photo-revealing')
  }
  void animation.finished.then(finish, finish)
}
onMounted(async () => {
  previous = document.activeElement as HTMLElement
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  await nextTick()
  dialog.value?.showModal()
  if (dialog.value) dialog.value.scrollTop = 0
   if (dialog.value && props.variant === 'item-detail') {
    const modal = dialog.value
    const body = modal.querySelector<HTMLElement>('.detail-body')
    if (body) {
      const measure = () => modal.style.setProperty('--detail-content-height', `${Math.ceil(body.getBoundingClientRect().height)}px`)
      measure()
      contentObserver = new ResizeObserver(measure)
      contentObserver.observe(body)
    }
  }
  await nextTick()
  // Both color themes use the same quiet, content-sized dialog reveal.
})
onBeforeUnmount(() => { contentObserver?.disconnect(); animations.forEach(animation => animation.cancel()); photoArt?.classList.remove('photo-revealing'); document.body.style.overflow = previousOverflow; previous?.focus({ preventScroll: true }) })
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="modal" :class="[variant, { 'detail-portrait': hasPhoto && photoRatio && photoRatio < 1, 'detail-has-photo': hasPhoto }]" :style="{ ...surfaceStyle, '--photo-ratio': photoRatio, '--photo-tone': photoTone, '--sheet-content-height': sheetHeight ? `${sheetHeight}px` : undefined }" aria-labelledby="modal-title" @cancel.prevent="emit('close')" @click="($event.target === dialog) && emit('close')">
      <div class="modal-inner">
        <header class="modal-header"><h2 id="modal-title">{{ title }}</h2><slot name="header-actions" /><button class="icon-button" aria-label="Закрыть" @click="emit('close')"><X :size="22" /></button></header>
        <slot />
      </div>
    </dialog>
  </Teleport>
</template>
