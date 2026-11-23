import json

import pytest

from src.integrations.product_metadata.marketplaces import (
    embedded_product,
    marketplace_title,
    prefer_large_image,
    product_ref,
    public_product,
    reject_marketplace_challenge,
    reject_yandex_challenge,
    state_product,
    wildberries_basket,
)
from src.integrations.product_metadata.network import FetchError


@pytest.mark.parametrize("url, expected", [
    ("https://www.wildberries.ru/catalog/1126771984/detail.aspx?targetUrl=SN", ("wildberries", "1126771984")),
    ("http://www.lamoda.ru/p/MP002XU08HF3/?utm_source=common", ("lamoda", "MP002XU08HF3")),
    ("https://ozon.ru/product/batteries-123456/", ("ozon", "123456")),
    ("https://ozon.ru/t/gmg46Bl", None),
    ("https://wildberries.ru.evil.test/catalog/1/detail.aspx", None),
    ("https://user:pass@wildberries.ru/catalog/1/detail.aspx", None),
])
def test_product_identity(url, expected):
    assert product_ref(url) == expected


def test_yandex_captcha_is_not_event_metadata():
    with pytest.raises(FetchError, match="Яндекс"):
        reject_yandex_challenge(b"<title>Captcha</title>", "https://afisha.yandex.ru/showcaptcha?retpath=event")
    reject_yandex_challenge(b"<title>Concert</title>", "https://afisha.yandex.ru/moscow/concert/example")
    reject_yandex_challenge(b"<title>Captcha</title>", "https://example.com/showcaptcha")


def test_state_selects_exact_product_not_recommendation():
    state = {"products": [
        {"sku": "OTHER", "name": "Recommendation", "image": "https://example.com/wrong.jpg"},
        {"sku": "MP002XU08HF3", "name": "Product", "images": ["https://example.com/right.jpg"],
         "price": {"value": 1200, "currency": "RUB"}},
    ]}
    html = f'<script type="application/json">{json.dumps(state)}</script>'.encode()
    result = embedded_product(html, "https://lamoda.ru/p/MP002XU08HF3/")
    assert result["title"] == "Product"
    assert result["image_url"] == "https://example.com/right.jpg"
    assert result["price"] == "1200.00"


def test_conflicting_variants_are_not_selected():
    html = b'<script type="application/json">[{"id":123,"name":"A"},{"id":123,"name":"B"}]</script>'
    assert embedded_product(html, "https://ozon.ru/product/123/") == {}


def test_state_is_not_executed_and_site_currency_can_be_inferred():
    html = b'<script>window.__INITIAL_STATE__ = {"id":123,"name":"A","price":150};</script>'
    result = embedded_product(html, "https://ozon.ru/product/123/")
    assert result["title"] == "A"
    assert result["price"] == "150.00"
    assert result["currency"] == "RUB"
    assert embedded_product(html.replace(b'{"id"', b'alert(1); {"id"'), "https://ozon.ru/product/123/") == {}


def test_wb_optional_public_catalog():
    def fetch(url, max_bytes):
        if "wbbasket.ru" in url:
            raise FetchError("Unavailable")
        assert "nm=1126771984" in url
        return json.dumps({"data": {"products": [
            {"id": 123, "name": "Wrong"},
            {"id": 1126771984, "name": "Candle", "salePriceU": 285000},
        ]}}).encode(), "application/json", url

    result = public_product("https://wildberries.ru/catalog/1126771984/detail.aspx", fetch, 10000)
    assert result["title"] == "Candle"
    assert result["price"] == "2850.00"
    assert result["currency"] == "RUB"


def test_wb_block_does_not_break_fallback():
    def fetch(*args):
        raise FetchError("Blocked")

    assert public_product("https://wildberries.ru/catalog/1126771984/detail.aspx", fetch, 10000) == {}


def test_wb_cdn_requires_matching_article_and_has_bounded_attempts():
    urls = []

    def fetch(url, limit):
        urls.append(url)
        card = {"nm_id": 1126771984 if "basket-43." in url else 123, "imt_name": "Cardigan"}
        return json.dumps(card).encode(), "application/json", url

    data = wildberries_basket("1126771984", fetch, 10000)
    assert data["title"] == "Cardigan"
    assert data["image_url"] == "https://basket-43.wbbasket.ru/vol11267/part1126771/1126771984/images/big/1.webp"
    assert len(urls) <= 4

    def wrong_product(url, limit):
        return b'{"nm_id":123}', "application/json", url

    assert wildberries_basket("1126771984", wrong_product, 10000) == {}


def test_ozon_short_link_has_no_static_product_ref():
    assert product_ref("https://ozon.ru/t/gmg46Bl") is None
    assert product_ref("https://www.ozon.ru/product/some-item-123456789/") == ("ozon", "123456789")


