from decimal import Decimal

from src.config import get_settings
from src.integrations.telegram.bot import _extract_url, wish_offer
from src.integrations.telegram.link_preview import preview_link


class _Entity:
    def __init__(self, kind, offset, length, url=None):
        self.type = kind
        self.offset = offset
        self.length = length
        self.url = url


class _Message:
    def __init__(self, text=None, caption=None, entities=None):
        self.text = text
        self.caption = caption
        self.entities = entities
        self.caption_entities = None


def test_extracts_link_entity_before_surrounding_text():
    text = "смотри https://shop.example/item."
    message = _Message(
        text, entities=[_Entity("url", text.index("https"), len("https://shop.example/item."))]
    )
    assert _extract_url(message) == "https://shop.example/item"


def test_wish_offer_escapes_title_and_keeps_the_link():
    image_id = "11111111-1111-4111-8111-111111111111"
    text, target = wish_offer(
        "https://fast-tundra-1847.a.tuna.free",
        "https://shop.example/item?id=1",
        {"title": "Лампа <b>", "price": "1200.5", "currency": "RUB"},
        image_id=image_id,
    )
    assert "Лампа &lt;b&gt;" in text
    assert "1200.5 ₽" in text
    assert "Первое фото" in text
    assert "Добавить" not in text
    assert target.startswith("https://fast-tundra-1847.a.tuna.free?")
    assert "url=https%3A%2F%2Fshop.example%2Fitem%3Fid%3D1" in target
    assert "title=" in target
    assert "price=1200.5" in target
    assert "currency=RUB" in target
    assert f"image_id={image_id}" in target


def test_wish_offer_without_preview_still_opens_the_form():
    text, target = wish_offer("https://app.example", "https://shop.example/item", {})
    assert "не удалось" in text
    assert target.endswith("url=https%3A%2F%2Fshop.example%2Fitem")


def test_preview_parses_product_html(monkeypatch):
    html = b"""<html><head>
    <script type="application/ld+json">{"@type":"Product","name":"Nice book",
    "image":"/cover.png","offers":{"@type":"Offer","price":"1200.50","priceCurrency":"RUB"}}
    </script></head></html>"""

    def fetch(url, max_bytes, timeout):
        assert url == "https://shop.example/item"
        assert max_bytes > 0 and timeout > 0
        return html, "text/html", url

    monkeypatch.setattr("src.integrations.telegram.link_preview.fetch_public", fetch)
    preview = preview_link("https://shop.example/item", get_settings())
    assert preview == {
        "title": "Nice book",
        "price": "1200.5",
        "currency": "RUB",
        "image_url": "https://shop.example/cover.png",
    }
    assert isinstance(Decimal(preview["price"]), Decimal)


def test_preview_failure_returns_empty(monkeypatch):
    from src.integrations.product_metadata.network import FetchError

    def fetch(url, max_bytes, timeout):
        raise FetchError("Сайт не ответил вовремя")

    monkeypatch.setattr("src.integrations.telegram.link_preview.fetch_public", fetch)
    assert preview_link("https://shop.example/item", get_settings()) == {}


def test_preview_keeps_first_telegram_photo(monkeypatch):
    html = b'''<div class="tgme_widget_message" data-post="finds/123">
      <div class="tgme_widget_message_author"><span>Finds</span></div>
      <a class="tgme_widget_message_photo_wrap" style="background-image:url('https://cdn.example/first.jpg')"></a>
      <a class="tgme_widget_message_photo_wrap" style="background-image:url('https://cdn.example/second.jpg')"></a>
    </div>'''

    def fetch(url, max_bytes, timeout):
        return html, "text/html", url

    monkeypatch.setattr("src.integrations.telegram.link_preview.fetch_public", fetch)
    preview = preview_link("https://t.me/finds/123", get_settings())
    assert preview["title"] == "Finds"
    assert preview["image_url"] == "https://cdn.example/first.jpg"
