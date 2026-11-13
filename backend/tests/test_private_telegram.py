import json
from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from src.cli import LOCAL_COMMUNITY, REAL_COMMUNITY, configure_telegram
from src.config import Settings, get_settings
from src.infrastructure.database import (
    AuthIdentity, Community, CommunityIntegration, Membership, PersonalWorkspace, User, utcnow,
)
from src.main import app
from src.modules.auth import service
from src.modules.communities import service as communities
from test_auth import signed_data
from test_media import photo


@pytest.fixture
def private_settings(db, monkeypatch):
    settings = get_settings()
    for key, value in {
        "dev_login_enabled": False,
        "telegram_mode": "polling",
        "telegram_bot_token": "123:secret",
        "telegram_chat_id": None,
        "telegram_allow_private_login": True,
    }.items():
        monkeypatch.setattr(settings, key, value)

    def unexpected(*args):
        raise AssertionError("Personal workspaces must not request group membership")

    monkeypatch.setattr(service, "check_membership", unexpected)
    monkeypatch.setattr(communities, "check_membership", unexpected)
    return settings


def login(client, settings, telegram_id=123):
    raw = signed_data(settings, user=json.dumps({"id": telegram_id, "first_name": "Личный"}))
    response = client.post("/api/v1/auth/telegram", json={"init_data": raw})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()


def test_private_settings_without_group():
    settings = Settings(
        dev_login_enabled=False, telegram_mode="polling", telegram_bot_token="123:secret",
        telegram_chat_id=None, telegram_allow_private_login=True,
    )
    assert settings.telegram_chat_id is None
    with pytest.raises(ValidationError):
        Settings(
            dev_login_enabled=False, telegram_mode="polling", telegram_bot_token="123:secret",
            telegram_chat_id=None, telegram_allow_private_login=False,
        )
    with pytest.raises(ValidationError):
        Settings(dev_login_enabled=False, telegram_mode="polling", telegram_bot_token="")


def test_private_login_crud_media_isolation_and_reentry(db, private_settings):
    settings = private_settings
    with TestClient(app, headers={"Origin": "http://testserver"}) as first, TestClient(
        app, headers={"Origin": "http://testserver"}
    ) as second:
        a = login(first, settings)
        b = login(second, settings, 456)
        uid = a["user"]["id"]
        assert a["community_id"] != b["community_id"]
        assert a["community_id"] not in {LOCAL_COMMUNITY, REAL_COMMUNITY}
        assert db.get(PersonalWorkspace, a["community_id"]).user_id == uid
        assert first.get("/api/v1/users").json() == []
        media = first.post("/api/v1/media", files={"file": ("photo.png", photo(), "image/png")})
        assert media.status_code == 201
        mid = media.json()["id"]
        response = first.post("/api/v1/items", json={
            "list_type": "wishlist", "recipient_id": uid, "item_type": "idea",
            "title": "Личное желание", "image_id": mid,
        })
        assert response.status_code == 201
        item = response.json()
        assert first.get(f"/api/v1/media/{mid}").status_code == 200
        assert second.get(f"/api/v1/media/{mid}").status_code == 404
        assert second.get(f"/api/v1/users/{uid}").status_code == 404
        assert second.get(f"/api/v1/users/{uid}/items/wishlist").status_code == 404
        assert second.get(f"/api/v1/items/{item['id']}").status_code == 404
        assert second.post(f"/api/v1/items/{item['id']}/surprise").status_code == 404
        assert second.post("/api/v1/items", json={
            "list_type": "surprise", "recipient_id": uid, "item_type": "idea", "title": "Нет",
        }).status_code == 404
        member = db.get(Membership, (a["community_id"], uid))
        member.checked_at = utcnow() - timedelta(days=1)
        db.commit()
        assert first.get("/api/v1/auth/session").status_code == 200
        assert first.get(f"/api/v1/users/{uid}/items/wishlist").json()[0]["id"] == item["id"]
        assert first.post(f"/api/v1/items/{item['id']}/archive", json={"archived": True}).status_code == 200
        again = login(first, settings)
        assert again["user"]["id"] == uid
        assert again["community_id"] == a["community_id"]
        assert first.delete(f"/api/v1/items/{item['id']}").status_code == 204
        assert first.get(f"/api/v1/items/{item['id']}").status_code == 404


def test_private_login_in_webview_cross_site_context(db, private_settings):
    with TestClient(app, headers={
        "Origin": "http://testserver", "Sec-Fetch-Site": "cross-site",
        "X-Wishlist-Request": "same-origin",
    }) as client:
        current = login(client, private_settings)
        assert client.get("/api/v1/auth/session").status_code == 200
        created = client.post("/api/v1/items", json={
            "list_type": "wishlist", "recipient_id": current["user"]["id"],
            "item_type": "idea", "title": "WebView",
        })
        assert created.status_code == 201
        client.headers.pop("Origin")
        assert client.get("/api/v1/auth/session").status_code == 200
        assert client.get(f"/api/v1/items/{created.json()['id']}").status_code == 200


def add_group(db, settings, monkeypatch):
    monkeypatch.setattr(settings, "telegram_chat_id", -100123)
    db.add(Community(id=REAL_COMMUNITY, name="Общее пространство"))
    db.flush()
    db.add(CommunityIntegration(community_id=REAL_COMMUNITY, telegram_chat_id=-100123))
    db.commit()


