import json
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


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


def parse_metadata(html: bytes, base_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    tags = {}
    for tag in soup.find_all("meta"):
        key = tag.get("property") or tag.get("name")
        if key and isinstance(tag.get("content"), str):
            tags[key] = tag["content"].strip()
    result = {
        "title": tags.get("og:title") or tags.get("twitter:title") or (soup.title.get_text(strip=True) if soup.title else None),
        "description": tags.get("og:description") or tags.get("description"),
        "image_url": tags.get("og:image") or tags.get("og:image:secure_url") or tags.get("twitter:image") or tags.get("twitter:image:src"),
        "price": None,
        "currency": None,
    }
    if urlsplit(base_url).hostname == "t.me":
        message = soup.select_one(".tgme_widget_message_text")
        photo = soup.select_one(".tgme_widget_message_photo_wrap")
        if message and not result["title"]:
            result["title"] = message.get_text(" ", strip=True)
        if photo and not result["image_url"]:
            match = re.search(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", photo.get("style", ""))
            if match:
                result["image_url"] = match[1]
    products = []

    def visit(value, depth=0):
        if depth > 20:
            return
        if isinstance(value, list):
            for entry in value:
                visit(entry, depth + 1)
        elif isinstance(value, dict):
            types = value.get("@type", [])
            if types == "Product" or isinstance(types, list) and "Product" in types:
                products.append(value)
            if "@graph" in value:
                visit(value["@graph"], depth + 1)

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            visit(json.loads(script.string or script.get_text()))
        except (ValueError, RecursionError):
            continue
    if len(products) == 1:
        product = products[0]
        for key in ("name", "description"):
            if isinstance(product.get(key), str) and product[key].strip():
                result["title" if key == "name" else key] = product[key].strip()
        image = product.get("image")
        if isinstance(image, list):
            image = image[0] if image else None
        if isinstance(image, dict):
            image = image.get("url")
        if isinstance(image, str):
            result["image_url"] = image
        offers = product.get("offers", [])
        if isinstance(offers, dict):
            offers = [offers]
        if isinstance(offers, list) and len(offers) == 1 and isinstance(offers[0], dict):
            offer = offers[0]
            if offer.get("@type") is None or offer.get("@type") == "Offer":
                result["price"] = parse_price(offer.get("price"))
                result["currency"] = offer.get("priceCurrency")
    elif not products:
        result["price"] = parse_price(tags.get("product:price:amount"))
        result["currency"] = tags.get("product:price:currency")
    currency = result["currency"]
    if (
        not isinstance(currency, str)
        or len(currency) != 3
        or not currency.isascii()
        or not currency.isalpha()
    ):
        result["price"], result["currency"] = None, None
    else:
        result["currency"] = currency.upper()
    if result["image_url"]:
        result["image_url"] = urljoin(base_url, result["image_url"])
    result["title"] = result["title"][:200] if result["title"] else None
    result["description"] = result["description"][:5000] if result["description"] else None
    return result
