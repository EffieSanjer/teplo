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


@pytest.mark.parametrize("kind", ["p", "reel", "reels", "tv"])
def test_instagram_share_preview_url(kind):
    from src.integrations.product_metadata.sources import instagram_post_url

    expected = "reel" if kind == "reels" else kind
    assert instagram_post_url(f"https://instagram.com/{kind}/Abc_123-/?igsh=tracking") == (
        f"https://www.instagram.com/{expected}/Abc_123-/"
    )
    for url in [
        "https://instagram.com.evil.test/p/abc/", "https://user:pass@instagram.com/p/abc/",
        "https://instagram.com:8443/p/abc/", "https://instagram.com/accounts/login/",
        "https://instagram.com/stories/name/123/", "https://instagram.com/name/",
    ]:
        assert instagram_post_url(url) is None


@pytest.mark.parametrize("failure", ["http", "login", "empty", "photo"])
def test_instagram_422_falls_back_to_public_embed(client, monkeypatch, failure):
    import io

    from PIL import Image

    from src.integrations.product_metadata import routes

    image = io.BytesIO()
    Image.new("RGB", (20, 30), "blue").save(image, "PNG")
    calls = []

    def fetch(url, max_bytes, timeout):
        calls.append(url)
        assert 0 < timeout <= 8
        if url == "https://www.instagram.com/p/Abc/":
            if failure == "http":
                raise FetchError("Сайт не предоставил данные")
            if failure == "login":
                return b'<meta property="og:image" content="https://cdn.example/avatar.jpg">', "text/html", "https://www.instagram.com/accounts/login/"
            if failure == "photo":
                return b'<meta property="og:image" content="https://cdn.example/expired.jpg">', "text/html", url
            return b"<title>Instagram</title>", "text/html", url
        if url == "https://cdn.example/expired.jpg":
            raise FetchError("Фото недоступно")
        if url.endswith("/embed/captioned/"):
            return (
                b'<img class="Avatar" src="https://cdn.example/avatar.jpg">'
                b'<div class="Caption">A nice find</div>'
                b'<img class="EmbeddedMediaImage" src="https://cdn.example/post.jpg">',
                "text/html", url,
            )
        assert url == "https://cdn.example/post.jpg"
        return image.getvalue(), "image/png", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://instagram.com/p/Abc/?igsh=track"})
    assert response.status_code == 200
    assert response.json()["title"] == "A nice find"
    assert response.json()["image_id"]
    assert response.json()["description"] is None
    assert "https://cdn.example/avatar.jpg" not in calls
    assert client.get(f"/api/v1/media/{response.json()['image_id']}").status_code == 200


def test_instagram_unavailable_returns_hint_not_422_and_link_can_be_saved(client, monkeypatch):
    from src.config import get_settings
    from src.integrations.product_metadata import routes

    def failed(*args):
        raise FetchError("Сайт не предоставил данные")

    monkeypatch.setattr(routes, "fetch_public", failed)
    url = "https://www.instagram.com/reel/Abc/?igsh=track"
    response = client.post("/api/v1/metadata", json={"url": url})
    assert response.status_code == 200
    assert response.json()["image_id"] is None
    assert response.json()["title"] is None
    assert "Сайт не предоставил фото" in response.json()["warning"]
    assert client.post("/api/v1/items", json={
        "recipient_id": get_settings().dev_user_id, "list_type": "wishlist",
        "item_type": "gift", "url": url,
    }).status_code == 201


def test_instagram_does_not_import_other_post_after_redirect(client, monkeypatch):
    from src.integrations.product_metadata import routes

    def fetch(url, *args):
        if url.endswith("favicon.ico"):
            raise FetchError("No icon")
        return b'<meta property="og:title" content="Wrong"><meta property="og:image" content="/wrong.jpg">', "text/html", "https://www.instagram.com/p/Other/"

    monkeypatch.setattr(routes, "fetch_public", fetch)
    data = client.post("/api/v1/metadata", json={"url": "https://www.instagram.com/p/Abc/"}).json()
    assert data["title"] is None
    assert data["image_id"] is None


