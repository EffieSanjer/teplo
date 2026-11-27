<script setup lang="ts">
import { computed } from 'vue';
import Spinner from '../feedback/Spinner.vue';

// One button primitive for every action: text, outlined, filled, icon-only and
// field-clear buttons differ only by a variant, not by a separate component.
type Variant = 'primary' | 'secondary' | 'danger' | 'text' | 'icon' | 'glass-icon' | 'glass' | 'glass-secondary' | 'clear' | 'custom';

const props = withDefaults(
  defineProps<{
    variant?: Variant;
    as?: 'button' | 'summary';
    type?: 'button' | 'submit';
    disabled?: boolean;
    loading?: boolean;
    loadingText?: string;
    label?: string;
    title?: string;
    pressed?: boolean;
    expanded?: boolean;
    iconSize?: number;
  }>(),
  { variant: 'secondary', as: 'button', type: 'button' },
);

const tag = computed(() => (props.as === 'summary' ? 'summary' : 'button'));
const classes = computed(() => {
  switch (props.variant) {
    case 'primary':
      return ['button', 'primary'];
    case 'danger':
      return ['button', 'danger'];
    case 'text':
      return ['text-button'];
    case 'icon':
      return ['icon-button'];
    case 'glass-icon':
      return ['glass-icon-button'];
    case 'glass':
      return ['button', 'glass-button'];
    case 'glass-secondary':
      return ['button', 'glass-button', 'glass-button-secondary'];
    case 'clear':
      return ['clear-field'];
    case 'custom':
      // Specialized controls keep their own class; only loading/spinner logic
      // and the accessible-button contract come from the primitive.
      return [];
    default:
      return ['button', 'secondary'];
  }
});
const spinnerSize = computed(() => props.iconSize ?? (props.variant === 'clear' ? 14 : 17));
</script>

<template>
  <component
    :is="tag"
    :type="tag === 'button' ? type : undefined"
    :class="classes"
    :disabled="tag === 'button' ? disabled || loading : undefined"
    :aria-label="label"
    :title="title"
    :aria-pressed="pressed"
    :aria-expanded="expanded"
  >
    <Spinner v-if="loading" :size="spinnerSize" />
    <slot :loading="loading">{{ loadingText }}</slot>
  </component>
</template>

<style scoped>
.glass-icon-button {
  display: inline-grid;
  /* Keep the visible circle compact, but make its entire 48px touch target
     clickable, including the icon and the transparent space around it. */
  box-sizing: border-box;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  place-items: center;
  border: 0;
  border-radius: 50%;
  color: #faf7ee;
  background: radial-gradient(circle at center, rgb(0 0 0 / 15%) 19px, transparent 20px);
  cursor: pointer;
  touch-action: manipulation;
}
.glass-icon-button :deep(svg) { pointer-events: none; }
.glass-button {
  color: #faf7ee;
  background: rgb(255 255 255 / 13%);
  border: 1px solid rgb(255 255 255 / 18%);
  border-radius: 14px;
}
.glass-button-secondary { background: rgb(255 255 255 / 6%); }
.glass-icon-button:focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
.glass-icon-button:disabled { opacity: .5; cursor: default; }
</style>
