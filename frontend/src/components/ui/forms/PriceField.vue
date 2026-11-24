<script setup lang="ts">
import AppButton from '../buttons/AppButton.vue';

type PriceMode = 'exact' | 'approximate' | 'from';
const priceOptions = [
  { value: 'approximate', label: 'Примерно' },
  { value: 'from', label: 'От' },
] as const;

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    mode?: PriceMode | null;
    id?: string;
    label?: string;
    disabled?: boolean;
    max?: number | string;
    step?: number | string;
    currency?: string;
  }>(),
  {
    modelValue: '',
    mode: 'exact',
    id: 'item-price',
    label: 'Стоимость',
    max: 999999999999.99,
    step: '0.01',
    currency: '₽',
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: string];
  'update:mode': [mode: PriceMode];
}>();
</script>

<template>
  <div class="price-field">
    <label :for="props.id">{{ props.label }}</label>
    <div class="price-value">
      <div class="price-options" role="group" aria-label="Уточнение стоимости">
        <AppButton
          v-for="option in priceOptions"
          :key="option.value"
          variant="custom"
          class="price-option"
          :class="{ selected: props.mode === option.value }"
          :pressed="props.mode === option.value"
          :disabled="props.disabled"
          @click="emit('update:mode', props.mode === option.value ? 'exact' : option.value)"
        >
          {{ option.label }}
        </AppButton>
      </div>
      <input
        :id="props.id"
        :value="props.modelValue"
        type="number"
        inputmode="decimal"
        min="0"
        :max="props.max"
        :step="props.step"
        placeholder="Сумма"
        :disabled="props.disabled"
        :aria-describedby="`${props.id}-mode-hint`"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <span class="price-currency" aria-hidden="true">{{ props.currency }}</span>
    </div>
    <span :id="`${props.id}-mode-hint`" class="sr-only" role="status">
      {{
        props.mode === 'approximate'
          ? 'Примерная сумма'
          : props.mode === 'from'
            ? 'Минимальная сумма'
            : 'Точная сумма'
      }}
    </span>
  </div>
</template>
