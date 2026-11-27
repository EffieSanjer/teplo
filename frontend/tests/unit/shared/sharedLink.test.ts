import { describe, expect, it } from 'vitest'
import { extractSharedDetails, extractSharedLink, wishSeedFromQuery } from '../../../src/shared/sharedLink'

describe('links copied from share sheets', () => {
  it.each([
    ['https://example.com/product?a=1&b=2#photo', 'https://example.com/product?a=1&b=2#photo'],
    ['Смотрите находку!\nhttps://pin.it/abc\nЭто точно твоё', 'https://pin.it/abc'],
    ['Пост: «https://t.me/finds/123?single»', 'https://t.me/finds/123?single'],
    ['Нашёл (https://example.com/item).', 'https://example.com/item'],
    ['[https://example.com/item]', 'https://example.com/item'],
    ['Книга https://example.com/Book_(edition)', 'https://example.com/Book_(edition)'],
    [
      'Смотри https://www.instagram.com/reel/abc/?igsh=123…',
      'https://www.instagram.com/reel/abc/?igsh=123',
    ],
    ['www.example.com/shop?item=1', 'https://www.example.com/shop?item=1'],
    ['https://пример.рф/подарок', 'https://пример.рф/подарок'],
    ['https://example.com/first https://example.com/second', 'https://example.com/first'],
  ])('extracts from %s without importing the caption', (text, expected) => {
    expect(extractSharedLink(text)).toBe(expected)
  })
  it.each([
    '',
    'Хочу на выходные за город',
    'javascript:alert(1)',
    'file:///etc/passwd',
    'https://',
    'https://user:pass@example.com',
    `https://example.com/${'a'.repeat(2048)}`,
  ])('ignores invalid or unsupported input %s', (text) => {
    expect(extractSharedLink(text)).toBeNull()
  })
})

describe('share caption metadata', () => {
  it('handles the actual marketplace share messages', () => {
    expect(
      extractSharedDetails(
        'https://www.wildberries.ru/catalog/1126771984/detail.aspx?targetUrl=SN, Свеча ароматическая Ta&Ko Home за 2\u00a0850\u00a0₽',
      ),
    ).toMatchObject({
      url: 'https://www.wildberries.ru/catalog/1126771984/detail.aspx?targetUrl=SN',
      title: 'Свеча ароматическая Ta&Ko Home',
      price: '2850',
      currency: 'RUB',
    })
    expect(
      extractSharedDetails(
        'TESLA BATTERIES BLACK+ ААА 24 шт Батарейки щелочные, 1,5V\nhttps://ozon.ru/t/gmg46Bl',
      ),
    ).toEqual({
      url: 'https://ozon.ru/t/gmg46Bl',
      title: 'TESLA BATTERIES BLACK+ ААА 24 шт Батарейки щелочные, 1,5V',
    })
  })
  it.each([
    [
      'Керамическая чашка\nЦена: 1 290,50 ₽\nhttps://example.com/item',
      'Керамическая чашка',
      '1290.50',
      'RUB',
    ],
    ['Лампа — 2400 руб. https://example.com/item', 'Лампа', '2400', 'RUB'],
    ['Название: Книга\nСтоимость: 19.99 EUR\nhttps://example.com/item', 'Книга', '19.99', 'EUR'],
    ['Рюкзак\nот 12\u202f500 ₸\nhttps://example.com/item', 'Рюкзак', '12500', 'KZT'],
    ['Блокнот\n0 RUB\nhttps://example.com/item', 'Блокнот', '0', 'RUB'],
    ['Блокнот\n$19.99\nhttps://example.com/item', 'Блокнот', '19.99', 'USD'],
  ])('extracts an explicit title and currency price from %s', (text, title, price, currency) => {
    expect(extractSharedDetails(text)).toMatchObject({
      url: 'https://example.com/item',
      title,
      price,
      currency,
    })
  })
  it('recognizes minimum prices without guessing from numbers', () => {
    expect(extractSharedDetails('Лампа от 1200 ₽ https://example.com/item')).toMatchObject({
      price: '1200',
      price_mode: 'from',
    })
    expect(
      extractSharedDetails('Модель 2026 размер 42 https://example.com/item')?.price,
    ).toBeUndefined()
    expect(extractSharedDetails('Скидка 50% https://example.com/item')?.price).toBeUndefined()
    expect(
      extractSharedDetails('Лампа 1000 ₽ вместо 2000 ₽ https://example.com/item')?.price,
    ).toBeUndefined()
    expect(
      extractSharedDetails('Лампа 1000000000000 ₽ https://example.com/item')?.price,
    ).toBeUndefined()
  })
  it('ignores generic share messages and URL query numbers', () => {
    expect(
      extractSharedDetails('Посмотри находку!\nhttps://example.com/item?price=123\nПоделиться'),
    ).toEqual({ url: 'https://example.com/item?price=123' })
    expect(extractSharedDetails('https://example.com/item')).toEqual({
      url: 'https://example.com/item',
    })
    expect(extractSharedDetails('Нет ссылки')).toBeNull()
  })
  it('reads a bot launch query and drops an incomplete price', () => {
    expect(
      wishSeedFromQuery({
        url: 'https://shop.example/item',
        title: '  Лампа  ',
        price: '1200.50',
        currency: 'RUB',
        image_id: '11111111-1111-4111-8111-111111111111',
      }),
    ).toEqual({
      url: 'https://shop.example/item',
      title: 'Лампа',
      price: '1200.50',
      currency: 'RUB',
      image_id: '11111111-1111-4111-8111-111111111111',
    })
    expect(wishSeedFromQuery({ url: 'https://shop.example/item', price: '10' })).toEqual({
      url: 'https://shop.example/item',
    })
    expect(
      wishSeedFromQuery({
        url: 'https://shop.example/item',
        image_id: 'not-a-uuid',
      }),
    ).toEqual({ url: 'https://shop.example/item' })
    expect(wishSeedFromQuery({ url: 'javascript:alert(1)', title: 'Lamp' })).toBeNull()
  })
})
