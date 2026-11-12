import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


def meta_tags(soup: BeautifulSoup) -> dict:
    tags = {}
    for tag in soup.find_all("meta"):
        key = tag.get("property") or tag.get("name")
        value = tag.get("content")
        if isinstance(key, str) and isinstance(value, str) and value.strip():
            tags.setdefault(key.strip().lower(), value.strip())
    return tags


def parse_logos(html: bytes, base_url: str) -> list[str]:
    """Explicit brand images, then touch icons/favicons; never an arbitrary image."""
    soup = BeautifulSoup(html, "html.parser")
    logos, icons = [], []

    def image_url(value):
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("contentUrl") or value.get("url")
        return None

    def visit(value, depth=0):
        if depth > 20:
            return
        if isinstance(value, list):
            for entry in value:
                visit(entry, depth + 1)
        elif isinstance(value, dict):
            if logo := image_url(value.get("logo")):
                logos.append(logo)
            for key in ("@graph", "publisher", "brand", "manufacturer"):
                if key in value:
                    visit(value[key], depth + 1)

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            visit(json.loads(script.string or script.get_text()))
        except (ValueError, RecursionError):
            continue
    for image in soup.select('img[src], img[data-src], [itemprop="logo"]'):
        marker = " ".join(str(image.get(key, "")) for key in ("id", "class", "alt", "itemprop"))
        if re.search(r"\blogo\b|логотип", marker, re.I):
            if logo := image.get("src") or image.get("data-src") or image.get("content"):
                logos.append(logo)
    for link in soup.find_all("link", href=True):
        rel = {value.lower() for value in link.get("rel", [])}
        if rel & {"apple-touch-icon", "apple-touch-icon-precomposed"}:
            icons.insert(0, link["href"])
        elif "icon" in rel:
            icons.append(link["href"])
    candidates = []
    for value in logos + icons:
        if not isinstance(value, str):
            continue
        try:
            url = urljoin(base_url, value.strip())
            parts = urlsplit(url)
        except ValueError:
            continue
        # SVG is not rasterized server-side: it may contain external references.
        if parts.scheme in {"http", "https"} and not parts.path.lower().endswith(".svg") and url not in candidates:
            candidates.append(url)
    return candidates[:4]


def parse_price(value) -> str | None:
    try:
        price = Decimal(str(value))
        if price.is_finite() and 0 <= price < Decimal("1000000000000") and price.as_tuple().exponent >= -2:
            return format(price, ".2f")
    except (ValueError, InvalidOperation, TypeError):
        pass
    return None


def parse_telegram_post(html: bytes, base_url: str, channel: str, message_id: str) -> dict:
    """Only the linked message: never a channel avatar or a neighbouring post."""
    soup = BeautifulSoup(html, "html.parser")
    result = dict(title=None, description=None, image_url=None, price=None, currency=None)
    message = next((
        tag for tag in soup.select(".tgme_widget_message[data-post]")
        if tag.get("data-post", "").casefold() == f"{channel}/{message_id}".casefold()
    ), None)
    # Some embed versions omit data-post; a channel feed must always match the ID.
    if message is None and not urlsplit(base_url).path.startswith("/s/"):
        if not soup.select(".tgme_widget_message[data-post]"):
            message = soup.select_one(".tgme_widget_message")
    if message is None:
        return result
    author = message.select_one(".tgme_widget_message_author, .tgme_widget_message_owner_name")
    if author:
        result["title"] = author.get_text(" ", strip=True)[:200] or None
    if not result["title"]:
        channel_name = soup.select_one(".tgme_channel_info_header_title")
        if channel_name:
            result["title"] = channel_name.get_text(" ", strip=True)[:200] or None
    photo = message.select_one(".tgme_widget_message_photo_wrap")
    if photo:
        match = re.search(r"background-image:\s*url\(\s*(['\"]?)(.*?)\1\s*\)", photo.get("style", ""))
        if match and match[2]:
            result["image_url"] = urljoin(base_url, match[2])
        else:
            image = photo.select_one("img[src]")
            if image:
                result["image_url"] = urljoin(base_url, image["src"])
    return result


