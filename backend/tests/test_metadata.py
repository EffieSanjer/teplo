import socket

import pytest

from src.integrations.product_metadata import network
from src.integrations.product_metadata.network import FetchError, fetch_public, public_addresses
from src.integrations.product_metadata.parser import parse_metadata


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "0.0.0.0",
        "::1",
        "fc00::1",
        "fe80::1",
        "::ffff:127.0.0.1",
        "224.0.0.1",
        "2002:7f00:1::",
    ],
)
def test_private_addresses_blocked(monkeypatch, address):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [(socket.AF_INET, 1, 6, "", (address, 80))])
    with pytest.raises(FetchError):
        public_addresses("anything.example", 80)


def test_mixed_dns_blocked(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [
            (socket.AF_INET, 1, 6, "", ("93.184.216.34", 80)),
            (socket.AF_INET, 1, 6, "", ("127.0.0.1", 80)),
        ],
    )
    with pytest.raises(FetchError):
        public_addresses("example.com", 80)


@pytest.mark.parametrize(
    "url", ["http://localhost:9000", "file:///etc/passwd", "http://user:pass@example.com"]
)
def test_unsafe_urls(url):
    with pytest.raises(FetchError):
        fetch_public(url, 100, 1)


def test_json_ld_and_fallback():
    html = b"""<html><title>Fallback</title><meta property="og:title" content="OG title">
    <script type="application/ld+json">{"@graph":[{"@type":"Product","name":"Nice book",
    "description":"Paper","image":"/cover.png","offers":{"@type":"Offer","price":"1200.50","priceCurrency":"RUB"}}]}</script></html>"""
    parsed = parse_metadata(html, "https://example.com/product")
    assert parsed["title"] == "Nice book"
    assert parsed["image_url"] == "https://example.com/cover.png"
    assert parsed["price"] == "1200.50"
    assert parsed["currency"] == "RUB"
    assert parse_metadata(b"<title>Just a title</title>", "https://example.com")["title"] == "Just a title"
    assert parse_metadata(b"<html></html>", "https://example.com")["price"] is None


def test_ambiguous_offers_and_malformed_json():
    html = b"""<script type="application/ld+json">not json</script>
    <script type="application/ld+json">{"@type":"Product","name":"Book",
    "offers":[{"price":"1","priceCurrency":"RUB"},{"price":"2","priceCurrency":"RUB"}]}</script>"""
    assert parse_metadata(html, "https://example.com")["price"] is None


@pytest.mark.parametrize("url", [
    "https://www.instagram.com/p/abc/", "https://www.pinterest.com/pin/123/", "https://t.me/finds/123",
])
def test_social_open_graph(url):
    parsed = parse_metadata(
        b'<meta property="og:title" content="Find"><meta property="og:image" content="/photo.jpg">', url
    )
    assert parsed["title"] == "Find"
    assert parsed["image_url"].endswith("/photo.jpg")


def test_twitter_preview_fallback():
    parsed = parse_metadata(
        b'<meta name="twitter:title" content="Shop"><meta name="twitter:image" content="/shop.jpg">',
        "https://example.com",
    )
    assert parsed["title"] == "Shop"
    assert parsed["image_url"] == "https://example.com/shop.jpg"


def test_telegram_embed_and_private_link_handling():
    from src.integrations.product_metadata.sources import preview_url

    assert preview_url("https://t.me/finds/123?single") == "https://t.me/finds/123?embed=1"
    assert preview_url("https://t.me/s/finds/123") == "https://t.me/finds/123?embed=1"
    for url in ["https://t.me/c/123/456", "https://t.me/+invite", "https://t.me.evil.test/finds/123"]:
        assert preview_url(url) == url
    parsed = parse_metadata(
        b'<div class="tgme_widget_message_text">A book</div>'
        b'<a class="tgme_widget_message_photo_wrap" style="background-image:url(\'https://cdn.example/photo.jpg\')"></a>',
        "https://t.me/finds/123?embed=1",
    )
    assert parsed["title"] == "A book"
    assert parsed["image_url"] == "https://cdn.example/photo.jpg"


def test_redirect_revalidated(monkeypatch):
    checked = []

    def resolve(host, port):
        checked.append(host)
        if host == "localhost":
            raise FetchError("Blocked")
        return ["93.184.216.34"]

    class Response:
        status = 302

        def getheader(self, name):
            return "http://localhost/private"

    class Connection:
        def __init__(self, *args):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(network, "public_addresses", resolve)
    monkeypatch.setattr(network, "PinnedConnection", Connection)
    with pytest.raises(FetchError):
        fetch_public("https://example.com", 100, 1)
    assert checked == ["example.com", "localhost"]


def test_metadata_failure_does_not_block_save(client, monkeypatch):
    from src.config import get_settings
    from src.integrations.product_metadata import routes

    def failed(*args):
        raise FetchError("Сайт недоступен")

    monkeypatch.setattr(routes, "fetch_public", failed)
    assert client.post("/api/v1/metadata", json={"url": "https://example.com"}).status_code == 422
    assert (
        client.post(
            "/api/v1/items",
            json={
                "recipient_id": get_settings().dev_user_id,
                "list_type": "wishlist",
                "item_type": "gift",
                "url": "https://example.com",
            },
        ).status_code
        == 201
    )


def telegram_html(first="https://cdn.example/first.jpg", second="https://cdn.example/second.jpg"):
    return f'''<div class="tgme_widget_message" data-post="finds/123">
      <div class="tgme_widget_message_author"><a><span>Finds &amp; gifts</span></a></div>
      <div class="tgme_widget_message_text">A long advertisement, not the channel name</div>
      <a class="tgme_widget_message_photo_wrap" style="background-image:url('{first}')"></a>
      <a class="tgme_widget_message_photo_wrap" style="background-image:url('{second}')"></a>
    </div>'''.encode()


