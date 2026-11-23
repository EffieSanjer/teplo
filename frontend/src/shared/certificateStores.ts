export const certificateStores = [
  { name: 'Ozon', host: 'ozon.ru', note: 'Покупки и подарки' },
  { name: 'Wildberries', host: 'wildberries.ru', note: 'Одежда, дом и многое другое' },
  { name: 'Яндекс Маркет', host: 'market.yandex.ru', note: 'Техника и товары для дома' },
  { name: 'Золотое Яблоко', host: 'goldapple.ru', note: 'Косметика и парфюмерия' },
  { name: 'Лэтуаль', host: 'letu.ru', note: 'Красота и уход' },
  { name: 'Лемана ПРО', host: 'lemanapro.ru', note: 'Дом, ремонт и сад' },
  { name: 'М.Видео', host: 'mvideo.ru', note: 'Техника и электроника' },
  { name: 'DNS', host: 'dns-shop.ru', note: 'Компьютеры и техника' },
  { name: 'Спортмастер', host: 'sportmaster.ru', note: 'Спорт и активный отдых' },
  { name: 'Читай-город', host: 'chitai-gorod.ru', note: 'Книги и вдохновение' },
  { name: 'Детский мир', host: 'detmir.ru', note: 'Для детей и родителей' },
  { name: 'Lamoda', host: 'lamoda.ru', note: 'Одежда и аксессуары' },
]
export function certificateStore(url: string) {
  try {
    const host = new URL(url).hostname.toLowerCase().replace(/^www\./, '')
    return certificateStores.find((store) => host === store.host || host.endsWith(`.${store.host}`))
  } catch {
    return undefined
  }
}
