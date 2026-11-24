import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import FormField from '../../../src/components/ui/forms/FormField.vue'

describe('FormField validation', () => {
  it('keeps counting beyond 500 and replaces the hint with an inline error', () => {
    const value = 'a'.repeat(513)
    const wrapper = mount(FormField, {
      props: {
        as: 'textarea', modelValue: value,
        hint: 'Ваши слова · 513 / 500',
        error: 'Не больше 500 символов · 513 / 500',
      },
    })
    expect(wrapper.get('textarea').element.value.length).toBe(513)
    expect(wrapper.get('textarea').attributes('maxlength')).toBeUndefined()
    expect(wrapper.get('textarea').attributes('aria-invalid')).toBe('true')
    expect(wrapper.text()).toContain('Не больше 500 символов · 513 / 500')
    expect(wrapper.text()).not.toContain('Ваши слова')
  })

  it('shows native validation errors inline and clears them on input', async () => {
    const wrapper = mount(FormField, { props: { required: true, hint: 'Подсказка' } })
    await wrapper.get('input').trigger('invalid')
    expect(wrapper.get('input').attributes('aria-invalid')).toBe('true')
    expect(wrapper.text()).not.toContain('Подсказка')
    await wrapper.get('input').setValue('Название')
    expect(wrapper.get('input').attributes('aria-invalid')).toBeUndefined()
    expect(wrapper.text()).toContain('Подсказка')
  })
})
