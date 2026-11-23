"""Best-effort public product data; no cookies, browser or protection bypass."""

import json
import re
from decimal import Decimal
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .network import FetchError
from .parser import clean_text, parse_price

# Host aliases are explicit: no arbitrary subdomain supplied by a page.
DOMAINS = {
    "wildberries.ru": "wildberries", "wb.ru": "wildberries",
    "wildberries.by": "wildberries", "wildberries.kz": "wildberries",
    "ozon.ru": "ozon", "ozon.by": "ozon", "ozon.kz": "ozon",
    "lamoda.ru": "lamoda", "lamoda.kz": "lamoda", "lamoda.by": "lamoda",
    "market.yandex.ru": "yandex", "market.yandex.com": "yandex",
    "market.yandex.by": "yandex", "market.yandex.kz": "yandex",
    "megamarket.ru": "megamarket", "sbermegamarket.ru": "megamarket",
    "aliexpress.ru": "aliexpress", "aliexpress.com": "aliexpress", "ru.aliexpress.com": "aliexpress",
    "avito.ru": "avito",
    "goldapple.ru": "goldapple",
    "dns-shop.ru": "dns", "mvideo.ru": "mvideo", "eldorado.ru": "eldorado",
    "citilink.ru": "citilink", "joom.com": "joom",
}

SITE_LABELS = {
    "wildberries": "Wildberries", "ozon": "Ozon", "lamoda": "Lamoda",
    "yandex": "Яндекс Маркет", "megamarket": "Мегамаркет",
    "aliexpress": "AliExpress", "avito": "Авито", "goldapple": "Золотое яблоко",
    "dns": "DNS", "mvideo": "М.Видео", "eldorado": "Эльдорадо",
    "citilink": "Ситилинк", "joom": "Joom",
}

# Prices on these sites are quoted in roubles. Other sites must state the currency.
SITE_CURRENCY = {
    "wildberries": "RUB", "ozon": "RUB", "lamoda": "RUB",
    "yandex": "RUB", "megamarket": "RUB", "avito": "RUB", "goldapple": "RUB",
    "dns": "RUB", "mvideo": "RUB", "eldorado": "RUB", "citilink": "RUB", "joom": "RUB",
}

PATTERNS = {
    "wildberries": r"/catalog/(?P<id>\d+)(?:/.*)?",
    "lamoda": r"/p/(?P<id>[A-Za-z0-9]+)(?:/.*)?",
    "ozon": r"/(?:product/(?:[^/]*-)?(?P<id>\d+)|context/detail/id/(?P<legacy_id>\d+))(?:/.*)?",
    "yandex": r"/(?:product--[^/]*|product)/(?P<id>\d+)(?:/.*)?",
    "megamarket": r"/catalog/details/(?:[^/]*-)?(?P<id>\d+)(?:/.*)?",
    "aliexpress": r"/item/(?P<id>\d+)\.html(?:/.*)?",
    "avito": r"/(?:[^/]+/)*[^/]*_(?P<id>\d+)(?:/.*)?",
    "goldapple": r"/(?:product/)?(?P<id>\d{6,})(?:-[^/]*)?(?:/.*)?",
    "dns": r"/product/(?P<id>\d+)(?:/.*)?",
    "mvideo": r"/products/(?:[^/]*-)?(?P<id>\d+)(?:/.*)?",
    "eldorado": r"/cat/detail/(?P<id>\d+)(?:/.*)?",
    "citilink": r"/product/(?:[^/]*-)?(?P<id>\d+)(?:/.*)?",
    "joom": r"/products/(?P<id>[A-Za-z0-9_-]+)(?:/.*)?",
}

TITLE_KEYS = (
    "name", "title", "imt_name", "productName", "displayName", "goodsName",
    "shortName", "subject", "product_name", "item_name", "offer_name", "modelName",
)
IMAGE_KEYS = (
    "image", "images", "pictures", "photos", "media", "gallery", "image_url", "imageUrl",
    "imageURL", "imagePathList", "imagePath", "pic", "pics", "preview", "cover", "coverImage",
    "mainImage", "main_image", "photo", "photoUrl", "thumb", "thumbnail",
)
ID_KEYS = (
    "id", "sku", "skuId", "productId", "product_id", "productID", "nmId", "nm_id",
    "article", "itemId", "item_id", "itemID", "offerId", "offer_id", "offerID",
    "goodsId", "goods_id", "goodsID", "productCode", "product_code", "vendorCode", "vendor_code",
)