def test_telegram_parser_uses_channel_and_first_photo_of_linked_post():
    from src.integrations.product_metadata.parser import parse_telegram_post

    neighbour = telegram_html().replace(b"finds/123", b"finds/122").replace(b"first.jpg", b"wrong.jpg")
    result = parse_telegram_post(neighbour + telegram_html(), "https://t.me/s/finds/123", "finds", "123")
    assert result["title"] == "Finds & gifts"
    assert result["image_url"] == "https://cdn.example/first.jpg"
    assert result["description"] is None


def test_telegram_parser_does_not_use_avatar_or_neighbour_photo():
    from src.integrations.product_metadata.parser import parse_telegram_post

    html = b'<meta property="og:image" content="https://cdn.example/avatar.jpg">'
    html += telegram_html().replace(b"finds/123", b"finds/122")
    result = parse_telegram_post(html, "https://t.me/s/finds/123", "finds", "123")
    assert result["image_url"] is None
    assert result["title"] is None


def test_telegram_parser_header_title_and_img_fallback():
    from src.integrations.product_metadata.parser import parse_telegram_post

    html = b'''<div class="tgme_channel_info_header_title">Channel name</div>
    <div class="tgme_widget_message" data-post="finds/123">
      <a class="tgme_widget_message_photo_wrap"><img src="/first.jpg"></a>
    </div>'''
    parsed = parse_telegram_post(html, "https://t.me/s/finds/123", "finds", "123")
    assert parsed["title"] == "Channel name"
    assert parsed["image_url"] == "https://t.me/first.jpg"


@pytest.mark.parametrize("failure", ["http", "empty", "photo"])
def test_telegram_fallback_imports_first_photo_and_channel(client, monkeypatch, failure):
    import io

    from PIL import Image

    from src.integrations.product_metadata import routes

    image = io.BytesIO()
    Image.new("RGB", (10, 20), "blue").save(image, "PNG")
    calls = []

    def fetch(url, max_bytes, timeout):
        calls.append(url)
        assert 0 < timeout <= 8
        if url == "https://t.me/finds/123?embed=1":
            if failure == "http":
                raise FetchError("Сайт недоступен")
            if failure == "empty":
                return b"<title>Telegram</title>", "text/html", url
            return telegram_html(first="https://cdn.example/expired.jpg"), "text/html", url
        if url == "https://cdn.example/expired.jpg":
            raise FetchError("Фото недоступно")
        if url == "https://t.me/s/finds/123":
            return telegram_html(), "text/html; charset=utf-8", url
        assert url == "https://cdn.example/first.jpg"
        return image.getvalue(), "image/png", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://t.me/finds/123?single"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Finds & gifts"
    assert data["description"] is None
    assert data["image_id"]
    assert "первое фото" in data["warning"]
    assert "https://t.me/s/finds/123" in calls
    assert not any("second.jpg" in url for url in calls)
    assert client.get(f"/api/v1/media/{data['image_id']}").status_code == 200


def test_telegram_embed_success_does_not_fetch_fallback(client, monkeypatch):
    import io

    from PIL import Image

    from src.integrations.product_metadata import routes

    image = io.BytesIO()
    Image.new("RGB", (10, 10)).save(image, "PNG")
    calls = []

    def fetch(url, *args):
        calls.append(url)
        if "embed=1" in url:
            return telegram_html(), "text/html", url
        assert url == "https://cdn.example/first.jpg"
        return image.getvalue(), "image/png", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://t.me/finds/123"})
    assert response.status_code == 200
    assert response.json()["image_id"]
    assert len(calls) == 2


def test_telegram_unavailable_returns_hint_without_fake_photo(client, monkeypatch):
    from src.integrations.product_metadata import routes

    calls = []

    def fetch(url, *args):
        calls.append(url)
        raise FetchError("Недоступно")

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://t.me/finds/123"})
    assert response.status_code == 200
    assert response.json()["image_id"] is None
    assert response.json()["title"] is None
    assert "вручную" in response.json()["warning"]
    assert calls == ["https://t.me/finds/123?embed=1", "https://t.me/s/finds/123"]


def test_telegram_fallback_photo_keeps_ssrf_validation(client, monkeypatch):
    from src.integrations.product_metadata import routes

    original_fetch = routes.fetch_public

    def fetch(url, *args):
        if url.startswith("https://t.me/"):
            return telegram_html(first="http://127.0.0.1/private"), "text/html", url
        return original_fetch(url, *args)

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://t.me/finds/123"})
    assert response.status_code == 200
    assert response.json()["title"] == "Finds & gifts"
    assert response.json()["image_id"] is None


def test_telegram_fallback_only_for_public_message_urls():
    from src.integrations.product_metadata.sources import telegram_fallback_url

    assert telegram_fallback_url("https://telegram.me/finds/123?single") == "https://t.me/s/finds/123"
    for url in [
        "https://t.me/c/123/456", "https://t.me/+invite", "https://t.me/finds",
        "https://t.me.evil.test/finds/123", "https://user:pass@t.me/finds/123",
        "https://t.me:8443/finds/123",
    ]:
        assert telegram_fallback_url(url) is None


def test_telegram_fallback_stops_at_shared_deadline(client, monkeypatch):
    from src.integrations.product_metadata import routes

    clock = [0]
    calls = []
    monkeypatch.setattr(routes.time, "monotonic", lambda: clock[0])

    def fetch(url, *args):
        calls.append(url)
        clock[0] = 17
        raise FetchError("Timeout")

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://t.me/finds/123"})
    assert response.status_code == 200
    assert len(calls) == 1
