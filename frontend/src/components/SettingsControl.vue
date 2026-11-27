<script setup lang="ts">
import { ref } from 'vue';
import { AlertTriangle, Moon, Send, Settings, Sun } from 'lucide-vue-next';
import Modal from './Modal.vue';
import { ApiError, send } from '../shared/api';
import { theme, themePreference, setTheme, type ThemePreference } from '../shared/theme';
import { notify } from '../shared/notifications';
import { AppButton, FieldMessage } from './ui';

const open = ref(false);
const feedback = ref('');
const sending = ref(false);
const appVersion = import.meta.env.VITE_APP_VERSION || '0.1.0';

const themes: { value: ThemePreference; label: string }[] = [
  { value: 'light', label: 'Светлая' },
  { value: 'dark', label: 'Тёмная' },
  { value: 'system', label: 'Система' },
];

function chooseTheme(value: ThemePreference) {
  setTheme(value);
}

function isSelected(value: ThemePreference) {
  return themePreference.value === value;
}

async function sendFeedback() {
  const text = feedback.value.trim();
  if (!text || sending.value) return;
  sending.value = true;
  try {
    await send('/feedback', { message: text });
    feedback.value = '';
    notify('Отправлено разработчикам');
  } catch (error) {
    notify(error instanceof ApiError ? error.message : 'Не удалось отправить. Попробуйте ещё раз');
  } finally {
    sending.value = false;
  }
}
</script>

<template>
  <AppButton
    variant="icon"
    class="settings-control theme-control"
    label="Настройки"
    title="Настройки"
    @click.stop="open = true"
  >
    <Settings :size="19" aria-hidden="true" />
  </AppButton>

  <Modal
    v-if="open"
    title="Настройки"
    class="settings-modal"
    close-on-backdrop
    @close="open = false"
  >
    <div class="settings-body">
      <section class="settings-section" aria-label="Тема оформления">
        <h3 class="settings-label">Тема</h3>
        <div class="theme-options" role="radiogroup" aria-label="Тема оформления">
          <AppButton
            v-for="option in themes"
            :key="option.value"
            variant="custom"
            class="theme-option"
            :class="{ selected: isSelected(option.value) }"
            :pressed="isSelected(option.value)"
            role="radio"
            :aria-checked="isSelected(option.value)"
            @click="chooseTheme(option.value)"
          >
            <Sun v-if="option.value === 'light'" :size="16" aria-hidden="true" />
            <Moon v-else-if="option.value === 'dark'" :size="16" aria-hidden="true" />
            <span v-else class="theme-system-dot" aria-hidden="true" />
            {{ option.label }}
          </AppButton>
        </div>
        <p class="settings-hint">
          Сейчас на экране:
          {{ theme === 'dark' ? 'тёмная' : 'светлая' }}
        </p>
      </section>

      <section class="settings-section" aria-label="Предложения разработчикам">
        <h3 class="settings-label">Предложения разработчикам</h3>
        <p class="settings-hint">
          Напишите, что улучшить или что мешает — сообщение уйдёт разработчикам через бота.
        </p>
        <label class="settings-feedback">
          <span class="visually-hidden">Ваше предложение</span>
          <textarea
            v-model="feedback"
            rows="4"
            maxlength="1000"
            placeholder="Хотелось бы…"
          />
        </label>
        <AppButton
          variant="primary"
          class="settings-send"
          :disabled="!feedback.trim()"
          :loading="sending"
          loading-text="Отправляем…"
          @click="sendFeedback"
        >
          <Send :size="16" />Отправить предложение
        </AppButton>
      </section>

      <section class="settings-beta" role="note">
        <AlertTriangle :size="18" aria-hidden="true" />
        <div>
          <strong>Бета-версия {{ appVersion }}</strong>
          <FieldMessage class="inline-hint">
            Приложение ещё в разработке: отдельные экраны и сценарии могут меняться.
          </FieldMessage>
        </div>
      </section>
      <p class="settings-version">кстати, · v{{ appVersion }}</p>
    </div>
  </Modal>
</template>

<style scoped>
.settings-body {
  display: grid;
  gap: 1.35rem;
}
.settings-section {
  display: grid;
  gap: 0.65rem;
}
.settings-label {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
}
.settings-hint {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.45;
  color: var(--muted);
}
.theme-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.4rem;
  padding: 0.3rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface) 70%, var(--paper));
}
.theme-option {
  display: inline-flex;
  min-height: 2.5rem;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  border: 0;
  border-radius: 999px;
  padding: 0.4rem 0.5rem;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--muted);
  background: transparent;
}
.theme-option.selected,
.theme-option[aria-pressed='true'] {
  color: var(--ink);
  background: color-mix(in srgb, var(--accent) 16%, var(--surface));
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 35%);
}
.theme-system-dot {
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #f3f6f8 50%, #1a2733 50%);
  box-shadow: inset 0 0 0 1px rgb(26 43 58 / 25%);
}
.settings-feedback textarea {
  min-height: 6.5rem;
  border-radius: 16px;
  background: color-mix(in srgb, var(--surface) 80%, var(--paper));
}
.settings-send {
  width: 100%;
}
.settings-beta {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.75rem;
  align-items: start;
  padding: 0.9rem 1rem;
  border: 1px solid color-mix(in srgb, var(--ember) 35%, var(--line));
  border-radius: 18px;
  background:
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--ember) 14%, var(--surface)) 0%,
      color-mix(in srgb, var(--accent) 8%, var(--surface)) 100%
    );
}
.settings-beta strong {
  display: block;
  margin-bottom: 0.15rem;
  font-size: 0.92rem;
}
.settings-beta :deep(.inline-hint) {
  margin-top: 0;
}
.settings-version {
  margin: 0;
  text-align: center;
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  color: var(--muted);
}
</style>