def test_instagram_image_keeps_ssrf_validation(client, monkeypatch):
    from src.integrations.product_metadata import routes

    original = routes.fetch_public

    def fetch(url, *args):
        if url.startswith("https://www.instagram.com/"):
            return b'<meta property="og:title" content="Find"><meta property="og:image" content="http://127.0.0.1/private">', "text/html", url
        return original(url, *args)

    monkeypatch.setattr(routes, "fetch_public", fetch)
    data = client.post("/api/v1/metadata", json={"url": "https://www.instagram.com/p/Abc/"}).json()
    assert data["title"] == "Find"
    assert data["image_id"] is None


def test_instagram_fallback_stops_at_deadline(client, monkeypatch):
    from src.integrations.product_metadata import routes

    clock = [0]
    calls = []
    monkeypatch.setattr(routes.time, "monotonic", lambda: clock[0])

    def fetch(url, *args):
        calls.append(url)
        clock[0] = 17
        raise FetchError("Timeout")

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://www.instagram.com/p/Abc/"})
    assert response.status_code == 200
    assert len(calls) == 1


def test_open_graph_title_is_case_insensitive_and_ignores_empty_duplicates():
    data = parse_metadata(b'''<title>Fallback</title>
    <meta name="OG:TITLE" content="A useful title"><meta property="og:title" content=" ">
    <script type="application/ld+json">{"@type":"Product","name":"Internal name"}</script>''', "https://shop.example")
    assert data["title"] == "Internal name"
    fallback = parse_metadata(b'<meta name="OG:TITLE" content="A useful title">'
                              b'<meta property="og:title" content=" ">', "https://shop.example")
    assert fallback["title"] == "A useful title"


def test_explicit_logos_then_icons_not_arbitrary_images():
    from src.integrations.product_metadata.parser import parse_logos

    html = b'''<script type="application/ld+json">{"@graph":[{"@type":"Organization",
    "logo":{"@type":"ImageObject","url":"/brand.png"}}]}</script>
    <img src="/random.jpg"><img class="site-logo" src="/header.png">
    <link rel="icon" href="/small.ico"><link rel="apple-touch-icon" href="/touch.png">
    <img alt="logo" src="data:image/png;base64,foo"><img alt="logo" src="/logo.svg">'''
    assert parse_logos(html, "https://shop.example/item") == [
        "https://shop.example/brand.png", "https://shop.example/header.png",
        "https://shop.example/touch.png", "https://shop.example/small.ico",
    ]


@pytest.mark.parametrize("prefer_logo", [False, True])
def test_product_photo_or_certificate_logo_priority(client, monkeypatch, prefer_logo):
    import io

    from PIL import Image

    from src.integrations.product_metadata import routes

    image = io.BytesIO()
    Image.new("RGBA", (32, 32), (255, 0, 0, 0)).save(image, "PNG")
    calls = []

    def fetch(url, *args):
        calls.append(url)
        if url == "https://shop.example/item":
            return b'''<meta property="og:title" content="Shop item">
            <meta property="og:image" content="/product.png"><img class="logo" src="/brand.png">''', "text/html", url
        assert url == ("https://shop.example/brand.png" if prefer_logo else "https://shop.example/product.png")
        return image.getvalue(), "image/png", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    data = client.post("/api/v1/metadata", json={"url": "https://shop.example/item", "prefer_logo": prefer_logo}).json()
    assert data["image_id"]
    assert data["image_is_icon"] is prefer_logo
    assert len(calls) == 2
    if prefer_logo:
        assert "логотип" in data["warning"]
    # Transparent brand images must be flattened onto white, not black.
    saved = client.get(f"/api/v1/media/{data['image_id']}")
    with Image.open(io.BytesIO(saved.content)) as clean:
        assert all(channel > 245 for channel in clean.getpixel((0, 0)))
    from src.config import get_settings

    created = client.post("/api/v1/items", json={
        "recipient_id": get_settings().dev_user_id, "list_type": "wishlist", "item_type": "gift",
        "url": "https://shop.example/item", "image_id": data["image_id"],
    })
    assert created.status_code == 201
    item = created.json()
    assert item["image_is_icon"] is prefer_logo
    updated = client.put(f"/api/v1/items/{item['id']}", json={
        "item_type": "gift", "url": item["url"], "image_id": item["image_id"], "title": "Edited",
    })
    assert updated.status_code == 200
    assert updated.json()["image_is_icon"] is prefer_logo