def test_marketplace_challenge_detection():
    with pytest.raises(FetchError, match="Lamoda"):
        reject_marketplace_challenge(
            b"<html><head><title>Checking device</title></head><body>js-challenge-loader</body></html>",
            "https://www.lamoda.ru/p/MP002XU08HF3/",
        )
    with pytest.raises(FetchError, match="Мегамаркет"):
        reject_marketplace_challenge(
            "<html><body>проверка устройства</body></html>".encode("utf-8"),
            "https://megamarket.ru/catalog/details/1/",
        )
    with pytest.raises(FetchError, match="Золотое яблоко"):
        reject_marketplace_challenge(
            b"<html><title>checking device</title></html>",
            "https://goldapple.ru/19000123456",
        )
    reject_marketplace_challenge(
        b"<html><title>Product</title></html>",
        "https://www.lamoda.ru/p/MP002XU08HF3/",
    )


def test_title_cleanup_and_large_images():
    assert marketplace_title("Крем для лица купить по низкой цене на OZON", "ozon") == "Крем для лица"
    assert marketplace_title("Товар | Мегамаркет", "megamarket") == "Товар"
    assert prefer_large_image(
        "https://cdn1.ozone.ru/s3/multimedia-1/wc200/1.jpg", "ozon"
    ).endswith("/wc1000/1.jpg")
    assert "/images/big/" in prefer_large_image(
        "https://basket-01.wbbasket.ru/vol1/part1/1/images/c246x328/1.webp", "wildberries"
    )
    assert prefer_large_image(
        "https://ae01.alicdn.com/kf/item_220x220.jpg", "aliexpress"
    ).endswith("/kf/item.jpg")


def test_embedded_nuxt_state_loose_json():
    html = b"""<script>window.__NUXT__={state:{product:{id:123456789,name:'Phone',price:{value:19990,currency:'RUB'},images:['/img.jpg']}}};</script>"""
    result = embedded_product(html, "https://www.ozon.ru/product/phone-123456789/")
    assert result["title"] == "Phone"
    assert result["price"] == "19990.00"
    assert result["currency"] == "RUB"
    assert result["image_url"].endswith("/img.jpg")


def test_embedded_apollo_state_exact_id():
    html = (
        '<script>window.__APOLLO_STATE__='
        + json.dumps({"Product:MP002XU08HF3": {"id": "MP002XU08HF3", "__typename": "Product", "name": "Coat", "price": 5000}})
        + ";</script>"
    ).encode()
    result = embedded_product(html, "https://www.lamoda.ru/p/MP002XU08HF3/")
    assert result["title"] == "Coat"
    assert result["price"] == "5000.00"
    assert result["currency"] == "RUB"


def test_lamoda_public_api():
    def fetch(url, max_bytes):
        assert url == "https://api.lamoda.ru/catalog/products/MP002XU08HF3/"
        return json.dumps({
            "id": "MP002XU08HF3",
            "name": "Платье",
            "price": "3 490",
            "currency": "RUB",
            "images": [{"src": "https://a.lamoda.ru/1.jpg"}],
        }).encode(), "application/json", url

    result = public_product("https://www.lamoda.ru/p/MP002XU08HF3/", fetch, 10000)
    assert result["title"] == "Платье"
    assert result["price"] == "3490.00"
    assert result["currency"] == "RUB"
    assert result["image_url"] == "https://a.lamoda.ru/1.jpg"


def test_megamarket_blocked_json_is_ignored():
    def fetch(url, max_bytes):
        return json.dumps({"error": "blocked", "code": 7}).encode(), "application/json", url

    assert public_product("https://megamarket.ru/catalog/details/600005678442/", fetch, 10000) == {}


def test_aliexpress_runparams_from_state():
    html = (
        '<script>window.runParams = {"data":{"titleModule":{"subject":"Phone Case"},'
        '"imageModule":{"imagePathList":["//ae01.alicdn.com/kf/a.jpg","//ae01.alicdn.com/kf/b.jpg"]},'
        '"priceModule":{"formatedActivityPrice":"1 234,56 \\u0440\\u0443\\u0431.","currencyCode":"RUB"}}};</script>'
    ).encode("utf-8")
    result = state_product(html, "https://aliexpress.ru/item/1005001234567890.html")
    assert result["title"] == "Phone Case"
    assert result["image_url"] == "https://ae01.alicdn.com/kf/a.jpg"
    assert result["price"] == "1234.56"
    assert result["currency"] == "RUB"


def test_ozon_composer_widgets():
    payload = {
        "widgetStates": {
            "webProductHeading-1": json.dumps({"title": "Наушники — купить на OZON"}),
            "webGallery-2": json.dumps({"images": [{"src": "https://cdn1.ozone.ru/s3/multimedia-1/wc200/1.jpg"}]}),
            "webSale-3": json.dumps({"price": "1 990 ₽"}),
        }
    }

    def fetch(url, max_bytes):
        assert "composer-api.bx/page/json/v2" in url
        assert "url=%2Fproduct%2Fheadphones-123456%2F" in url
        return json.dumps(payload).encode(), "application/json", url

    result = public_product("https://www.ozon.ru/product/headphones-123456/", fetch, 10000)
    assert result["title"] == "Наушники"
    assert result["price"] == "1990.00"
    assert result["currency"] == "RUB"
    assert result["image_url"].endswith("1.jpg")