@pytest.mark.parametrize("unavailable", [False, True])
def test_failed_group_check_only_grants_private_access(db, private_settings, monkeypatch, unavailable):
    settings = private_settings
    add_group(db, settings, monkeypatch)

    def check(*args):
        if unavailable:
            raise HTTPException(503, "Недоступно")
        return False

    monkeypatch.setattr(service, "check_membership", check)
    user, community_id = service.telegram_login(db, signed_data(settings), settings)
    assert db.get(PersonalWorkspace, community_id).user_id == user.id
    assert db.get(Membership, (REAL_COMMUNITY, user.id)) is None


def test_group_only_mode_still_fails_closed_on_unavailable_check(db, private_settings, monkeypatch):
    settings = private_settings
    add_group(db, settings, monkeypatch)
    monkeypatch.setattr(settings, "telegram_allow_private_login", False)

    def unavailable(*args):
        raise HTTPException(503, "Недоступно")

    monkeypatch.setattr(service, "check_membership", unavailable)
    with pytest.raises(HTTPException) as exc:
        service.telegram_login(db, signed_data(settings), settings)
    assert exc.value.status_code == 503
    assert db.scalar(select(PersonalWorkspace)) is None


def test_private_user_cannot_read_group_wishes_media_or_surprises(db, private_settings, monkeypatch):
    settings = private_settings
    add_group(db, settings, monkeypatch)
    monkeypatch.setattr(service, "check_membership", lambda *args: True)
    with TestClient(app, headers={"Origin": "http://testserver"}) as group, TestClient(
        app, headers={"Origin": "http://testserver"}
    ) as recipient, TestClient(app, headers={"Origin": "http://testserver"}) as private:
        owner = login(group, settings)
        friend = login(recipient, settings, 789)
        media = group.post("/api/v1/media", files={"file": ("photo.png", photo(), "image/png")}).json()
        wish = group.post("/api/v1/items", json={
            "list_type": "wishlist", "recipient_id": owner["user"]["id"],
            "item_type": "idea", "title": "В группе", "image_id": media["id"],
        }).json()
        surprise = group.post("/api/v1/items", json={
            "list_type": "surprise", "recipient_id": friend["user"]["id"],
            "item_type": "idea", "title": "Секрет",
        }).json()
        monkeypatch.setattr(service, "check_membership", lambda *args: False)
        login(private, settings, 456)
        assert private.get("/api/v1/users").json() == []
        assert private.get(f"/api/v1/items/{wish['id']}").status_code == 404
        assert private.get(f"/api/v1/media/{media['id']}").status_code == 404
        assert private.get(f"/api/v1/items/{surprise['id']}").status_code == 404
        assert private.get(f"/api/v1/users/{friend['user']['id']}/items/surprise").status_code == 404


def test_transition_to_group_preserves_personal_wishes_and_group_revocation(db, private_settings, monkeypatch):
    settings = private_settings
    with TestClient(app, headers={"Origin": "http://testserver"}) as client:
        a = login(client, settings)
        uid = a["user"]["id"]
        item = client.post("/api/v1/items", json={
            "list_type": "wishlist", "recipient_id": uid, "item_type": "idea", "title": "Сохранить",
        }).json()
        add_group(db, settings, monkeypatch)
        monkeypatch.setattr(service, "check_membership", lambda *args: True)
        b = login(client, settings)
        assert b["user"]["id"] == uid
        assert b["community_id"] == REAL_COMMUNITY
        assert client.get(f"/api/v1/items/{item['id']}").status_code == 200
        group_member = db.get(Membership, (REAL_COMMUNITY, uid))
        group_member.checked_at = utcnow() - timedelta(days=1)
        db.commit()
        monkeypatch.setattr(communities, "check_membership", lambda *args: False)
        # Existing group sessions do not silently fall back after revocation.
        assert client.get("/api/v1/auth/session").status_code == 403
        monkeypatch.setattr(service, "check_membership", lambda *args: False)
        c = login(client, settings)
        assert c["community_id"] == a["community_id"]
        assert client.get(f"/api/v1/items/{item['id']}").status_code == 200


def test_private_scope_cannot_reuse_group_demo_or_other_owner_session(db, private_settings, login_as, monkeypatch):
    settings = private_settings
    user, cid = service.telegram_login(db, signed_data(settings), settings)
    assert login_as(user.id, LOCAL_COMMUNITY).get("/api/v1/auth/session").status_code == 403
    other, _ = service.telegram_login(db, signed_data(
        settings, user=json.dumps({"id": 456, "first_name": "Другой"})
    ), settings)
    db.add(Membership(community_id=cid, user_id=other.id))
    db.commit()
    assert login_as(other.id, cid).get("/api/v1/auth/session").status_code == 403
    own = login_as(user.id, cid)
    monkeypatch.setattr(settings, "telegram_allow_private_login", False)
    assert own.get("/api/v1/auth/session").status_code == 403


def test_invalid_init_data_never_creates_private_user(db, private_settings):
    before = len(db.scalars(select(User)).all())
    with pytest.raises(HTTPException) as exc:
        service.telegram_login(db, "user=forged", private_settings)
    assert exc.value.status_code == 401
    assert len(db.scalars(select(User)).all()) == before
    assert db.scalar(select(PersonalWorkspace)) is None
    assert db.scalar(select(AuthIdentity)) is None


def test_configure_private_mode_does_not_modify_demo(db, private_settings):
    configure_telegram(db)
    assert db.get(Community, LOCAL_COMMUNITY) is not None
    assert db.get(Community, REAL_COMMUNITY) is None