@pytest.mark.parametrize("failure", ["missing", "broken", "page"])
def test_logo_fallback_from_home_page_and_ico(client, monkeypatch, failure):
    import io

    from PIL import Image

    from src.integrations.product_metadata import routes

    icon = io.BytesIO()
    Image.new("RGB", (32, 32), "blue").save(icon, "ICO")
    calls = []

    def fetch(url, max_bytes, timeout):
        calls.append(url)
        assert 0 < timeout <= 8
        if url == "https://shop.example/item":
            if failure == "page":
                raise FetchError("No page")
            html = b'<meta property="og:title" content="Item">'
            if failure == "broken":
                html += b'<meta property="og:image" content="/expired.jpg">'
            return html, "text/html", url
        if url.endswith("expired.jpg"):
            raise FetchError("No photo")
        if url == "https://shop.example/":
            return b'<link rel="icon" href="/favicon.ico">', "text/html", url
        assert url == "https://shop.example/favicon.ico"
        return icon.getvalue(), "image/x-icon", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://shop.example/item", "prefer_logo": True})
    assert response.status_code == 200
    assert response.json()["image_id"]
    assert "логотип" in response.json()["warning"]
    assert "https://shop.example/" in calls


def test_logo_fallback_keeps_ssrf_validation_and_attempt_limits(client, monkeypatch):
    from src.integrations.product_metadata import routes

    original = routes.fetch_public
    calls = []

    def fetch(url, *args):
        calls.append(url)
        if url.startswith("https://shop.example/"):
            return b'<img class="logo" src="http://127.0.0.1/private"><link rel="icon" href="file:///secret">', "text/html", url
        return original(url, *args)

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://shop.example/item", "prefer_logo": True})
    assert response.status_code == 200
    assert response.json()["image_id"] is None
    assert len(calls) <= 7
    assert not any(url.startswith("file:") for url in calls)


def test_logo_fallback_respects_shared_deadline(client, monkeypatch):
    from src.integrations.product_metadata import routes

    clock = [0]
    monkeypatch.setattr(routes.time, "monotonic", lambda: clock[0])
    calls = []

    def fetch(url, *args):
        calls.append(url)
        clock[0] = 25
        return b'<img class="logo" src="/brand.png">', "text/html", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://shop.example/item", "prefer_logo": True})
    assert response.status_code == 200
    assert response.json()["image_id"] is None
    assert len(calls) == 1


def test_certificate_uses_photo_when_no_logo_is_loadable(client, monkeypatch):
    import io

    from PIL import Image

    from src.integrations.product_metadata import routes

    image = io.BytesIO()
    Image.new("RGB", (32, 32), "blue").save(image, "PNG")
    calls = []

    def fetch(url, *args):
        calls.append(url)
        if url == "https://shop.example/item":
            return b'<meta property="og:image" content="/photo.png">', "text/html", url
        if url.endswith("/photo.png"):
            return image.getvalue(), "image/png", url
        raise FetchError("No logo")

    monkeypatch.setattr(routes, "fetch_public", fetch)
    data = client.post("/api/v1/metadata", json={"url": "https://shop.example/item", "prefer_logo": True}).json()
    assert data["image_id"]
    assert data["warning"] is None
    assert calls[-1] == "https://shop.example/photo.png"


@pytest.mark.parametrize("prefer_logo", [False, True])
def test_public_post_uses_site_icon_only_for_certificates(client, monkeypatch, prefer_logo):
    import io

    from PIL import Image

    from src.integrations.product_metadata import routes

    image = io.BytesIO()
    Image.new("RGB", (32, 32), "blue").save(image, "PNG")
    calls = []

    def fetch(url, *args):
        calls.append(url)
        if url.endswith("/favicon.ico"):
            return image.getvalue(), "image/png", url
        return b'<img class="Avatar" src="https://cdn.example/avatar.png">', "text/html", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    data = client.post("/api/v1/metadata", json={"url": "https://www.instagram.com/p/Abc/", "prefer_logo": prefer_logo}).json()
    assert bool(data["image_id"]) is prefer_logo
    assert data["image_is_icon"] is prefer_logo
    assert any(url.endswith("/favicon.ico") for url in calls) is prefer_logo
    assert not any("avatar.png" in url for url in calls)


