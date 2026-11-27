<script setup lang="ts">
import { computed, ref } from 'vue';
import type { Component, HTMLAttributes } from 'vue';
import AppButton from '../buttons/AppButton.vue';
import FieldMessage from './FieldMessage.vue';

// All labeled controls share one primitive: text, search, URL, textarea and
// select differ only by props. Icons, clear buttons and hints are parameters.
const props = withDefaults(
  defineProps<{
    modelValue?: string;
    label?: string;
    required?: boolean;
    placeholder?: string;
    hint?: string;
    error?: string;
    hintId?: string;
    messageRole?: 'auto' | 'alert' | 'status' | 'none';
    id?: string;
    as?: 'input' | 'textarea' | 'select';
    type?: string;
    rows?: number;
    maxlength?: number;
    min?: number | string;
    max?: number | string;
    step?: number | string;
    inputmode?: string;
    autocomplete?: string;
    disabled?: boolean;
    readonly?: boolean;
    invalid?: boolean;
    clearable?: boolean;
    clearLabel?: string;
    clearVariant?: 'clear' | 'custom';
    clearClass?: string;
    focused?: boolean;
    autoGrow?: boolean;
    ariaLabel?: string;
    describedBy?: string;
    icon?: Component;
    iconSize?: number;
    controlClass?: HTMLAttributes['class'];
    hintClass?: HTMLAttributes['class'];
    controlAttrs?: Record<string, unknown>;
  }>(),
  {
    as: 'input',
    clearLabel: 'Очистить',
    clearVariant: 'clear',
    messageRole: 'auto',
    iconSize: 17,
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: string];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
  paste: [event: ClipboardEvent];
  keydown: [event: KeyboardEvent];
  input: [event: Event];
  clear: [];
}>();

const control = ref<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>();
const nativeError = ref('');
const fieldError = computed(() => props.error || nativeError.value);
const message = ref<HTMLElement>();
const showClear = computed(
  () => Boolean(props.modelValue) && props.clearable && !props.focused,
);
const describedBy = computed(
  () =>
    props.describedBy || (props.hintId && (props.hint || fieldError.value) ? props.hintId : undefined),
);
const messageRole = computed(() => {
  if (props.messageRole === 'none') return undefined;
  if (props.messageRole !== 'auto') return props.messageRole;
  return fieldError.value ? 'alert' : props.hint ? 'status' : undefined;
});

function update(event: Event) {
  nativeError.value = '';
  emit(
    'update:modelValue',
    (event.target as HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement).value,
  );
}
function clear() {
  nativeError.value = '';
  emit('update:modelValue', '');
  emit('clear');
  control.value?.focus();
}
defineExpose({ control, message, focus: () => control.value?.focus() });
</script>

<template>
  <label class="form-field" :for="id">
    <slot name="label"> {{ label }}<span v-if="required">*</span> </slot>
    <slot name="before" />
    <div
      class="form-field__control"
      :class="{
        'input-with-icon': icon,
        clearable: clearable && !icon,
      }"
    >
      <component :is="icon" v-if="icon" :size="iconSize" aria-hidden="true" />
      <component
        :is="as"
        :id="id"
        ref="control"
        :class="[controlClass, { 'auto-grow': autoGrow }]"
        :value="modelValue"
        :type="as === 'input' ? type : undefined"
        :rows="as === 'textarea' ? rows : undefined"
        :placeholder="placeholder"
        :maxlength="maxlength"
        :min="min"
        :max="max"
        :step="step"
        :inputmode="inputmode"
        :autocomplete="autocomplete"
        :disabled="disabled"
        :readonly="readonly"
        :required="required"
        :aria-label="ariaLabel"
        :aria-describedby="describedBy"
        :aria-invalid="invalid || !!fieldError || undefined"
        v-bind="controlAttrs"
        @invalid.prevent="nativeError = ($event.target as HTMLInputElement).validationMessage"
        @input="update"
        @focus="emit('focus', $event)"
        @blur="emit('blur', $event)"
        @paste="emit('paste', $event)"
        @keydown="emit('keydown', $event)"
      >
        <slot name="options" />
      </component>
      <AppButton
        v-if="showClear"
        :variant="clearVariant"
        :class="clearClass"
        :label="clearLabel"
        :disabled="disabled"
        type="button"
        @click.stop.prevent="clear"
      >
        <slot name="clear-icon">×</slot>
      </AppButton>
      <slot name="after" />
    </div>
    <FieldMessage
      v-if="fieldError || hint || $slots.hint"
      ref="message"
      :id="hintId"
      :kind="fieldError ? 'error' : 'hint'"
      :class="hintClass"
      :role="messageRole"
    >
      <template v-if="fieldError">{{ fieldError }}</template>
      <slot v-else name="hint">{{ hint }}</slot>
    </FieldMessage>
    <slot />
  </label>
</template>
