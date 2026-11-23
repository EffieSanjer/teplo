import json

import pytest

from src.integrations.product_metadata.avito import is_avito, parse_avito
from src.integrations.product_metadata.marketplaces import product_ref
from src.integrations.product_metadata.network import FetchError


URL = "https://www.avito.ru/krasnodar/posuda_i_tovary_dlya_kuhni/ikornitsa_morskoy_grebeshok_8242088827"


def test_shared_listing_identity():
    assert product_ref(URL + "?businessModeForceEnabled=true&utm_source=soc_sharing") == ("avito", "8242088827")
    assert product_ref(URL + "/") == ("avito", "8242088827")
    assert is_avito(URL)
    assert not is_avito(URL.replace("www.avito.ru", "avito.ru.evil.test"))
    assert not is_avito(URL.replace("www.avito.ru", "user:pass@www.avito.ru"))


def test_public_listing_metadata():
    product = {"@type": "Product", "name": "Икорница морской гребешок",
               "image": "https://images.example/photo.jpg",
               "offers": {"@type": "Offer", "price": "1500", "priceCurrency": "RUB"}}
    html = ('<script type="application/ld+json">' + json.dumps(product) + '</script>').encode()
    draft = parse_avito(html, URL, URL + "?utm_source=soc_sharing")
    assert draft["title"] == "Икорница морской гребешок"
    assert draft["price"] == "1500.00"
    assert draft["image_url"] == "https://images.example/photo.jpg"


def test_listing_microdata_and_not_recommendation_price():
    html = '''<h1 data-marker="item-view/title-info">Икорница</h1>
    <div data-marker="item-view/item-price"><meta itemprop="price" content="1200">
    <meta itemprop="priceCurrency" content="RUB"></div>
    <aside><meta itemprop="price" content="99"></aside>'''.encode()
    draft = parse_avito(html, URL, URL)
    assert draft["title"] == "Икорница"
    assert draft["price"] == "1200.00"


@pytest.mark.parametrize("html", [
    '<title>Авито — Объявления на сайте Авито</title><meta property="og:image" content="https://m.avito.ru/icons/touch-icon-512x512.png">',
    '<title>Доступ ограничен</title>',
    '<title>Captcha</title>',
    '<html></html>',
])
def test_shell_and_challenge_are_not_listing_metadata(html):
    with pytest.raises(FetchError, match="Авито"):
        parse_avito(html.encode(), URL, URL)


def test_redirect_to_another_listing_is_rejected():
    with pytest.raises(FetchError, match="Авито"):
        parse_avito(b'<title>Other</title>', URL.replace("8242088827", "123"), URL)


def test_api_does_not_download_avito_shell_icon(client, monkeypatch):
    from src.integrations.product_metadata import routes

    calls = []

    def fetch(url, *args):
        calls.append(url)
        return ('<title>Авито — Объявления на сайте Авито</title>'
                '<meta property="og:image" content="https://m.avito.ru/icons/touch-icon-512x512.png">').encode(), "text/html", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    response = client.post("/api/v1/metadata", json={"url": URL})
    assert response.status_code == 422
    assert "Авито" in response.json()["detail"]
    assert calls == [URL]
