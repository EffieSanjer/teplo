from src.config import get_settings
from src.integrations.product_metadata.network import FetchError
from src.integrations.product_metadata.routes import load_page_draft


def test_wb_uses_public_catalog_before_blocked_html():
    calls = []

    def fetch(url, max_bytes):
        calls.append(url)
        if "wbbasket.ru" in url and url.endswith("/card.json"):
            return (
                b'{"nm_id":1126771984,"imt_name":"Cardigan"}',
                "application/json",
                url,
            )
        if "card.wb.ru" in url:
            raise FetchError("Blocked")
        raise FetchError("HTML blocked")

    draft, html, final_url, failure = load_page_draft(
        "https://www.wildberries.ru/catalog/1126771984/detail.aspx",
        get_settings(),
        fetch,
    )
    assert failure is None
    assert html == b""
    assert final_url.endswith("/1126771984/detail.aspx")
    assert draft["title"] == "Cardigan"
    assert draft["image_url"].endswith("/images/big/1.webp")
    assert any(url.endswith("/images/big/1.jpg") for url in draft["image_urls"])
    assert not any("wildberries.ru/catalog" in url for url in calls)
