import type { Item } from './api'

export interface CertificateStore {
  name: string
  host: string
  icon: string
}

export const certificateStores: CertificateStore[] = [
  { name: 'Ozon', host: 'ozon.ru', icon: '/store-icons/ozon.svg' },
  { name: 'Wildberries', host: 'wildberries.ru', icon: '/store-icons/wildberries.svg' },
  { name: 'Яндекс Маркет', host: 'market.yandex.ru', icon: '/store-icons/yandex-market.svg' },
  { name: 'Золотое Яблоко', host: 'goldapple.ru', icon: '/store-icons/golden-apple.svg' },
  { name: 'Лэтуаль', host: 'letu.ru', icon: '/store-icons/letu.svg' },
  { name: 'Лемана ПРО', host: 'lemanapro.ru', icon: '/store-icons/lemana-pro.svg' },
  { name: 'М.Видео', host: 'mvideo.ru', icon: '/store-icons/mvideo.svg' },
  { name: 'DNS', host: 'dns-shop.ru', icon: '/store-icons/dns.svg' },
  { name: 'Спортмастер', host: 'sportmaster.ru', icon: '/store-icons/sportmaster.svg' },
  { name: 'Lamoda', host: 'lamoda.ru', icon: '/store-icons/lamoda.svg' },
]

export function certificateStore(url: string) {
  try {
    const host = new URL(url).hostname.toLowerCase().replace(/^www\./, '')
    return certificateStores.find((store) => host === store.host || host.endsWith(`.${store.host}`))
  } catch {
    return undefined
  }
}

export function certificateIcon(
  item: Pick<Item, 'item_type' | 'url' | 'image_id' | 'image_is_icon'>,
) {
  if (item.item_type !== 'certificate') return null
  if (item.image_id && !item.image_is_icon) return null
  return certificateStore(item.url || '')?.icon || null
}
