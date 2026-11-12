"""Public previews only; no login, scraping proxies or private-channel access."""

import re
from urllib.parse import urlsplit, urlunsplit


def telegram_post(url: str) -> tuple[str, str] | None:
    parts = urlsplit(url)
    if (
        parts.scheme in {"http", "https"}
        and not parts.username and not parts.password
        and parts.port in {None, 80 if parts.scheme == "http" else 443}
        and parts.hostname in {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}
    ):
        match = re.fullmatch(r"/(?:s/)?([A-Za-z][A-Za-z0-9_]{3,})/(\d+)/?", parts.path)
        if match:
            return match[1], match[2]
    return None


def preview_url(url: str) -> str:
    if post := telegram_post(url):
        return urlunsplit(("https", "t.me", f"/{post[0]}/{post[1]}", "embed=1", ""))
    return url


def instagram_post_url(url: str) -> str | None:
    parts = urlsplit(url)
    if (
        parts.scheme in {"http", "https"}
        and not parts.username and not parts.password
        and parts.port in {None, 80 if parts.scheme == "http" else 443}
        and parts.hostname in {"instagram.com", "www.instagram.com", "m.instagram.com"}
    ):
        match = re.fullmatch(r"/(p|reel|reels|tv)/([A-Za-z0-9_-]+)/?", parts.path)
        if match:
            kind = "reel" if match[1] == "reels" else match[1]
            return f"https://www.instagram.com/{kind}/{match[2]}/"
    return None


def telegram_fallback_url(url: str) -> str | None:
    if post := telegram_post(url):
        return f"https://t.me/s/{post[0]}/{post[1]}"
    return None
