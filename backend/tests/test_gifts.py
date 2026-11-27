import pytest
from sqlalchemy import select

from src.cli import LOCAL_COMMUNITY
from src.config import get_settings
from src.infrastructure.database import Community, Item, Membership, User

ROOT = "/api/v1"


def create(client, **changes):
    payload = {
        "item_type": "idea",
        "title": "Тёплые носки",
        "list_type": "wishlist",
        "recipient_id": get_settings().dev_user_id,
    }
    return client.post(ROOT + "/items", json=payload | changes)


def test_crud_archive_and_decimal(client):
    result = create(client, price="1234.50", currency="RUB")
    assert result.status_code == 201
    item = result.json()
    assert item["price"] == "1234.50"
    assert item["can_manage"] is True
    item_id = item["id"]
    assert (
        client.put(
            f"{ROOT}/items/{item_id}",
            json={
                "item_type": "gift",
                "url": "https://example.com/product",
                "description": "Без названия",
            },
        ).status_code
        == 200
    )
    assert client.post(f"{ROOT}/items/{item_id}/archive", json={"archived": True}).json()["archived_at"]
    assert (
        client.put(f"{ROOT}/items/{item_id}", json={"item_type": "idea", "title": "Новое"}).status_code == 409
    )
    assert (
        client.post(f"{ROOT}/items/{item_id}/archive", json={"archived": False}).json()["archived_at"] is None
    )
    assert client.delete(f"{ROOT}/items/{item_id}").status_code == 204
    assert client.get(f"{ROOT}/items/{item_id}").status_code == 404


@pytest.mark.parametrize(
    "changes",
    [
        {"title": " "},
        {"item_type": "gift"},
        {"price": "-1", "currency": "RUB"},
        {"price": "1"},
        {"price": "0.001", "currency": "RUB"},
        {"url": "javascript:alert(1)"},
        {"url": "https://user:secret@example.com"},
        {"title": "a" * 201},
        {"price": "NaN", "currency": "RUB"},
        {"item_type": "certificate", "url": None},
        {"item_type": "ticket", "url": None},
        {"price_mode": "unknown"},
    ],
)
def test_validation(client, changes):
    assert create(client, **changes).status_code == 422


def test_ticket_crud(client):
    result = create(
        client,
        item_type="ticket",
        url="https://theatre.example/show/1",
        title="Спектакль",
    )
    assert result.status_code == 201
    item = result.json()
    assert item["item_type"] == "ticket"
    assert item["url"] == "https://theatre.example/show/1"
    assert item["title"] == "Спектакль"


def test_null_price_and_zero(client):
    assert create(client).json()["price"] is None
    assert create(client, price="0", currency="USD").json()["price"] == "0.00"


def test_certificate_crud_and_privacy(client, friend_id, login_as):
    recipient = login_as(friend_id)
    source = recipient.post(
        ROOT + "/items",
        json={
            "recipient_id": friend_id, "list_type": "wishlist", "item_type": "certificate",
            "url": "https://example.com/shop", "price": "1000", "currency": "RUB", "price_mode": "from",
        },
    )
    assert source.status_code == 201
    item = source.json()
    assert item["item_type"] == "certificate"
    assert item["price_mode"] == "from"
    assert client.post(f"{ROOT}/items/{item['id']}/surprise").status_code == 404
    copied = create(client, recipient_id=friend_id, list_type="surprise", item_type="certificate",
                    url="https://example.com/shop", price="1000", currency="RUB", price_mode="from").json()
    assert copied["price_mode"] == "from"
    assert copied["item_type"] == "certificate"
    assert recipient.get(f"{ROOT}/items/{copied['id']}").status_code == 404
    assert client.post(f"{ROOT}/items/{copied['id']}/archive", json={"archived": True}).status_code == 200
    assert client.delete(f"{ROOT}/items/{copied['id']}").status_code == 204
    assert recipient.get(f"{ROOT}/items/{item['id']}").json()["price_mode"] == "from"


@pytest.mark.parametrize("url", [
    "https://t.me/finds/123", "https://www.instagram.com/p/abc/",
    "https://pin.it/abc", "https://www.pinterest.com/pin/123/",
])
def test_social_links_can_be_saved_without_metadata(client, url):
    result = create(client, item_type="gift", url=url, title=None)
    assert result.status_code == 201
    assert result.json()["url"] == url
    assert result.json()["price_mode"] == "exact"