def test_primary_product_graph_references_and_alternative_images():
    html = b'''<meta property="og:title" content="Preview title">
    <meta property="og:image" content="/og.jpg"><meta property="OG:IMAGE" content="/og2.jpg">
    <meta name="twitter:image" content="/card.jpg"><link rel="image_src" href="/legacy.jpg">
    <script type="Application/LD+JSON; charset=utf-8">{"@graph":[
      {"@type":"WebPage","url":"https://shop.example/item","mainEntity":{"@id":"#item"}},
      {"@id":"#item","@type":["Thing","https://schema.org/Product"],"name":"Real product",
       "image":[{"@id":"#photo"},"/second.jpg"],"offers":{"@id":"#offer"}},
      {"@id":"#photo","@type":"ImageObject","contentUrl":"/first.jpg"},
      {"@id":"#offer","@type":"Offer","priceSpecification":{"price":"0","priceCurrency":"rub"}},
      {"@type":"Product","name":"Recommendation","image":"/wrong.jpg"}
    ]}</script>'''
    data = parse_metadata(html, "https://shop.example/item")
    assert data["title"] == "Real product"
    assert data["price"] == "0.00"
    assert data["currency"] == "RUB"
    assert data["image_urls"] == [f"https://shop.example/{name}.jpg"
                                  for name in ("first", "second", "og", "og2", "card", "legacy")]


def test_nested_primary_product_does_not_use_recommendations():
    data = parse_metadata(b'''<script type="application/ld+json">{
    "@type":"WebPage","mainEntity":{"@type":"Product","name":"Actual product"},
    "itemListElement":[{"@type":"Product","name":"Recommendation","image":"/wrong.jpg"}]}
    </script><img src="/banner.jpg">''', "https://shop.example/item")
    assert data["title"] == "Actual product"
    assert data["image_urls"] == []


def test_product_url_selects_one_product_without_mixing_fields():
    data = parse_metadata(b'''<meta property="og:image" content="/preview.jpg">
    <script type="application/ld+json">[
    {"@id":"#other","@type":"Product","url":"/other","name":"Other","description":"Wrong","image":"/wrong.jpg"},
    {"@id":"#selected","@type":"Product","url":"/item","name":"Selected"}]</script>''', "https://shop.example/item")
    assert data["title"] == "Selected"
    assert data["description"] is None
    assert data["image_urls"] == ["https://shop.example/preview.jpg"]


def test_ambiguous_products_do_not_supply_images_or_prices():
    data = parse_metadata(b'''<meta property="og:title" content="Collection">
    <meta property="og:image" content="/preview.jpg"><meta property="product:price:amount" content="7">
    <meta property="product:price:currency" content="RUB">
    <script type="application/ld+json">[{"@type":"Product","name":"One","image":"/one.jpg"},
    {"@type":"Product","name":"Two","image":"/two.jpg"}]</script>
    <div class="product-gallery"><img src="/random.jpg"></div>''', "https://shop.example/list")
    assert data["title"] == "Collection"
    assert data["price"] is None
    assert data["image_urls"] == ["https://shop.example/preview.jpg"]


def test_microdata_product_with_scoped_offer_and_lazy_images():
    data = parse_metadata(b'''<meta property="og:title" content="Preview">
    <main><div itemscope itemtype="https://schema.org/Product">
    <h1 itemprop="name">Product name</h1><p itemprop="description">Details</p>
    <img itemprop="image" src="data:image/gif;base64,placeholder" data-src="/original.jpg"
      srcset="/small.jpg 320w, /large.jpg 1200w">
    <div itemprop="brand" itemscope itemtype="https://schema.org/Brand"><b itemprop="name">Wrong name</b></div>
    <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
      <meta itemprop="price" content="2500.50"><meta itemprop="priceCurrency" content="RUB">
    </div></div></main>''', "https://shop.example/item")
    assert data["title"] == "Product name"
    assert data["description"] == "Details"
    assert data["price"] == "2500.50"
    assert data["image_urls"] == [f"https://shop.example/{name}.jpg" for name in ("large", "small", "original")]


