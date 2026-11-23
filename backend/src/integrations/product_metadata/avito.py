"""Public listing metadata only; never use the app shell as a product preview."""

from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .marketplaces import embedded_product, merge_product, product_ref
from .network import FetchError
from .parser import parse_metadata, parse_price


def is_avito(url):
    parts = urlsplit(url)
    return (parts.scheme in {"http", "https"} and not parts.username and not parts.password
            and parts.hostname in {"avito.ru", "www.avito.ru", "m.avito.ru"})


def parse_avito(html, url, requested_url):
    ref = product_ref(requested_url)
    if not ref or ref[0] != "avito" or product_ref(url) != ref:
        raise FetchError("Авито не предоставил страницу объявления. Ссылку можно сохранить вручную")
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True).casefold() if soup.title else ""
    text = soup.get_text(" ", strip=True)[:4000].casefold()
    raw = html[:50_000].decode("utf-8", "ignore").casefold()
    challenge_markers = (
        "captcha", "доступ ограничен", "проверка браузера", "подтвердите",
        "проблемы с ip", "blocked", "qrator", "too many requests",
    )
    if (urlsplit(url).path.startswith(("/blocked", "/captcha"))
            or any(marker in title or marker in text or marker in raw for marker in challenge_markers)):
        raise FetchError("Авито ограничил доступ или запросил проверку безопасности. Ссылку можно сохранить, добавьте название и фото вручную")
    draft = parse_metadata(html, url)
    # The desktop app shell advertises Avito's touch icon as og:image.
    if draft.get("title") and draft["title"].strip().casefold() in {
        "авито", "авито — объявления на сайте авито", "авито - объявления на сайте авито",
    }:
        draft = {}
    merge_product(draft, embedded_product(html, url))
    heading = soup.select_one('[data-marker="item-view/title-info"], h1[itemprop="name"]')
    if heading and heading.get_text(" ", strip=True):
        draft["title"] = heading.get_text(" ", strip=True)[:200]
    # Listing-level microdata, not prices on recommendation cards.
    price = soup.select_one('[data-marker="item-view/item-price"] [itemprop="price"], '
                            '[data-marker="item-view/item-price"][itemprop="price"]')
    currency = soup.select_one('[data-marker="item-view/item-price"] [itemprop="priceCurrency"]')
    if price and currency and draft.get("price") is None:
        amount = parse_price(price.get("content"))
        code = currency.get("content", "")
        if amount is not None and code in {"RUB", "USD", "EUR"}:
            draft.update(price=amount, currency=code)
    images = []
    for image in draft.get("image_urls", []):
        absolute = urljoin(url, image)
        parts = urlsplit(absolute)
        if (parts.scheme in {"http", "https"}
                and not parts.path.startswith(("/icons/", "/s/app/logo/"))):
            images.append(absolute)
    draft["image_urls"] = images
    draft["image_url"] = images[0] if images else None
    if not draft.get("title") and not images:
        raise FetchError("Авито не предоставил данные объявления. Ссылку можно сохранить, а фото добавить вручную")
    return draft
