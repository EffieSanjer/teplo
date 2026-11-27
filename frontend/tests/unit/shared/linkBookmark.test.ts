import { describe, expect, it } from 'vitest'
import { linkBookmark } from '../../../src/shared/linkBookmark'

describe('linkBookmark', () => {
  it('uses known store brands without crowding the card with a path', () => {
    expect(linkBookmark('https://www.wildberries.ru/catalog/123/detail.aspx')).toMatchObject({
      host: 'wildberries.ru',
      name: 'Wildberries',
      mark: 'W',
      icon: '/store-icons/wildberries.svg',
      hint: 'По ссылке',
    })
    expect(linkBookmark('https://wb.ru/catalog/123/detail.aspx')).toMatchObject({
      name: 'Wildberries',
      icon: '/store-icons/wildberries.svg',
      hint: 'По ссылке',
    })
  })

  it('names a public Telegram post by channel', () => {
    expect(linkBookmark('https://t.me/finds/123')).toEqual({
      host: 't.me',
      name: '@finds',
      mark: 'F',
      hint: 'Пост в Telegram',
      icon: null,
    })
  })

  it('falls back to the host for an unknown shop', () => {
    expect(linkBookmark('https://shop.example/item')).toMatchObject({
      host: 'shop.example',
      name: 'shop.example',
      mark: 'S',
      hint: 'По ссылке',
      icon: null,
    })
  })

  it('rejects an unusable URL', () => {
    expect(linkBookmark('not a url')).toBeNull()
  })
})
