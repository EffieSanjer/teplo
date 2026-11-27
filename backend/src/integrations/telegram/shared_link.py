"""Parse title and price from share-sheet captions that wrap a product URL."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

_URL_RE = re.compile(
    r'https?://[^\s<>"«»“”]+|\bwww\.[^\s<>"«»“”]+',
    re.IGNORECASE,
)
_CURRENCY_TOKEN = r"(?:₽|руб(?:лей|ля|ль)?\.?|р\.|RUB|RUR|USD|EUR|GEL|KZT|BYN|€|\$|₸|₾)"
_AMOUNT_TOKEN = r"(?:\d{1,3}(?:[ \u00a0\u202f]\d{3})+|\d+)(?:[.,]\d{1,2})?"
_SPACES = r"[ \t\u00a0\u202f]*"
# Only explicit currency amounts: sizes, model numbers and discount percentages are not prices.
_PRICES_RE = re.compile(
    rf"(?<![\w.,])(?:(от)[ \t]+)?({_AMOUNT_TOKEN}){_SPACES}({_CURRENCY_TOKEN})(?!\w)"
    rf"|(?<!\w)({_CURRENCY_TOKEN}){_SPACES}({_AMOUNT_TOKEN})(?![\d.,])",
    re.IGNORECASE,
)
_GENERIC_LINE = re.compile(
    r"^(?:поделиться.*|смотри(?:те)?.*|посмотри(?:те)?.*|это точно тво[её].*|пост|ссылка|купить|перейти|скидка.*)$",
    re.IGNORECASE,
)
_EDGE_PUNCT = re.compile(r'^[\s:—–\-.,;!«»"()[\]]+|[\s:—–\-.,;!«»"()[\]]+$')
_TITLE_LABEL = re.compile(r"^(?:название|товар)\s*:\s*", re.IGNORECASE)
_PRICE_LABEL = re.compile(r"(?:цена|стоимость)\s*:?", re.IGNORECASE)
_TRAILING_ZA = re.compile(r"\s+за\s*$", re.IGNORECASE)
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


def extract_shared_link(text: str) -> str | None:
    """First http(s) URL from share text; mirrors frontend extractSharedLink."""
    for raw in _URL_RE.findall(text or ""):
        candidate = raw
        candidate = re.sub(r"[.,!?:;…'’]+$", "", candidate)
        for open_ch, close_ch in (("(", ")"), ("[", "]"), ("{", "}")):
            while (
                candidate.endswith(close_ch)
                and candidate.count(close_ch) > candidate.count(open_ch)
            ):
                candidate = candidate[:-1]
        candidate = re.sub(r"[.,!?:;…'’]+$", "", candidate)
        if candidate.lower().startswith("www."):
            candidate = f"https://{candidate}"
        if len(candidate) > 2048:
            continue
        try:
            parts = urlsplit(candidate)
        except ValueError:
            continue
        if (
            parts.scheme in {"http", "https"}
            and parts.hostname
            and not parts.username
            and not parts.password
        ):
            return candidate
    return None


def _currency_code(token: str) -> str:
    if re.match(r"^(₽|руб|р\.|RUB|RUR)", token, re.IGNORECASE):
        return "RUB"
    if re.match(r"^(€|EUR)$", token, re.IGNORECASE):
        return "EUR"
    if re.match(r"^(\$|USD)$", token, re.IGNORECASE):
        return "USD"
    if token == "₸":
        return "KZT"
    if token == "₾":
        return "GEL"
    return token.upper()


def extract_shared_details(text: str) -> dict | None:
    """Title/price carried by marketplace share messages around the URL."""
    url = extract_shared_link(text)
    if not url:
        return None
    result: dict = {"url": url}
    caption = _URL_RE.sub("", text[:16000])
    matches = list(_PRICES_RE.finditer(caption))
    values = []
    for match in matches:
        amount = match.group(2) or match.group(5)
        token = match.group(3) or match.group(4)
        if not amount or not token:
            continue
        price = re.sub(r"[\s\u00a0\u202f]", "", amount).replace(",", ".")
        values.append({"price": price, "currency": _currency_code(token)})
    if (
        values
        and all(value["price"] == values[0]["price"] and value["currency"] == values[0]["currency"]
                for value in values)
        and float(values[0]["price"]) < 1e12
    ):
        result.update(values[0])
        if matches and matches[0].group(1):
            result["price_mode"] = "from"
    caption = _PRICES_RE.sub("", caption)
    caption = _PRICE_LABEL.sub("", caption)
    caption = _TRAILING_ZA.sub("", caption)
    lines = []
    for raw_line in re.split(r"[\r\n]+", caption):
        line = _EDGE_PUNCT.sub("", raw_line)
        line = _TITLE_LABEL.sub("", line).strip()
        if _LETTER.search(line) and not _GENERIC_LINE.match(line):
            lines.append(line)
    if lines:
        result["title"] = lines[0][:200]
    return result


def merge_caption_preview(preview: dict, caption: dict | None) -> dict:
    """Fill gaps left by page scraping with share-caption title/price."""
    if not caption:
        return preview
    merged = dict(preview)
    if not merged.get("title") and caption.get("title"):
        merged["title"] = caption["title"]
    if merged.get("price") is None and caption.get("price") and caption.get("currency"):
        merged["price"] = caption["price"]
        merged["currency"] = caption["currency"]
    return merged
