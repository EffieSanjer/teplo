"""Public ticket-widget sessions; no account or purchase operations."""

import base64
import json
import re
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

from .network import FetchError


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
            if not isinstance(url, str):
                continue
            parts = urlsplit(url)
            if (parts.scheme == "https" and parts.hostname == "avatars.mds.yandex.net"
                    and not parts.username and not parts.password and parts.port in {None, 443}
                    and parts.path.startswith("/get-tickets/")):
                candidates.append(url)
        candidates = sorted(dict.fromkeys(candidates), key=lambda url: not url.endswith("/orig"))[:4]
        if not isinstance(title, str) or not title.strip():
            raise ValueError
        # Ticket prices are session/seat-specific; deliberately leave them empty.
        return {"title": title.strip()[:200], "image_urls": candidates,
                "image_url": candidates[0] if candidates else None}
    except (ValueError, KeyError, TypeError, RecursionError):
        raise FetchError("Афиша не предоставила данные мероприятия") from None
