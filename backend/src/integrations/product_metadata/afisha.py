"""Public ticket-widget sessions and event-title cleanup; no purchase operations."""

import base64
import json
import re
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

from .network import FetchError

_YANDEX_IMAGE_PREFIXES = ("/get-tickets/", "/get-afishanew/", "/get-afisha/")
_TICKET_HOST_SUFFIXES = (
    "afisha.yandex.ru", "widget.afisha.yandex.ru", "afisha.ru", "kassir.ru",
    "ticketland.ru", "live.mts.ru", "mtslive.ru", "ponominalu.ru", "kassy.ru",
    "redkassa.ru", "concert.ru", "bigbilet.ru", "ticketscloud.ru",
    "qtickets.events", "russpass.ru", "culture.ru",
)


def is_ticket_page(url: str) -> bool:
    try:
        host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in _TICKET_HOST_SUFFIXES)


def clean_event_title(title: str | None) -> str | None:
    """Drop SEO wrappers like `Билеты на «X» … на Яндекс Афише`."""
    if not title or not isinstance(title, str):
        return None
    text = re.sub(r"\s+", " ", title).strip()
    quoted = re.fullmatch(
        r"билеты\s+на\s+[«\"](.+?)[»\"](?:\s+в\s+.+?)?\s*[|\-–—].+",
        text,
        flags=re.I,
    )
    if quoted:
        text = quoted.group(1).strip()
    else:
        plain = re.fullmatch(r"билеты\s+на\s+(.+?)\s*[|\-–—].+", text, flags=re.I)
        if plain:
            text = plain.group(1).strip()
    text = re.sub(
        r"\s*[|\-–—]\s*(?:концерты|спектакли|события|афиша|яндекс\s*афиш\w*|"
        r"kassir|ticketland|mts\s*live|ponominalu).*$",
        "",
        text,
        flags=re.I,
    ).strip(" -–—|,«»\"")
    return text[:200] if len(text) >= 2 else (title.strip()[:200] or None)


def session_api_url(url):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname != "widget.afisha.yandex.ru"
            or parts.username or parts.password or parts.port not in {None, 443}):
        return None
    match = re.fullmatch(r"/(?:w|api/tickets/v1)/sessions/([^/]+)", parts.path)
    if not match:
        return None
    key = unquote(match[1])
    if len(key) > 256:
        return None
    try:
        decoded = base64.b64decode(key, validate=True).decode("ascii")
    except (ValueError, UnicodeError):
        return None
    if not re.fullmatch(r"\d+\|\d+\|\d+\|\d+", decoded):
        return None
    clients = parse_qs(parts.query).get("clientKey", [])
    if len(clients) != 1 or not re.fullmatch(r"[0-9a-fA-F-]{36}", clients[0]):
        return None
    return ("https://widget.afisha.yandex.ru/api/tickets/v1/sessions/"
            + quote(key, safe="") + "?" + urlencode({"clientKey": clients[0]}))


def _public_yandex_image(url: str) -> bool:
    parts = urlsplit(url)
    return (
        parts.scheme == "https" and parts.hostname == "avatars.mds.yandex.net"
        and not parts.username and not parts.password and parts.port in {None, 443}
        and parts.path.startswith(_YANDEX_IMAGE_PREFIXES)
    )


def fetch_session(endpoint, fetch, max_bytes):
    body, kind, _ = fetch(endpoint, max_bytes)
    if kind.split(";")[0].strip().lower() != "application/json":
        raise FetchError("Афиша не предоставила данные мероприятия")
    try:
        payload = json.loads(body)
        if payload["status"] != "success":
            raise ValueError
        event = payload["result"]["session"]["event"]
        if not isinstance(event, dict):
            raise ValueError
        title = event.get("name")
        images = event.get("images", [])
        if not isinstance(images, list):
            raise ValueError
        candidates = []
        for image in images:
            if not isinstance(image, dict) or image.get("crop"):
                continue
            url = image.get("url")
            if isinstance(url, str) and _public_yandex_image(url):
                candidates.append(url)
        candidates = sorted(dict.fromkeys(candidates), key=lambda url: not url.endswith("/orig"))[:4]
        if not isinstance(title, str) or not title.strip():
            raise ValueError
        # Ticket prices are session/seat-specific; deliberately leave them empty.
        return {"title": title.strip()[:200], "image_urls": candidates,
                "image_url": candidates[0] if candidates else None}
    except (ValueError, KeyError, TypeError, RecursionError):
        raise FetchError("Афиша не предоставила данные мероприятия") from None
