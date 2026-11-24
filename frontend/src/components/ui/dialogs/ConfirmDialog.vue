<script setup lang="ts">
import Modal from '../../Modal.vue';
import AppButton from '../buttons/AppButton.vue';
import FieldMessage from '../forms/FieldMessage.vue';
import FormActions from '../forms/FormActions.vue';

// The repeated "are you sure?" dialog: wish removal and friendship removal
// share the same body, hints, errors and action row.
withDefaults(
  defineProps<{
    title: string;
    description: string;
    hint?: string;
    error?: string;
    busy?: boolean;
    cancelText?: string;
    confirmText: string;
    busyText?: string;
    danger?: boolean;
  }>(),
  { cancelText: 'Оставить', busyText: '', danger: true },
);

const emit = defineEmits<{ close: []; confirm: [] }>();
</script>

<template>
  <Modal :title="title" @close="!busy && emit('close')">
    <div class="confirm-body">
      <p>{{ description }}</p>
      <FieldMessage v-if="hint" class="inline-hint">{{ hint }}</FieldMessage>
      <FieldMessage v-if="error" class="inline-error" kind="error" role="alert">
        {{ error }}
      </FieldMessage>
      <FormActions>
        <AppButton variant="secondary" :disabled="busy" @click="emit('close')">
          {{ cancelText }}
        </AppButton>
        <AppButton
          :variant="danger ? 'danger' : 'primary'"
          :loading="busy"
          :loading-text="busyText"
          @click="emit('confirm')"
        >
          {{ busy ? busyText : confirmText }}
        </AppButton>
      </FormActions>
    </div>
  </Modal>
</template>
