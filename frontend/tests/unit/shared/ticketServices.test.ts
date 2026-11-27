import { describe, expect, it } from 'vitest'
import { isTicketGift, ticketService } from '../../../src/shared/ticketServices'

describe('ticketServices', () => {
  it.each([
    ['https://afisha.yandex.ru/moscow/concert/show', 'Яндекс Афиша'],
    ['https://widget.afisha.yandex.ru/w/sessions/abc?clientKey=1', 'Яндекс Афиша'],
    ['https://www.kassir.ru/event/123', 'Kassir'],
    ['https://ticketland.ru/theater/play', 'Ticketland'],
    ['https://spb.kassir.ru/event/1', 'Kassir'],
  ])('recognizes %s', (url, name) => {
    expect(ticketService(url)?.name).toBe(name)
  })

  it('ignores shops and empty values', () => {
    expect(ticketService('https://www.wildberries.ru/catalog/1')).toBeUndefined()
    expect(ticketService('https://afisha.yandex.ru.evil.test/show')).toBeUndefined()
    expect(ticketService(null)).toBeUndefined()
    expect(ticketService('not-a-url')).toBeUndefined()
  })

  it('marks ticket items and gift items from ticket desks', () => {
    expect(
      isTicketGift({ item_type: 'gift', url: 'https://afisha.yandex.ru/moscow/concert' }),
    ).toBe(true)
    expect(
      isTicketGift({ item_type: 'ticket', url: 'https://theatre.example/show/1' }),
    ).toBe(true)
    expect(
      isTicketGift({ item_type: 'idea', url: 'https://afisha.yandex.ru/moscow/concert' }),
    ).toBe(false)
    expect(isTicketGift({ item_type: 'gift', url: 'https://shop.example/item' })).toBe(false)
  })
})
