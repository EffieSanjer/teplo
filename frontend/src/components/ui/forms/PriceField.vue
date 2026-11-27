<script setup lang="ts">
import { computed, nextTick } from 'vue';
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
function formatAmount(value: string) {
  const [integer = '', fraction] = value.split('.');
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (fraction === undefined ? '' : `,${fraction}`);
}
const displayAmount = computed(() => formatAmount(props.modelValue));
async function updateAmount(event: Event) {
  const input = event.target as HTMLInputElement;
  const before = input.value.slice(0, input.selectionStart ?? input.value.length).replace(/\s/g, '').length;
  const raw = input.value.replace(/\s/g, '').replace(',', '.');
  if (!/^\d*(\.\d{0,2})?$/.test(raw)) {
    input.value = displayAmount.value;
    return;
  }
  emit('update:modelValue', raw);
  await nextTick();
  input.value = formatAmount(raw);
  let position = 0;
  let count = 0;
  while (position < input.value.length && count < before) {
    if (input.value[position] !== ' ') count++;
    position++;
  }
  input.setSelectionRange(position, position);
}
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
        :value="displayAmount"
        type="text"
        inputmode="decimal"
        min="0"
        :max="props.max"
        :step="props.step"
        placeholder="Сумма"
        :disabled="props.disabled"
        :aria-describedby="`${props.id}-mode-hint`"
        @input="updateAmount"
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