def clean_text(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def schema_type(value, name):
    types = value if isinstance(value, list) else [value]
    return any(isinstance(kind, str) and kind.rstrip("/").rsplit("/", 1)[-1] == name for kind in types)


def same_page(value, base_url):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        target, base = urlsplit(urljoin(base_url, value)), urlsplit(base_url)
        return (target.scheme, target.netloc, target.path.rstrip("/"), target.query) == (
            base.scheme, base.netloc, base.path.rstrip("/"), base.query,
        )
    except ValueError:
        return False


def structured_product(soup, base_url):
    """Follow page entities and graph references, not related products or item lists."""
    nodes, primary = [], []

    def visit(value, depth=0):
        if depth > 20:
            return
        if isinstance(value, list):
            for entry in value:
                visit(entry, depth + 1)
        elif isinstance(value, dict):
            nodes.append(value)
            if schema_type(value.get("@type"), "WebPage") and (
                not value.get("url") or same_page(value["url"], base_url)
            ):
                entity = value.get("mainEntity", [])
                primary.extend(entity if isinstance(entity, list) else [entity])
            for key in ("@graph", "mainEntity", "image", "offers", "priceSpecification"):
                if key in value:
                    visit(value[key], depth + 1)

    for script in soup.find_all("script", type=lambda value: bool(
        value and value.split(";")[0].strip().lower() == "application/ld+json"
    )):
        try:
            visit(json.loads(script.string or script.get_text()))
        except (ValueError, RecursionError):
            continue
    references = {}
    for node in nodes:
        if isinstance(node.get("@id"), str):
            try:
                key = urljoin(base_url, node["@id"])
            except ValueError:
                continue
            references[key] = {**references.get(key, {}), **node}

    def resolve(value):
        if isinstance(value, dict) and isinstance(value.get("@id"), str):
            try:
                return {**references.get(urljoin(base_url, value["@id"]), {}), **value}
            except ValueError:
                pass
        return value

    products = []
    for node in nodes:
        node = resolve(node)
        if schema_type(node.get("@type"), "Product") and node not in products:
            products.append(node)
    main = [resolve(node) for node in primary]
    selected = [product for product in products if product in main]
    if not selected:
        selected = [product for product in products if same_page(product.get("url"), base_url)]
    if not selected:
        selected = [product for product in products if same_page(
            product.get("mainEntityOfPage", {}).get("@id") if isinstance(product.get("mainEntityOfPage"), dict)
            else product.get("mainEntityOfPage"), base_url,
        )]
    if not selected:
        selected = [product for product in products if same_page(product.get("@id"), base_url)]
    if not selected and len(products) == 1 and not products[0].get("url"):
        selected = products
    return (selected[0] if len(selected) == 1 else {}), bool(products and len(selected) != 1), resolve


def image_values(value, resolve=lambda value: value, depth=0):
    if depth > 10:
        return []
    value = resolve(value)
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [url for entry in value for url in image_values(entry, resolve, depth + 1)]
    if isinstance(value, dict):
        return [url for key in ("contentUrl", "url", "thumbnailUrl")
                for url in image_values(value.get(key), resolve, depth + 1)]
    return []


def element_value(tag):
    return tag.get("content") or tag.get("href") or tag.get_text(" ", strip=True)


def element_images(tag):
    images = []
    for key in ("data-srcset", "srcset"):
        # Prefer the largest declared version; retain smaller alternatives if it fails.
        candidates = []
        for entry in tag.get(key, "").split(","):
            parts = entry.split()
            if parts:
                size = re.fullmatch(r"(\d+(?:\.\d+)?)[wx]", parts[-1]) if len(parts) > 1 else None
                candidates.append((float(size[1]) if size else 0, parts[0]))
        images.extend(url for _, url in sorted(candidates, reverse=True))
    images.extend(tag.get(key) for key in ("data-src", "data-original", "data-lazy-src", "src", "content", "href"))
    return [value for value in images if isinstance(value, str) and value.strip()]


def microdata_product(soup, base_url):
    products = [tag for tag in soup.select("[itemscope][itemtype]")
                if schema_type(tag.get("itemtype", "").split(), "Product")]
    matching = [tag for tag in products if same_page(tag.get("itemid"), base_url)]
    selected = matching or products
    return selected[0] if len(selected) == 1 else None, bool(products and len(selected) != 1)


def product_properties(scope, name):
    if scope is None:
        return []
    # Do not borrow fields from a nested brand, review, or recommended product.
    return [tag for tag in scope.select(f'[itemprop~="{name}"]')
            if tag.find_parent(attrs={"itemscope": True}) is scope]


def price_pair(amount, currency):
    currency = clean_text(currency)
    price = parse_price(amount)
    if price is not None and currency and len(currency) == 3 and currency.isascii() and currency.isalpha():
        return price, currency.upper()
    return None, None


def parse_metadata(html: bytes, base_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    tags = meta_tags(soup)
    product, ambiguous, resolve = structured_product(soup, base_url)
    scope, micro_ambiguous = microdata_product(soup, base_url)
    # An ambiguous product collection is not a source of individual product fields.
    if ambiguous:
        scope = None
    # Separate markup blocks may describe a recommendation rather than this product.
    if scope is not None and product.get("name"):
        names = product_properties(scope, "name")
        if names and clean_text(element_value(names[0])) != clean_text(product["name"]):
            scope = None

    def properties(name):
        if scope is not None:
            return product_properties(scope, name)
        if ambiguous or micro_ambiguous:
            return []
        # Some pages declare item properties without a surrounding Product scope.
        return [tag for tag in soup.select(f'[itemprop~="{name}"]')
                if tag.find_parent(attrs={"itemscope": True}) is None]

    def prop(name):
        return next((value for tag in properties(name) if (value := clean_text(element_value(tag)))), None)

    main = soup.find("main") or soup
    headings = main.find_all("h1")
    heading = headings[0].get_text(" ", strip=True) if len(headings) == 1 else None
    result = {
        "title": clean_text(product.get("name")) or prop("name") or tags.get("product:title")
        or heading or tags.get("og:title") or tags.get("twitter:title")
        or (soup.title.get_text(strip=True) if soup.title else None),
        "description": clean_text(product.get("description")) or prop("description")
        or tags.get("og:description") or tags.get("twitter:description") or tags.get("description"),
        "price": None, "currency": None,
    }
    images = image_values(product.get("image"), resolve)
    for tag in properties("image"):
        images.extend(element_images(tag))
        for child in tag.select('[itemprop~="contentUrl"], [itemprop~="url"], img, source'):
            images.extend(element_images(child))
    # Only explicitly marked product galleries, never every image on the page.
    if not ambiguous and not micro_ambiguous:
        for tag in main.select(
            '[data-product-gallery] img, [data-product-gallery] source, .product-gallery img, '
            '.product-gallery source, .product__gallery img, #product-gallery img, '
            'img[data-product-image], img.product-image, img.product__image, img#landingImage'
        ):
            owner = next((parent for parent in tag.parents
                          if schema_type(str(parent.get("itemtype", "")).split(), "Product")), None)
            if owner is not None and owner is not scope:
                continue
            if any(re.search(r"recommend|related|upsell|cross-sell", " ".join([
                str(parent.get("class", "")), str(parent.get("id", "")),
            ]), re.I) for parent in tag.parents if parent is not main):
                continue
            images.extend(element_images(tag))
    for key in ("og:image:secure_url", "og:image", "og:image:url", "twitter:image", "twitter:image:src"):
        for tag in soup.find_all("meta"):
            if str(tag.get("property") or tag.get("name", "")).strip().lower() == key:
                images.extend(image_values(tag.get("content")))
    for link in soup.select('link[rel~="image_src"][href]'):
        images.append(link["href"])
    images.extend(image_values(product.get("thumbnailUrl"), resolve))

    offers = resolve(product.get("offers"))
    if isinstance(offers, dict):
        offers = [offers]
    ambiguous_offers = isinstance(offers, list) and len(offers) > 1
    if isinstance(offers, list) and len(offers) == 1:
        offer = resolve(offers[0])
        if isinstance(offer, dict):
            if offer.get("@type") is None or schema_type(offer.get("@type"), "Offer"):
                result["price"], result["currency"] = price_pair(offer.get("price"), offer.get("priceCurrency"))
                specification = resolve(offer.get("priceSpecification"))
                if not result["price"] and isinstance(specification, dict):
                    result["price"], result["currency"] = price_pair(
                        specification.get("price"), specification.get("priceCurrency") or offer.get("priceCurrency"),
                    )
            else:
                ambiguous_offers = True  # Aggregate/range prices are not an exact price.
    micro_offers = product_properties(scope, "offers")
    ambiguous_offers |= len(micro_offers) > 1
    if not result["price"] and not (ambiguous or micro_ambiguous or ambiguous_offers):
        price_scope = micro_offers[0] if len(micro_offers) == 1 else scope
        amounts = product_properties(price_scope, "price") if price_scope is not None else properties("price")
        currencies = product_properties(price_scope, "priceCurrency") if price_scope is not None else properties("priceCurrency")
        if len(amounts) == 1 and len(currencies) == 1:
            result["price"], result["currency"] = price_pair(element_value(amounts[0]), element_value(currencies[0]))
        if not result["price"]:
            result["price"], result["currency"] = price_pair(
                tags.get("product:price:amount") or tags.get("og:price:amount"),
                tags.get("product:price:currency") or tags.get("og:price:currency"),
            )

    if urlsplit(base_url).hostname == "t.me":
        message = soup.select_one(".tgme_widget_message_text")
        photo = soup.select_one(".tgme_widget_message_photo_wrap")
        if message and not result["title"]:
            result["title"] = message.get_text(" ", strip=True)
        if photo:
            match = re.search(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", photo.get("style", ""))
            if match:
                images.append(match[1])
    candidates = []
    for value in images:
        try:
            url = urljoin(base_url, value.strip())
            parts = urlsplit(url)
        except ValueError:
            continue
        if (parts.scheme in {"http", "https"} and parts.hostname and not parts.username and not parts.password
                and not parts.path.lower().endswith(".svg") and len(url) <= 4096 and url not in candidates):
            candidates.append(url)
        if len(candidates) >= 12:
            break
    result["image_urls"] = candidates
    result["image_url"] = candidates[0] if candidates else None
    result["title"] = result["title"][:200] if result["title"] else None
    result["description"] = result["description"][:5000] if result["description"] else None
    return result


def parse_instagram_post(html: bytes, base_url: str) -> dict:
    """Only public post previews; never use an arbitrary image or account avatar."""
    from src.integrations.product_metadata.sources import instagram_post_url

    result = dict(title=None, description=None, image_url=None, price=None, currency=None)
    if not instagram_post_url(base_url.removesuffix("embed/captioned/").removesuffix("embed/")):
        return result  # Login/challenge redirects are not the linked post.
    soup = BeautifulSoup(html, "html.parser")
    tags = meta_tags(soup)
    title = tags.get("og:title") or tags.get("twitter:title")
    if title and title.casefold() not in {"instagram", "login • instagram", "log in • instagram"}:
        result["title"] = title[:200]
    result["image_url"] = tags.get("og:image") or tags.get("twitter:image")
    # Public embeds can omit Open Graph but expose the post's main image.
    image = soup.select_one("img.EmbeddedMediaImage[src]")
    if not result["image_url"] and image:
        result["image_url"] = image["src"]
    if not result["title"]:
        caption = soup.select_one(".Caption")
        if caption:
            result["title"] = caption.get_text(" ", strip=True)[:200] or None
    if result["image_url"]:
        result["image_url"] = urljoin(base_url, result["image_url"])
    return result