CURRENCY_NUMBERS = {
    "643": "RUB", "810": "RUB", "840": "USD", "978": "EUR", "398": "KZT", "933": "BYN",
    "980": "UAH", "985": "PLN", "826": "GBP", "392": "JPY", "156": "CNY", "356": "INR",
    "702": "SGD", "344": "HKD", "410": "KRW", "032": "ARS", "076": "BRL", "484": "MXN",
}
CURRENCY_SYMBOLS = {"₽": "RUB", "€": "EUR", "$": "USD", "₸": "KZT", "₴": "UAH", "£": "GBP"}

# A successful HTTP response can still be a device check, not a product page.
CHALLENGE_MARKERS = {
    "ozon": ("доступ ограничен", "проблема с ip", "отключите vpn"),
    "wildberries": ("доступ ограничен", "проверьте, что вы не робот", "ой! что-то пошло не так"),
    "lamoda": (
        "checking device", "проверка устройства", "доступ ограничен",
        "js-challenge-loader", "id_captcha_frame_div", "servicepipe", "exhkqyad",
    ),
    "megamarket": (
        "проверка устройства", "доступ ограничен", "checking device",
        "js-challenge-loader", "id_captcha_frame_div", "servicepipe",
    ),
    "goldapple": (
        "checking device", "проверка устройства", "доступ ограничен",
        "js-challenge-loader", "id_captcha_frame_div", "servicepipe",
    ),
    "aliexpress": ("проверка безопасности", "punish", "captcha", "slide to verify"),
    "yandex": ("подтвердите, что вы не робот", "вы не робот", "smartcaptcha"),
    "dns": ("доступ ограничен", "captcha", "проверка браузера"),
    "mvideo": ("доступ ограничен", "captcha", "проверка браузера"),
    "eldorado": ("доступ ограничен", "captcha", "проверка браузера"),
    "citilink": ("доступ ограничен", "captcha", "проверка браузера"),
    "joom": ("доступ ограничен", "captcha", "проверка браузера"),
    "avito": ("доступ ограничен", "captcha", "проверка браузера", "подтвердите",
              "проблемы с ip", "blocked", "qrator"),

}

_STATE_NAMES = (
    r"__NUXT__|__APOLLO_STATE__|__INITIAL_STATE__|__PRELOADED_STATE__|"
    r"__NEXT_DATA__|__INITIAL_DATA__|__INITIAL_PROPS__|__STATE__|__DATA__|"
    r"__REDUX_STATE__|__STORE__|__APP_STATE__|__PRODUCT__|__NUXT_DATA__|"
    r"runParams|productData"
)
STATE_ASSIGNMENT = re.compile(
    r"(?:(?:window|self|globalThis)\s*\.\s*|(?:var|let|const)\s+)?"
    rf"(?P<name>{_STATE_NAMES})\s*=\s*(?=[\{{\[])"
)
STATE_BRACKET = re.compile(
    r"(?:window|self|globalThis)\s*\[\s*['\"]"
    rf"(?P<name>{_STATE_NAMES})['\"]\s*\]\s*=\s*(?=[\{{\[])"
)


def site_of(url):
    parts = urlsplit(url)
    if parts.username or parts.password or parts.scheme not in {"http", "https"}:
        return None
    host = (parts.hostname or "").lower()
    host = host.removeprefix("www.").removeprefix("m.")
    return DOMAINS.get(host)


def product_ref(url):
    parts = urlsplit(url)
    site = site_of(url)
    if not site:
        return None
    match = re.fullmatch(PATTERNS.get(site, r"(?!)"), parts.path, re.I)
    if not match:
        return None
    identifier = match.groupdict().get("id") or match.groupdict().get("legacy_id")
    return (site, identifier) if identifier else None