def test_own_surprises_are_inaccessible(client, db):
    uid = get_settings().dev_user_id
    surprise = db.scalar(select(Item).where(Item.recipient_id == uid, Item.list_type == "surprise"))
    assert client.get(f"{ROOT}/users/{uid}/items/surprise").status_code == 404
    assert client.get(f"{ROOT}/items/{surprise.id}").json() == {"detail": "Не найдено"}
    for method, path, data in [
        (
            "post",
            "/items",
            {"recipient_id": uid, "list_type": "surprise", "item_type": "idea", "title": "Себе"},
        ),
        ("post", f"/items/{surprise.id}/archive", {"archived": True}),
        ("put", f"/items/{surprise.id}", {"item_type": "idea", "title": "Чужое"}),
    ]:
        assert getattr(client, method)(ROOT + path, json=data).status_code == 404
    assert client.delete(f"{ROOT}/items/{surprise.id}").status_code == 404
    surprise.archived_at = surprise.created_at
    db.commit()
    assert client.get(f"{ROOT}/items/{surprise.id}").status_code == 404


def test_only_author_manages(client, friend_id, login_as):
    result = create(client, recipient_id=friend_id, list_type="surprise")
    assert result.status_code == 201
    item_id = result.json()["id"]
    from src.cli import FRIENDS

    other = login_as(FRIENDS[1][0])
    assert other.get(f"{ROOT}/items/{item_id}").status_code == 200
    assert other.get(f"{ROOT}/items/{item_id}").json()["can_manage"] is False
    assert other.delete(f"{ROOT}/items/{item_id}").status_code == 404
    assert create(client, recipient_id=friend_id).status_code == 404
    recipient = login_as(friend_id)
    assert recipient.get(f"{ROOT}/items/{item_id}").status_code == 404


def test_copy_is_no_longer_available(client, db, friend_id):
    source = db.scalar(select(Item).where(Item.recipient_id == friend_id, Item.list_type == "wishlist"))
    assert client.post(f"{ROOT}/items/{source.id}/surprise").status_code == 404
    db.refresh(source)
    assert source.archived_at is None


def test_sorting(client):
    first = create(client, title="Первое").json()
    second = create(client, title="Второе").json()
    uid = get_settings().dev_user_id
    data = client.get(f"{ROOT}/users/{uid}/items/wishlist").json()
    assert [row["id"] for row in data][:2] == [second["id"], first["id"]]
    client.post(f"{ROOT}/items/{second['id']}/archive", json={"archived": True})
    data = client.get(f"{ROOT}/users/{uid}/items/wishlist").json()
    archived = [row for row in data if row["archived_at"]]
    assert archived[0]["id"] == second["id"]
    flags = [row["archived_at"] is not None for row in data]
    assert flags == sorted(flags)


def test_leaving_revokes_author_access(client, db, friend_id):
    item_id = create(client, recipient_id=friend_id, list_type="surprise").json()["id"]
    db.get(Membership, (LOCAL_COMMUNITY, get_settings().dev_user_id)).status = "left"
    db.commit()
    assert client.get(f"{ROOT}/items/{item_id}").status_code == 403


def test_community_isolation(client, db, friend_id, login_as):
    item_id = create(client, recipient_id=friend_id, list_type="surprise").json()["id"]
    second = Community(name="Другая компания")
    db.add(second)
    db.flush()
    for uid in [get_settings().dev_user_id, friend_id]:
        db.add(Membership(community_id=second.id, user_id=uid))
    db.commit()
    other = login_as(get_settings().dev_user_id, second.id)
    assert other.get(f"{ROOT}/items/{item_id}").status_code == 404
    assert other.get(f"{ROOT}/users/{friend_id}/items/surprise").json() == []
    assert other.get(f"{ROOT}/users/{friend_id}/items/wishlist").status_code == 200


def test_outsider_cannot_read(client, db, login_as, friend_id):
    user = User(display_name="Посторонний")
    db.add(user)
    db.commit()
    outsider = login_as(user.id)
    assert outsider.get(ROOT + "/users").status_code == 403


def test_seed_repeatable(db):
    from src.cli import seed

    before = len(db.scalars(select(Item)).all())
    seed(db)
    assert len(db.scalars(select(Item)).all()) == before


def test_database_constraints(db):
    from sqlalchemy.exc import IntegrityError

    invalid = Item(
        recipient_id=get_settings().dev_user_id,
        author_id=get_settings().dev_user_id,
        list_type="surprise",
        community_id=LOCAL_COMMUNITY,
        item_type="idea",
        title="Нельзя",
    )
    db.add(invalid)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
