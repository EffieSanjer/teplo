<script setup lang="ts">
import { computed } from 'vue';
import Spinner from '../feedback/Spinner.vue';

// One button primitive for every action: text, outlined, filled, icon-only and
// field-clear buttons differ only by a variant, not by a separate component.
type Variant = 'primary' | 'secondary' | 'danger' | 'text' | 'icon' | 'clear' | 'custom';

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
