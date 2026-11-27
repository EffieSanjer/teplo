"""Best-effort title and price for a link sent to the bot. Does not store images."""

import re
import time
from decimal import Decimal

from src.config import Settings
from src.integrations.product_metadata.network import FetchError, fetch_public
from src.integrations.product_metadata.parser import parse_instagram_post, parse_telegram_post
from src.integrations.product_metadata.routes import load_page_draft
from src.integrations.product_metadata.sources import (
    instagram_post_url,
    preview_url,
    telegram_fallback_url,
    telegram_post,
)
from src.modules.gifts.schemas import valid_url

_PRICE = re.compile(r"\d{1,12}(\.\d{1,2})?")
_CURRENCY = re.compile(r"[A-Z]{3}")


def preview_link(url: str, settings: Settings) -> dict:
    url = valid_url(url)
    deadline = time.monotonic() + settings.metadata_timeout_seconds * 3

    def fetch(target, max_bytes):
        remaining = min(settings.metadata_timeout_seconds, deadline - time.monotonic())
        if remaining <= 0:
            raise FetchError("Сайт не ответил вовремя")
        return fetch_public(target, max_bytes, remaining)

    try:
        if post := telegram_post(url):
            return _telegram_preview(url, post, settings, fetch)
        if post_url := instagram_post_url(url):
            return _instagram_preview(post_url, settings, fetch)
        draft, _, _, failure = load_page_draft(url, settings, fetch)
    except FetchError:
        return {}
    if failure and not draft.get("title") and draft.get("price") is None and not draft.get("image_url"):
        return {}
    return _fields(draft)


def _telegram_preview(url: str, post: tuple[str, str], settings: Settings, fetch) -> dict:
    found = {}
    for candidate in (preview_url(url), telegram_fallback_url(url)):
        if not candidate:
            continue
        try:
            html, content_type, final_url = fetch(candidate, settings.metadata_max_bytes)
        except FetchError:
            continue
        if content_type.split(";")[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
            continue
        found = _fields(parse_telegram_post(html, final_url, *post))
        if found.get("title") or found.get("image_url"):
            break
    return found


def _instagram_preview(post_url: str, settings: Settings, fetch) -> dict:
    found = {}
    for candidate in (post_url, f"{post_url}embed/captioned/"):
        try:
            html, content_type, final_url = fetch(candidate, settings.metadata_max_bytes)
        except FetchError:
            continue
        if content_type.split(";")[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
            continue
        opened = final_url.removesuffix("embed/captioned/").removesuffix("embed/")
        if instagram_post_url(opened) != post_url:
            continue
        found = _fields(parse_instagram_post(html, final_url))
        if found.get("title") or found.get("image_url"):
            break
    return found


def _fields(draft: dict) -> dict:
    title = draft.get("title")
    title = title.strip()[:200] if isinstance(title, str) and title.strip() else None
    price = draft.get("price")
    currency = draft.get("currency") if isinstance(draft.get("currency"), str) else None
    amount = None
    if price is not None and currency and _CURRENCY.fullmatch(currency):
        text = format(Decimal(str(price)), "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        if _PRICE.fullmatch(text):
            amount = text
        else:
            currency = None
    else:
        currency = None
    image_url = draft.get("image_url")
    image_url = image_url.strip() if isinstance(image_url, str) and image_url.strip() else None
    if image_url and len(image_url) > 4096:
        image_url = None
    return {
        "title": title,
        "price": amount,
        "currency": currency if amount else None,
        "image_url": image_url,
    }
