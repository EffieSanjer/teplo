import type { Item } from './api'

export type TicketService = {
  name: string
  host: string
  mark: string
  accent: string
}

/** Known ticket desks and afisha aggregators; matched by hostname suffix. */
export const ticketServices: TicketService[] = [
  { name: 'Яндекс Афиша', host: 'afisha.yandex.ru', mark: 'ЯА', accent: '#1f3b57' },
  { name: 'Яндекс Афиша', host: 'widget.afisha.yandex.ru', mark: 'ЯА', accent: '#1f3b57' },
  { name: 'Афиша', host: 'afisha.ru', mark: 'АФ', accent: '#2a455c' },
  { name: 'Kassir', host: 'kassir.ru', mark: 'K', accent: '#3d617f' },
  { name: 'Ticketland', host: 'ticketland.ru', mark: 'TL', accent: '#24506f' },
  { name: 'МТС Live', host: 'live.mts.ru', mark: 'М', accent: '#2f5478' },
  { name: 'МТС Live', host: 'mtslive.ru', mark: 'М', accent: '#2f5478' },
  { name: 'Ponominalu', host: 'ponominalu.ru', mark: 'P', accent: '#3d5f78' },
  { name: 'Kassy', host: 'kassy.ru', mark: 'К', accent: '#4a6d8a' },
  { name: 'RedKassa', host: 'redkassa.ru', mark: 'RK', accent: '#35576f' },
  { name: 'Concert.ru', host: 'concert.ru', mark: 'C', accent: '#2a455c' },
  { name: 'BigBilet', host: 'bigbilet.ru', mark: 'BB', accent: '#3d617f' },
  { name: 'Ticketscloud', host: 'ticketscloud.ru', mark: 'TC', accent: '#24506f' },
  { name: 'Qtickets', host: 'qtickets.events', mark: 'Q', accent: '#2f5478' },
  { name: 'Russpass', host: 'russpass.ru', mark: 'RP', accent: '#1f3b57' },
  { name: 'Культура.рф', host: 'culture.ru', mark: 'КР', accent: '#3d5f78' },
]

export function ticketService(url: string | null | undefined) {
  if (!url?.trim()) return undefined
  try {
    const host = new URL(url).hostname.toLowerCase().replace(/^www\./, '')
    return ticketServices.find((service) => host === service.host || host.endsWith(`.${service.host}`))
  } catch {
    return undefined
  }
}

export function isTicketGift(item: Pick<Item, 'item_type' | 'url'>) {
  return (
    item.item_type === 'ticket' ||
    (item.item_type === 'gift' && Boolean(ticketService(item.url)))
  )
}
