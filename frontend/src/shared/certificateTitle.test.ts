import { describe, expect, it } from 'vitest'
import { certificateTitle } from './certificateTitle'

describe('certificateTitle', () => {
  it.each(['-', '–', '—'])('uses a spaced %s as a subtitle separator', separator => {
    expect(certificateTitle(`Книжный клуб ${separator} Книги и подарки`))
      .toEqual({ name: 'Книжный клуб', description: 'Книги и подарки' })
  })
  it('keeps hyphenated names intact and only splits once', () => {
    expect(certificateTitle('Арт-студия - Курсы - Для двоих'))
      .toEqual({ name: 'Арт-студия', description: 'Курсы - Для двоих' })
    expect(certificateTitle('Арт-студия')).toEqual({ name: 'Арт-студия', description: '' })
  })
  it('does not create an empty subtitle', () => {
    expect(certificateTitle('Магазин - ')).toEqual({ name: 'Магазин - ', description: '' })
  })
})