def currency_code(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        value = str(int(value))
    if not isinstance(value, str):
        return None
    value = value.strip()
    if value in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[value]
    if value in CURRENCY_NUMBERS:
        return CURRENCY_NUMBERS[value]
    lowered = value.casefold().rstrip(".")
    if lowered in {"руб", "рубль", "рубля", "рублей", "р", "rur"}:
        return "RUB"
    if re.fullmatch(r"[A-Za-z]{3}", value):
        return value.upper()
    return None


def _number(text):
    """Parse a human-formatted amount such as `1 234,50` without guessing units."""
    text = re.sub(r"[ \u00a0\u202f\u2009]", "", text)
    text = re.sub(r"[^\d.,]", "", text)
    if not text:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        head, _, tail = text.rpartition(",")
        text = text.replace(",", ".") if len(tail) <= 2 else head + tail
    return parse_price(text)


def money(value, hint=None):
    """Return `(amount, currency)`; a bare number is accepted only with a currency hint."""
    if isinstance(value, dict):
        hint = currency_code(
            value.get("currency") or value.get("currencyId") or value.get("priceCurrency")
            or value.get("currencyCode")
        ) or hint
        for key in ("value", "amount", "total", "price", "current", "final", "sale", "min"):
            if key in value:
                value = value[key]
                break
        else:
            return None, None
    if isinstance(value, bool) or value is None:
        return None, None
    if isinstance(value, (int, float, Decimal)):
        return parse_price(value), hint
    if isinstance(value, str):
        amount = parse_price(value)
        if amount is not None:
            return amount, hint
        normalized = value.replace("\u00a0", " ").replace("\u202f", " ")
        # A range is not an exact price: do not pick one endpoint silently.
        if re.search(r"\d\s*(?:[-\u2013\u2014]|\.\.)\s*\d", normalized) or re.search(
            r"\b\u043e\u0442\b.*\b\u0434\u043e\b", normalized, re.I
        ):
            return None, None
        match = re.search(
            r"(\d[\d\s.,]*)\s*(\u20bd|\u0440\u0443\u0431(?:\.|\u043b\u044f|\u043b\u0435\u0439)?|\u0440\.|RUB|RUR|USD|EUR|\u20b8|\u20b4|\xa3|\u20ac|\$)",
            normalized, re.I,
        )
        if match:
            return _number(match[1]), currency_code(match[2]) or hint
        if hint:
            amount = _number(normalized)
            if amount is not None:
                return amount, hint
    return None, None

def gallery(value, depth=0):
    if depth > 8:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [url for item in value for url in gallery(item, depth + 1)]
    if isinstance(value, dict):
        keys = (
            "src", "url", "contentUrl", "thumbnailUrl", "path", "preview", "original",
            "image", "image_url", "imageUrl", "big", "large", "medium", "small",
        )
        return [url for key in keys if key in value for url in gallery(value[key], depth + 1)]
    return []


def product_price(value, depth=0, default_hint=None):
    hint = currency_code(
        value.get("priceCurrency") or value.get("currency") or value.get("currencyId")
        or value.get("currencyCode")
    ) or default_hint
    for key in (
        "price", "salePrice", "finalPrice", "currentPrice", "priceValue", "minPrice",
        "price_with_discount", "priceWithDiscount", "discountPrice", "discountedPrice",
        "min_price", "minPriceValue",
    ):
        if key not in value:
            continue
        price, code = money(value[key], hint)
        if price is not None:
            return price, code or hint
    # Wildberries encodes amounts in kopecks in these fields.
    for key in ("salePriceU", "priceU"):
        if key in value:
            price, _ = money(value[key], "RUB")
            if price is not None:
                return format(Decimal(price) / 100, ".2f"), "RUB"
    if depth < 2:
        offers = value.get("offers")
        if isinstance(offers, dict):
            price, currency = product_price(offers, depth + 1, default_hint=hint)
            if price is not None:
                return price, currency
        elif isinstance(offers, list) and len(offers) == 1 and isinstance(offers[0], dict):
            price, currency = product_price(offers[0], depth + 1, default_hint=hint)
            if price is not None:
                return price, currency
    return None, None


def product_data(value, default_currency=None):
    title = clean_text(value.get("name")) or clean_text(value.get("title"))
    for key in TITLE_KEYS:
        if title:
            break
        title = clean_text(value.get(key))
    images = []
    for key in IMAGE_KEYS:
        images.extend(gallery(value.get(key)))
    images = [url for url in dict.fromkeys(images) if isinstance(url, str) and url.strip()]
    result = {"title": title[:200] if title else None, "image_urls": images,
              "image_url": images[0] if images else None}
    price, currency = product_price(value, default_hint=default_currency)
    if price is not None and currency:
        result.update(price=price, currency=currency)
    return result


def _balanced(text, start):
    """Return the balanced object/array beginning at `start`, ignoring strings."""
    pairs = {"{": "}", "[": "]"}
    stack = []
    quote = None
    index, length = start, len(text)
    while index < length:
        char = text[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in "\"'`":
            quote = char
            index += 1
            continue
        if char == "/" and index + 1 < length and text[index + 1] == "/":
            end = text.find("\n", index + 2)
            index = length if end < 0 else end + 1
            continue
        if char == "/" and index + 1 < length and text[index + 1] == "*":
            end = text.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        if char in pairs:
            stack.append(pairs[char])
        elif char in "}]":
            if not stack or stack.pop() != char:
                return None
            if not stack:
                return text[start:index + 1]
        index += 1
    return None


def _loose_json(text):
    """Best-effort JSON5-like parsing for Nuxt/Apollo objects; never executes JS."""
    out = []
    index, length = 0, len(text)
    quote = None
    stack = []
    expect_key = False
    while index < length:
        char = text[index]
        if quote:
            if char == "\\":
                if index + 1 >= length:
                    return None
                following = text[index + 1]
                if following == quote and quote == "'":
                    out.append("'")
                elif following == "'" and quote == '"':
                    out.append("'")
                else:
                    out.append(char)
                    out.append(following)
                index += 2
                continue
            if char == quote:
                out.append('"')
                quote = None
            elif char == '"' and quote == "'":
                out.append('\\"')
            else:
                out.append(char)
            index += 1
            continue
        if char in "\"'":
            quote = char
            out.append('"')
            index += 1
            continue
        if char == "`":
            return None
        if char == "/" and index + 1 < length and text[index + 1] == "/":
            end = text.find("\n", index + 2)
            index = length if end < 0 else end + 1
            continue
        if char == "/" and index + 1 < length and text[index + 1] == "*":
            end = text.find("*/", index + 2)
            index = length if end < 0 else end + 2
            continue
        if char == "{":
            stack.append("}")
            expect_key = True
            out.append(char)
        elif char == "[":
            stack.append("]")
            expect_key = False
            out.append(char)
        elif char in "}]":
            if not stack or stack.pop() != char:
                return None
            expect_key = False
            out.append(char)
        elif char == ",":
            expect_key = bool(stack and stack[-1] == "}")
            out.append(char)
        elif char == ":":
            expect_key = False
            out.append(char)
        elif expect_key and (char.isalpha() or char in "_$"):
            end = index
            while end < length and (text[end].isalnum() or text[end] in "_$"):
                end += 1
            after = end
            while after < length and text[after].isspace():
                after += 1
            if after < length and text[after] == ":":
                out.append(json.dumps(text[index:end]))
                index = end
                continue
            out.append("null")
            index = end
            continue
        elif expect_key and char.isdigit():
            end = index
            while end < length and text[end].isdigit():
                end += 1
            after = end
            while after < length and text[after].isspace():
                after += 1
            if after < length and text[after] == ":":
                out.append(json.dumps(text[index:end]))
                index = end
                continue
            out.append(text[index:end])
            index = end
            continue
        elif char.isalpha() or char in "_$":
            end = index
            while end < length and (text[end].isalnum() or text[end] in "_$"):
                end += 1
            word = text[index:end]
            if word in {"true", "false", "null"}:
                out.append(word)
            else:
                out.append("null")
            index = end
            continue
        else:
            out.append(char)
        index += 1
    if quote or stack:
        return None
    cleaned = re.sub(r",\s*([}\]])", r"\1", "".join(out))
    try:
        return json.loads(cleaned)
    except (ValueError, RecursionError):
        return None


def _parse_json(raw):
    raw = raw.lstrip("\ufeff").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, RecursionError):
        return _loose_json(raw)


def _json_blobs(soup):
    """Yield JSON text from scripts and common state assignments."""
    for script in soup.find_all("script"):
        content = script.string or script.get_text()
        if not content or len(content) > 4_000_000:
            continue
        kind = script.get("type", "").split(";")[0].strip().lower()
        if kind in {"application/json", "application/ld+json", "text/json"} or kind.endswith("+json"):
            yield content
            continue
        if kind not in {"", "text/javascript", "application/javascript", "module"}:
            continue
        for pattern in (STATE_ASSIGNMENT, STATE_BRACKET):
            for match in pattern.finditer(content):
                start = match.end()
                if start >= len(content) or content[start] not in "[{":
                    continue
                blob = _balanced(content, start)
                if blob:
                    yield blob


def _identity(value, identifier):
    expected = identifier.casefold()
    for key in ID_KEYS:
        item = value.get(key)
        if item is not None and str(item).strip().casefold() == expected:
            return True
    # Apollo normalizes objects under keys such as `Product:12345`.
    for key in value:
        if isinstance(key, str) and key.rsplit(":", 1)[-1].strip().casefold() == expected:
            return True
    return False


def _matching_objects(value, identifier, limit=200_000):
    """Find objects with the exact product ID; never guess a recommendation."""
    matches = []
    stack = [(value, 0)]
    seen = 0
    while stack and seen < limit:
        node, depth = stack.pop()
        seen += 1
        if depth > 24:
            continue
        if isinstance(node, dict):
            if _identity(node, identifier):
                matches.append(node)
            stack.extend((item, depth + 1) for item in node.values())
        elif isinstance(node, list):
            stack.extend((item, depth + 1) for item in node)
    return matches


def _merge_matches(drafts):
    """Merge copies of the same product; conflicting fields are dropped, not guessed."""
    drafts = [
        draft for draft in drafts
        if draft.get("title") or draft.get("image_urls") or draft.get("price") is not None
    ]
    if not drafts:
        return {}

    def agreed(key, normalize=lambda value: value):
        values = [normalize(draft[key]) for draft in drafts if draft.get(key) is not None]
        return values[0] if values and all(value == values[0] for value in values) else None

    result = {"title": agreed("title")}
    images = agreed("image_urls", lambda value: tuple(value))
    if images:
        result["image_urls"] = list(images)
        result["image_url"] = images[0]
    price = agreed("price")
    currency = agreed("currency")
    if price is not None and currency:
        result.update(price=price, currency=currency)
    return {key: value for key, value in result.items() if value is not None}


def embedded_product(html, url):
    """Only exact-ID products in JSON state, never a guessed recommendation."""
    ref = product_ref(url)
    if not ref:
        return {}
    site, identifier = ref
    soup = BeautifulSoup(html, "html.parser")
    matches = []
    for raw in _json_blobs(soup):
        payload = _parse_json(raw)
        if payload is None:
            continue
        matches.extend(_matching_objects(payload, identifier))
    drafts = []
    for match in matches:
        draft = product_data(match, default_currency=SITE_CURRENCY.get(site))
        if draft.get("title"):
            draft["title"] = marketplace_title(draft["title"], site)
        drafts.append(draft)
    return _merge_matches(drafts)


def aliexpress_product(html, url=None):
    """AliExpress keeps the item page payload in `window.runParams`."""
    if url is not None:
        ref = product_ref(url)
        if not ref or ref[0] != "aliexpress":
            return {}
    soup = BeautifulSoup(html, "html.parser")
    for raw in _json_blobs(soup):
        payload = _parse_json(raw)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            continue
        title = None
        module = data.get("titleModule")
        if isinstance(module, dict):
            title = (
                clean_text(module.get("subject"))
                or clean_text(module.get("title"))
                or clean_text(module.get("name"))
            )
        if not title:
            title = clean_text(data.get("subject")) or clean_text(data.get("title"))
        images = []
        for key in ("imageModule", "imageModuleV2"):
            module = data.get(key)
            if not isinstance(module, dict):
                continue
            for field in ("imagePathList", "imagePath", "summImagePathList", "imgList", "images"):
                images.extend(gallery(module.get(field)))
        images = [
            "https:" + value if value.startswith("//") else value
            for value in dict.fromkeys(url for url in images if isinstance(url, str) and url.strip())
        ]
        prices = data.get("priceModule") if isinstance(data.get("priceModule"), dict) else {}
        price, currency = None, None
        for key in (
            "minActivityAmount", "activityAmount", "minAmount", "maxAmount",
            "minPrice", "price",
        ):
            if key in prices:
                price, currency = money(prices[key])
                if price is not None and currency:
                    break
        if not (price is not None and currency):
            for key in ("formatedActivityPrice", "formatedPrice", "priceText"):
                if key in prices:
                    price, currency = money(prices[key])
                    if price is not None and currency:
                        break
        if price is not None and not currency and url:
            host = (urlsplit(url).hostname or "").lower()
            if host.endswith(".ru"):
                currency = "RUB"
        result = {
            "title": title[:200] if title else None,
            "image_urls": images,
            "image_url": images[0] if images else None,
            "price": price,
            "currency": currency,
        }
        if result["title"]:
            result["title"] = marketplace_title(result["title"], "aliexpress")
        if result["title"] or result["image_urls"] or result["price"] is not None:
            return {key: value for key, value in result.items() if value not in (None, [])}
    return {}


def _widget_json(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw[:1] in "[{":
        try:
            value = json.loads(raw)
        except (ValueError, RecursionError):
            return None
        return value if isinstance(value, dict) else None
    return None


def ozon_product(url, fetch, max_bytes):
    """Ozon's page composer is public; a block or challenge simply yields nothing."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host not in {
        "ozon.ru", "www.ozon.ru", "m.ozon.ru",
        "ozon.by", "www.ozon.by", "m.ozon.by",
        "ozon.kz", "www.ozon.kz", "m.ozon.kz",
    }:
        return {}
    ref = product_ref(url)
    if not ref or ref[0] != "ozon" or not parts.path.startswith(("/product/", "/context/detail/id/")):
        return {}
    api_host = host.removeprefix("m.")
    if not api_host.startswith("www."):
        api_host = "www." + api_host
    endpoint = (
        f"https://{api_host}/api/composer-api.bx/page/json/v2?"
        + urlencode({"url": parts.path})
    )
    try:
        body, kind, _ = fetch(endpoint, max_bytes)
        if kind.split(";")[0].strip().lower() != "application/json":
            return {}
        payload = json.loads(body)
    except (FetchError, ValueError, RecursionError):
        return {}
    states = payload.get("widgetStates") if isinstance(payload, dict) else None
    if not isinstance(states, dict):
        page = payload.get("page") if isinstance(payload, dict) else None
        states = page.get("widgetStates") if isinstance(page, dict) else None
    if not isinstance(states, dict):
        return {}
    title, images, price, currency = None, [], None, None
    for key, raw in states.items():
        name = key.split("-", 1)[0]
        value = _widget_json(raw)
        if value is None:
            continue
        if name == "webProductHeading" and not title:
            title = (
                clean_text(value.get("title"))
                or clean_text(value.get("text"))
                or clean_text(value.get("name"))
            )
        elif name in {"webGallery", "webGalleryDesktop"} and not images:
            for field in ("images", "photos", "coverImage", "images360"):
                images.extend(gallery(value.get(field)))
        elif name in {"webPrice", "webSale", "webPriceV2"} and price is None:
            for field in ("price", "cardPrice", "originalPrice", "priceText"):
                found, code = money(value.get(field), SITE_CURRENCY["ozon"])
                if found is not None:
                    price, currency = found, code or SITE_CURRENCY["ozon"]
                    break
    images = [
        "https:" + value if value.startswith("//") else value
        for value in dict.fromkeys(url for url in images if isinstance(url, str) and url.strip())
    ]
    result = {"title": title[:200] if title else None, "image_urls": images,
              "image_url": images[0] if images else None}
    if title:
        result["title"] = marketplace_title(result["title"], "ozon")
    if price is not None:
        result.update(price=price, currency=currency)
    return {key: value for key, value in result.items() if value not in (None, [])}


def _kopeck_price(value, current):
    price, _ = money(value, "RUB")
    return format(Decimal(price) / 100, ".2f") if price is not None else current


def wildberries_price(product):
    amounts = set()
    for size in product.get("sizes") or []:
        if not isinstance(size, dict) or not isinstance(size.get("price"), dict):
            continue
        value = size["price"].get("total", size["price"].get("product"))
        if value is not None:
            amounts.add(str(value))
    # Different sizes mean different prices: do not silently choose one variant.
    if len(amounts) == 1:
        return _kopeck_price(amounts.pop(), None), "RUB"
    if not amounts:
        for key in ("salePriceU", "priceU"):
            if product.get(key) is not None:
                return _kopeck_price(product[key], None), "RUB"
    return None, None


def wildberries_product(identifier, fetch, max_bytes):
    result = {}
    endpoint = (
        f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&nm={identifier}"
    )
    try:
        body, kind, _ = fetch(endpoint, max_bytes)
        if kind.split(";")[0].strip().lower() == "application/json":
            payload = json.loads(body)
            data = payload.get("data", payload) if isinstance(payload, dict) else {}
            products = data.get("products") if isinstance(data, dict) else None
            products = [item for item in products or []
                        if isinstance(item, dict) and str(item.get("id")) == identifier]
            if len(products) == 1:
                title = clean_text(products[0].get("name"))
                if title:
                    result["title"] = title[:200]
                price, currency = wildberries_price(products[0])
                if price is not None:
                    result.update(price=price, currency=currency)
    except (FetchError, ValueError, RecursionError):
        pass
    basket = wildberries_basket(identifier, fetch, max_bytes)
    result = merge_product(result, basket)
    if result.get("title"):
        result["title"] = marketplace_title(result["title"], "wildberries")
    if not (result.get("title") or result.get("price") is not None or result.get("image_urls")):
        return {}
    return result


def wildberries_basket(identifier, fetch, max_bytes):
    """Bounded CDN discovery; an exact nm_id match is mandatory before using a photo.

    Newer CDN shards roughly follow catalog volumes. This is only a search hint,
    not an authoritative mapping: missing/moved products simply yield no image.
    """
    number = int(identifier)
    if number <= 0 or number > 10**12:
        return {}
    volume, part = number // 100000, number // 1000
    guess = volume // 270 + 2
    for shard in dict.fromkeys(max(1, guess + offset) for offset in (0, -1, 1, -2)):
        if shard > 100:
            continue
        root = f"https://basket-{shard:02d}.wbbasket.ru/vol{volume}/part{part}/{number}"
        try:
            body, kind, _ = fetch(f"{root}/info/ru/card.json", max_bytes)
            if kind.split(";")[0].strip().lower() != "application/json":
                continue
            card = json.loads(body)
            if not isinstance(card, dict) or str(card.get("nm_id")) != identifier:
                continue
            title = clean_text(card.get("imt_name"))
            image = f"{root}/images/big/1.webp"
            result = {"title": title[:200] if title else None, "image_url": image, "image_urls": [image]}
            price, currency = wildberries_price(card)
            if price is not None:
                result.update(price=price, currency=currency)
            return result
        except (FetchError, ValueError, RecursionError):
            continue
    return {}


def _api_product(payload, identifier, site):
    """Use an exact ID when present; a deterministic endpoint may return no ID at all."""
    matches = _matching_objects(payload, identifier, limit=50_000)
    if not matches:
        candidates = []
        stack = [(payload, 0)]
        seen = 0
        while stack and seen < 50_000:
            node, depth = stack.pop()
            seen += 1
            if depth > 24:
                continue
            if isinstance(node, dict):
                if (
                    not any(key in node for key in ID_KEYS)
                    and any(key in node for key in TITLE_KEYS)
                    and any(key in node for key in ("price", "salePrice", "finalPrice",
                                                    "images", "image", "pictures", "photos"))
                ):
                    candidates.append(node)
                stack.extend((item, depth + 1) for item in node.values())
            elif isinstance(node, list):
                stack.extend((item, depth + 1) for item in node)
        if len(candidates) == 1:
            matches = candidates
    default_currency = SITE_CURRENCY.get(site)
    draft = _merge_matches([product_data(match, default_currency=default_currency) for match in matches])
    if draft.get("title"):
        draft["title"] = marketplace_title(draft["title"], site)
    return draft


def lamoda_product(identifier, fetch, max_bytes):
    """Lamoda's public catalog endpoint; tolerate both flat and `data` responses."""
    endpoint = f"https://api.lamoda.ru/catalog/products/{quote(identifier)}/"
    try:
        body, kind, _ = fetch(endpoint, max_bytes)
        if kind.split(";")[0].strip().lower() != "application/json":
            return {}
        payload = json.loads(body)
    except (FetchError, ValueError, RecursionError):
        return {}
    if isinstance(payload, dict) and (payload.get("error") or payload.get("code") not in {None, 0, 200}):
        return {}
    return _api_product(payload, identifier, "lamoda")


def megamarket_product(identifier, fetch, max_bytes):
    """Megamarket's mobile catalog is public, but may answer with an IP/VPN error."""
    for endpoint in (
        f"https://megamarket.ru/api/mobile/v1/catalogService/product/{quote(identifier)}",
        f"https://megamarket.ru/api/mobile/v1/catalogService/product/{quote(identifier)}/detail",
    ):
        try:
            body, kind, _ = fetch(endpoint, max_bytes)
            if kind.split(";")[0].strip().lower() != "application/json":
                continue
            payload = json.loads(body)
        except (FetchError, ValueError, RecursionError):
            continue
        if not isinstance(payload, (dict, list)):
            continue
        if isinstance(payload, dict) and (
            payload.get("error") or payload.get("code") not in {None, 0, 200}
        ):
            continue
        draft = _api_product(payload, identifier, "megamarket")
        if draft:
            return draft
    return {}


def public_product(url, fetch, max_bytes, html=None):
    """Public endpoints are optional: any of them may be unavailable or blocked."""
    ref = product_ref(url)
    if not ref:
        return {}
    site, identifier = ref
    if site == "wildberries":
        return wildberries_product(identifier, fetch, max_bytes)
    if site == "ozon":
        return ozon_product(url, fetch, max_bytes)
    if site == "lamoda":
        return lamoda_product(identifier, fetch, max_bytes)
    if site == "megamarket":
        return megamarket_product(identifier, fetch, max_bytes)
    if site == "aliexpress" and html is not None:
        return aliexpress_product(html, url)
    return {}


def state_product(html, url):
    """Combine embedded state with site-specific page payloads."""
    draft = embedded_product(html, url)
    if site_of(url) == "aliexpress":
        merge_product(draft, aliexpress_product(html, url))
    return draft


def merge_product(draft, extra):
    if not extra.get("image_urls") and extra.get("image_url"):
        extra = {**extra, "image_urls": [extra["image_url"]]}
    if not draft.get("image_urls") and draft.get("image_url"):
        draft["image_urls"] = [draft["image_url"]]
    if not draft.get("title") and extra.get("title"):
        draft["title"] = extra["title"]
    if draft.get("price") is None and extra.get("price") is not None:
        draft["price"], draft["currency"] = extra["price"], extra.get("currency")
    images = list(dict.fromkeys(
        list(draft.get("image_urls") or []) + list(extra.get("image_urls") or [])
    ))
    draft["image_urls"] = images
    draft["image_url"] = images[0] if images else None
    return draft


def marketplace_title(title, site):
    """Drop SEO suffixes such as `купить по низкой цене на OZON`."""
    if not title or site not in SITE_LABELS:
        return title
    text = re.sub(r"\s+", " ", title).strip()
    for pattern in (
        r"\s*[|\-–—]\s*(?:купить|заказать|цена|стоимость|отзывы|характеристики|"
        r"описание|доставка|официальный\s+сайт|интернет-магазин)\b.*$",
        r"\s+купить\b.*$",
        r",\s*(?:цена|стоимость)\b.*$",
        r"\s*[|\-–—]\s*(?:маркетплейс\s+)?(?:мегамаркет|ozon|wildberries|lamoda|aliexpress|"
        r"яндекс\s*маркет|золотое\s+яблоко|gold\s*apple|dns|м\.?\s*видео|эльдорадо|ситилинк|joom)\s*$",
        r"\s+(?:на|в)\s+(?:ozon|wildberries|lamoda|megamarket|aliexpress|яндекс\s*маркет(?:е)?|"
        r"золот(?:ом|ое)\s+яблок(?:е|о)|gold\s*apple|dns|м\.?\s*видео|эльдорадо|ситилинк|joom)\b.*$",
    ):
        text = re.sub(pattern, "", text, flags=re.I).strip()
    text = text.strip(" -–—|,")
    return text if len(text) >= 3 else title


def prefer_large_image(url, site=None):
    """Ask known CDNs for a larger copy when the markup mentioned a thumbnail."""
    parts = urlsplit(url)
    path = parts.path
    if site == "ozon":
        path = re.sub(r"/wc\d+/", "/wc1000/", path)
    elif site == "wildberries":
        path = re.sub(r"/images/(?:small|medium|c\d+x\d+)/", "/images/big/", path)
    elif site == "aliexpress":
        path = re.sub(r"_\d+x\d+(?=\.[A-Za-z]+$)", "", path)
    if path == parts.path:
        return url
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def reject_marketplace_challenge(html, url):
    site = site_of(url)
    markers = CHALLENGE_MARKERS.get(site) if site else None
    if not markers:
        return
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(" ", strip=True) if soup.title else "").casefold()
    text = soup.get_text(" ", strip=True)[:4000].casefold()
    raw = html[:50_000].decode("utf-8", "ignore").casefold()
    path = (urlsplit(url).path or "").casefold()
    if (
        any(marker in title or marker in text or marker in raw for marker in markers)
        or any(part in path for part in ("/captcha", "/blocked", "/challenge"))
    ):
        raise FetchError(
            f"{SITE_LABELS[site]} запросил проверку безопасности. "
            "Название, цена и фото недоступны"
        )


def reject_yandex_challenge(html, url):
    """A successful HTTP response can still be a CAPTCHA, not a product/event."""
    parts = urlsplit(url)
    if parts.hostname not in {
        "market.yandex.ru", "market.yandex.com", "market.yandex.by", "market.yandex.kz",
        "afisha.yandex.ru",
    }:
        return
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True).casefold() if soup.title else ""
    if (parts.path.startswith(("/showcaptcha", "/checkcaptcha", "/captcha"))
            or "подтвердите, что" in title or "captcha" in title or "вы не робот" in title
            or soup.select_one('form[action*="checkcaptcha"]')):
        raise FetchError("Яндекс запросил проверку безопасности. Название и фото недоступны")