def test_standalone_item_properties_and_product_gallery_fallbacks():
    data = parse_metadata(b'''<meta itemprop="name" content="Marked product">
    <meta itemprop="price" content="19.99"><meta itemprop="priceCurrency" content="EUR">
    <main><h1>Page heading</h1><div data-product-gallery><picture>
    <source data-srcset="/high.webp 2x, /low.webp 1x"><img data-original="/original.jpg"></picture></div>
    <div class="recommendations"><img class="product-image" src="/wrong.jpg"></div>
    <img src="/banner.jpg"></main>''', "https://shop.example/item")
    assert data["title"] == "Marked product"
    assert data["price"] == "19.99"
    assert data["image_urls"] == ["https://shop.example/high.webp", "https://shop.example/low.webp",
                                  "https://shop.example/original.jpg"]


def test_missing_product_fields_use_page_fallbacks():
    data = parse_metadata(b'''<script type="application/ld+json">{"@type":"Product","name":"Book"}</script>
    <meta property="product:price:amount" content="42"><meta property="product:price:currency" content="USD">
    <meta name="twitter:description" content="Preview details"><meta property="og:image:url" content="/photo.jpg">
    ''', "https://shop.example/item")
    assert data["title"] == "Book"
    assert data["description"] == "Preview details"
    assert data["price"] == "42.00"
    assert data["image_url"] == "https://shop.example/photo.jpg"
    assert parse_metadata(b'<main><h1>Product heading</h1></main><meta property="og:title" content="Shop">',
                          "https://shop.example/item")["title"] == "Product heading"


@pytest.mark.parametrize("offers", [
    '[{"price":"1","priceCurrency":"RUB"},{"price":"2","priceCurrency":"RUB"}]',
    '{"@type":"AggregateOffer","lowPrice":"1","highPrice":"2","priceCurrency":"RUB"}',
])
def test_ambiguous_offer_does_not_fall_back_to_page_price(offers):
    html = f'''<script type="application/ld+json">{{"@type":"Product","offers":{offers}}}</script>
    <meta property="product:price:amount" content="1"><meta property="product:price:currency" content="RUB">'''
    assert parse_metadata(html.encode(), "https://shop.example/item")["price"] is None


def test_image_candidates_are_unique_bounded_and_ignore_invalid_urls():
    import json

    images = ["data:image/png;base64,foo", "file:///secret", "http://[bad", "/logo.svg", "/ok.jpg", "/ok.jpg"]
    images += [f"/{index}.jpg" for index in range(20)]
    html = f'<script type="application/ld+json">{json.dumps({"@type": "Product", "image": images})}</script>'
    data = parse_metadata(html.encode(), "https://shop.example/item")
    assert len(data["image_urls"]) == 12
    assert data["image_url"] == "https://shop.example/ok.jpg"


@pytest.mark.parametrize("failure", ["network", "invalid-image"])
def test_image_import_tries_alternatives_before_logo(client, monkeypatch, failure):
    import io

    from PIL import Image

    from src.integrations.product_metadata import routes

    image = io.BytesIO()
    Image.new("RGB", (32, 32), "blue").save(image, "PNG")
    calls = []

    def fetch(url, *args):
        calls.append(url)
        if url == "https://shop.example/item":
            return b'''<script type="application/ld+json">{"@type":"Product","name":"Product",
            "image":["/broken.jpg","/good.jpg"]}</script><img class="logo" src="/brand.png">''', "text/html", url
        if url.endswith("/broken.jpg"):
            if failure == "network":
                raise FetchError("No image")
            return b"not an image", "image/jpeg", url
        assert url.endswith("/good.jpg")
        return image.getvalue(), "image/png", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://shop.example/item"})
    assert response.status_code == 200
    assert response.json()["image_id"]
    assert response.json()["warning"] is None
    assert len(calls) == 3


