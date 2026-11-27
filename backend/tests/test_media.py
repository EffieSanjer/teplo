import io
from datetime import timedelta

import pytest
from PIL import Image

from src.cli import FRIENDS
from src.config import get_settings
from src.infrastructure.database import Media, utcnow
from src.modules.media.service import cleanup
from src.modules.media import routes
from src.integrations.product_metadata.network import FetchError

ROOT = "/api/v1"


def photo():
    output = io.BytesIO()
    Image.new("RGB", (32, 32), (180, 120, 70)).save(output, "PNG")
    return output.getvalue()


def upload(client):
    return client.post(ROOT + "/media", files={"file": ("photo.png", photo(), "image/png")})


def test_upload_validation(client):
    for data, content_type in [(b"not a photo", "image/png"), (b"<svg></svg>", "image/svg+xml")]:
        result = client.post(ROOT + "/media", files={"file": ("photo.png", data, content_type)})
        assert result.status_code == 422
    result = client.post(ROOT + "/media", files={"file": ("big.png", b"x" * (5242880 + 1), "image/png")})
    assert result.status_code == 413


def test_unattached_private_and_reencoded(client, login_as, friend_id):
    result = upload(client)
    assert result.status_code == 201
    media_id = result.json()["id"]
    response = client.get(f"{ROOT}/media/{media_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "private, max-age=604800, stale-while-revalidate=86400"
    card = client.get(f"{ROOT}/media/{media_id}?w=400")
    assert card.status_code == 200
    assert card.headers["content-type"] == "image/jpeg"
    assert len(card.content) <= len(response.content)
    other = login_as(friend_id)
    assert other.get(f"{ROOT}/media/{media_id}").status_code == 404


def test_surprise_photo_hidden_even_in_archive(client, friend_id, login_as):
    media_id = upload(client).json()["id"]
    item = client.post(
        ROOT + "/items",
        json={
            "list_type": "surprise",
            "recipient_id": friend_id,
            "item_type": "idea",
            "title": "Сюрприз",
            "image_id": media_id,
        },
    ).json()
    recipient = login_as(friend_id)
    other = login_as(FRIENDS[1][0])
    assert recipient.get(f"{ROOT}/media/{media_id}").status_code == 404
    assert other.get(f"{ROOT}/media/{media_id}").status_code == 200
    client.post(f"{ROOT}/items/{item['id']}/archive", json={"archived": True})
    assert recipient.get(f"{ROOT}/media/{media_id}").status_code == 404
    client.delete(f"{ROOT}/items/{item['id']}")
    assert client.get(f"{ROOT}/media/{media_id}").status_code == 404


def test_cannot_attach_someone_elses_upload(client, friend_id, login_as):
    friend = login_as(friend_id)
    media_id = upload(friend).json()["id"]
    result = client.post(
        ROOT + "/items",
        json={
            "list_type": "wishlist",
            "recipient_id": get_settings().dev_user_id,
            "item_type": "idea",
            "title": "Фото",
            "image_id": media_id,
        },
    )
    assert result.status_code == 404


def test_cleanup_only_unreferenced(client, db):
    media_id = upload(client).json()["id"]
    media = db.get(Media, media_id)
    media.created_at = utcnow() - timedelta(days=2)
    db.commit()
    assert cleanup(db, get_settings()) == 1
    assert not (get_settings().media_root / media.storage_key).exists()
    assert client.get(f"{ROOT}/media/{media_id}").status_code == 404


def test_image_from_url_is_stored_privately(client, monkeypatch, login_as, friend_id):
    calls = []

    def fetch(url, max_bytes, timeout):
        calls.append((url, max_bytes, timeout))
        return photo(), "application/octet-stream", url

    monkeypatch.setattr(routes, "fetch_public", fetch)
    result = client.post(ROOT + "/media/from-url", json={"url": " https://example.com/photo "})
    assert result.status_code == 201
    media_id = result.json()["id"]
    assert calls == [("https://example.com/photo", get_settings().max_upload_bytes,
                      get_settings().metadata_timeout_seconds)]
    image = client.get(f"{ROOT}/media/{media_id}")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"
    assert login_as(friend_id).get(f"{ROOT}/media/{media_id}").status_code == 404
    item = client.post(ROOT + "/items", json={
        "list_type": "surprise", "recipient_id": friend_id, "item_type": "idea",
        "title": "Фото по ссылке", "image_id": media_id,
    })
    assert item.status_code == 201
    assert login_as(friend_id).get(f"{ROOT}/media/{media_id}").status_code == 404


@pytest.mark.parametrize("data,status", [(b"<html>Not an image</html>", 422),
                                        (b"<svg></svg>", 422), (b"x" * 5242881, 413)])
def test_image_url_validates_actual_content(client, monkeypatch, data, status):
    monkeypatch.setattr(routes, "fetch_public", lambda *args: (data, "image/jpeg", "https://example.com"))
    assert client.post(ROOT + "/media/from-url", json={"url": "https://example.com/photo.jpg"}).status_code == status


@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)",
                                  "https://user:secret@example.com/photo", ""])
def test_image_url_rejects_invalid_urls(client, monkeypatch, url):
    def unexpected(*args):
        pytest.fail("Invalid URL must not be fetched")

    monkeypatch.setattr(routes, "fetch_public", unexpected)
    assert client.post(ROOT + "/media/from-url", json={"url": url}).status_code == 422


def test_image_url_blocks_private_network(client):
    result = client.post(ROOT + "/media/from-url", json={"url": "http://127.0.0.1/photo.jpg"})
    assert result.status_code == 422
    assert "Недопустимый адрес" in result.json()["detail"]


def test_image_url_network_failure_releases_slot(client, monkeypatch):
    def failed(*args):
        raise FetchError("Сайт не ответил вовремя")

    monkeypatch.setattr(routes, "fetch_public", failed)
    for _ in range(4):
        result = client.post(ROOT + "/media/from-url", json={"url": "https://example.com/photo"})
        assert result.status_code == 422
        assert result.json()["detail"] == "Сайт не ответил вовремя"


def test_image_url_requires_csrf(client, monkeypatch):
    def unexpected(*args):
        pytest.fail("Unauthorized request must not fetch an image")

    monkeypatch.setattr(routes, "fetch_public", unexpected)
    client.headers.pop("X-CSRF-Token")
    assert client.post(ROOT + "/media/from-url", json={"url": "https://example.com/photo"}).status_code == 403


def test_image_url_shares_upload_limit(client, monkeypatch):
    monkeypatch.setattr(routes, "fetch_public", lambda *args: (photo(), "image/png", "https://example.com"))
    for _ in range(15):
        assert upload(client).status_code == 201
    assert client.post(ROOT + "/media/from-url", json={"url": "https://example.com/photo"}).status_code == 429
