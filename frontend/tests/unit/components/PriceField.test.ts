import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PriceField from '../../../src/components/ui/forms/PriceField.vue'

describe('PriceField', () => {
  it('keeps both optional modes inside the amount field', async () => {
    const wrapper = mount(PriceField, { props: { mode: 'exact', modelValue: '123456789' } })
    const field = wrapper.get('.price-value')
    const buttons = field.findAll('button')
    expect(buttons.map((button) => button.text())).toEqual(['Примерно', 'От'])
    expect(buttons.every((button) => button.attributes('aria-pressed') === 'false')).toBe(true)
    expect(field.get('input').element.value).toBe('123 456 789')

    await buttons[0]!.trigger('click')
    expect(wrapper.emitted('update:mode')?.at(-1)).toEqual(['approximate'])
    await wrapper.setProps({ mode: 'approximate' })
    await buttons[0]!.trigger('click')
    expect(wrapper.emitted('update:mode')?.at(-1)).toEqual(['exact'])

    await buttons[1]!.trigger('click')
    expect(wrapper.emitted('update:mode')?.at(-1)).toEqual(['from'])
    await wrapper.setProps({ mode: 'from' })
    await buttons[1]!.trigger('click')
    expect(wrapper.emitted('update:mode')?.at(-1)).toEqual(['exact'])
  })

  it('disables both modes along with the amount', () => {
    const wrapper = mount(PriceField, { props: { disabled: true } })
    expect(wrapper.get('input').attributes('disabled')).toBeDefined()
    expect(
      wrapper.findAll('button').every((button) => button.attributes('disabled') !== undefined),
    ).toBe(true)
  })
})