def test_photo_attempts_are_bounded_before_logo(client, monkeypatch):
    from src.integrations.product_metadata import routes

    calls = []

    def fetch(url, *args):
        calls.append(url)
        if url == "https://shop.example/item":
            return b'''<script type="application/ld+json">{"@type":"Product",
            "image":["/1.jpg","/2.jpg","/3.jpg","/4.jpg","/5.jpg"]}</script>''', "text/html", url
        raise FetchError("Unavailable")

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://shop.example/item"})
    assert response.status_code == 200
    assert response.json()["image_id"] is None
    assert len([url for url in calls if url.endswith(".jpg")]) == 4
    assert len(calls) == 5  # Page and photos only: no home page, logo or favicon requests.


def test_photo_alternatives_share_deadline(client, monkeypatch):
    from src.integrations.product_metadata import routes

    clock = [0]
    calls = []
    monkeypatch.setattr(routes.time, "monotonic", lambda: clock[0])

    def fetch(url, *args):
        calls.append(url)
        if url == "https://shop.example/item":
            return b'''<script type="application/ld+json">{"@type":"Product",
            "image":["/first.jpg","/second.jpg"]}</script>''', "text/html", url
        clock[0] = 25
        raise FetchError("Timeout")

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://shop.example/item"})
    assert response.status_code == 200
    assert calls == ["https://shop.example/item", "https://shop.example/first.jpg"]


def test_alternative_images_still_use_ssrf_validation(client, monkeypatch):
    import io

    from PIL import Image

    from src.integrations.product_metadata import routes

    original = routes.fetch_public
    image = io.BytesIO()
    Image.new("RGB", (32, 32), "blue").save(image, "PNG")
    calls = []

    def fetch(url, *args):
        calls.append(url)
        if url == "https://shop.example/item":
            return b'''<script type="application/ld+json">{"@type":"Product",
            "image":["http://127.0.0.1/private.jpg","/safe.jpg"]}</script>''', "text/html", url
        if url == "https://shop.example/safe.jpg":
            return image.getvalue(), "image/png", url
        return original(url, *args)

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://shop.example/item"})
    assert response.status_code == 200
    assert response.json()["image_id"]
    assert calls == ["https://shop.example/item", "http://127.0.0.1/private.jpg", "https://shop.example/safe.jpg"]


def test_product_identified_by_main_entity_of_page():
    data = parse_metadata(b'''<script type="application/ld+json">[
    {"@type":"Product","name":"Related","image":"/wrong.jpg"},
    {"@type":"Product","name":"Main","mainEntityOfPage":{"@id":"https://shop.example/item"}}
    ]</script>''', "https://shop.example/item")
    assert data["title"] == "Main"
    assert data["image_urls"] == []


def test_explicit_other_product_is_not_imported_as_current_product():
    data = parse_metadata(b'''<meta property="og:title" content="Current page">
    <script type="application/ld+json">{"@type":"Product","url":"/other",
    "name":"Recommendation","image":"/wrong.jpg"}</script>''', "https://shop.example/item")
    assert data["title"] == "Current page"
    assert data["image_urls"] == []


def test_microdata_image_object():
    data = parse_metadata(b'''<div itemscope itemtype="https://schema.org/Product">
    <span itemprop="image" itemscope itemtype="https://schema.org/ImageObject">
    <meta itemprop="contentUrl" content="/full.jpg"><link itemprop="url" href="/alternate.jpg">
    </span></div>''', "https://shop.example/item")
    assert data["image_urls"] == ["https://shop.example/full.jpg", "https://shop.example/alternate.jpg"]


@pytest.mark.parametrize("preview", [False, True])
def test_regular_items_never_fetch_or_store_site_icons(client, db, monkeypatch, preview):
    from sqlalchemy import func, select

    from src.infrastructure.database import Media
    from src.integrations.product_metadata import routes

    before = db.scalar(select(func.count()).select_from(Media))
    calls = []

    def fetch(url, *args):
        calls.append(url)
        assert url == "https://shop.example/item"
        html = b'<title>Product</title><img class="logo" src="/brand.png"><link rel="icon" href="/favicon.ico">'
        if preview:
            html += b'<meta property="og:image" content="/brand.png">'
        return html, "text/html", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": "https://shop.example/item"})
    assert response.status_code == 200
    assert response.json()["image_id"] is None
    assert response.json()["image_is_icon"] is False
    assert "логотип" not in response.json()["warning"]
    assert calls == ["https://shop.example/item"]
    assert db.scalar(select(func.count()).select_from(Media)) == before
