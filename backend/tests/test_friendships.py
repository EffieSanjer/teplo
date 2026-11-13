from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.infrastructure.database import FriendInvitation, Friendship, Membership, utcnow
from src.integrations.telegram.bot import invitation_path
from src.main import app
from src.config import get_settings
from src.modules.auth import service as auth_service
from test_private_telegram import add_group
from test_private_telegram import login, private_settings as private_login_settings  # noqa: F401
from test_media import photo


def invite(client):
    response = client.post("/api/v1/friends/invitations")
    assert response.status_code == 201, response.text
    payload = parse_qs(urlsplit(response.json()["url"]).query)["start"][0]
    assert len(payload) <= 64
    assert payload.startswith("friend_")
    return payload.removeprefix("friend_")


@pytest.fixture
def people(db, private_login_settings, monkeypatch):  # noqa: F811
    monkeypatch.setattr(private_login_settings, "telegram_bot_username", "test_wishlist_bot")
    with TestClient(app, headers={"Origin": "http://testserver"}) as a, TestClient(
        app, headers={"Origin": "http://testserver"}
    ) as b, TestClient(app, headers={"Origin": "http://testserver"}) as c:
        aa = login(a, private_login_settings, 123)
        bb = login(b, private_login_settings, 456)
        cc = login(c, private_login_settings, 789)
        yield a, b, c, aa, bb, cc


def test_invitation_explicit_mutual_access_and_immediate_revocation(db, people):
    a, b, c, aa, bb, _ = people
    uid, bid = aa["user"]["id"], bb["user"]["id"]
    mid = a.post("/api/v1/media", files={"file": ("photo.png", photo(), "image/png")}).json()["id"]
    wish = a.post("/api/v1/items", json={
        "recipient_id": uid, "list_type": "wishlist", "item_type": "idea", "title": "Желание", "image_id": mid,
    }).json()
    token = invite(a)
    assert token not in db.scalar(select(FriendInvitation)).token_hash
    assert a.get(f"/api/v1/friends/invitations/{token}").json()["own"] is True
    assert a.post("/api/v1/friends/accept", json={"token": token}).status_code == 409
    preview = b.get(f"/api/v1/friends/invitations/{token}")
    assert preview.status_code == 200
    assert preview.json()["inviter"]["id"] == uid
    assert b.get(f"/api/v1/items/{wish['id']}").status_code == 404
    assert b.get("/api/v1/users").json() == []
    assert db.scalar(select(Friendship)) is None
    assert b.post("/api/v1/friends/accept", json={"token": token}).status_code == 200
    assert b.get("/api/v1/users").json()[0]["id"] == uid
    assert a.get("/api/v1/users").json()[0]["id"] == bid
    assert b.get(f"/api/v1/users/{uid}").json()["can_surprise"] is True
    assert b.get(f"/api/v1/items/{wish['id']}").status_code == 200
    assert b.get(f"/api/v1/users/{uid}/items/wishlist").json()[0]["id"] == wish["id"]
    assert b.get(f"/api/v1/media/{mid}").status_code == 200
    for outsider in (b, c):
        assert outsider.post("/api/v1/friends/accept", json={"token": token}).status_code == 404
    assert c.get(f"/api/v1/users/{uid}").status_code == 404
    assert c.get(f"/api/v1/media/{mid}").status_code == 404
    assert c.get("/api/v1/users").json() == []
    assert b.put(f"/api/v1/items/{wish['id']}", json={"item_type": "idea", "title": "Чужое"}).status_code == 404
    assert b.delete(f"/api/v1/items/{wish['id']}").status_code == 404
    assert b.post(f"/api/v1/items/{wish['id']}/archive", json={"archived": True}).status_code == 404
    assert b.post(f"/api/v1/items/{wish['id']}/surprise").status_code == 201
    assert b.get(f"/api/v1/users/{uid}/items/surprise").status_code == 200
    assert b.post("/api/v1/items", json={
        "recipient_id": uid, "list_type": "surprise", "item_type": "idea", "title": "Секрет",
    }).status_code == 201
    assert db.get(Membership, (aa["community_id"], bid)) is None
    assert b.delete(f"/api/v1/friends/{uid}").status_code == 204
    assert a.get("/api/v1/users").json() == b.get("/api/v1/users").json() == []
    assert b.get(f"/api/v1/items/{wish['id']}").status_code == 404
    assert b.get(f"/api/v1/media/{mid}").status_code == 404
    assert b.get(f"/api/v1/users/{uid}").status_code == 404
    assert a.get(f"/api/v1/items/{wish['id']}").status_code == 200


def test_revoked_replaced_expired_and_invalid_links(db, people):
    a, b, _, _, _, _ = people
    old = invite(a)
    new = invite(a)
    assert b.get(f"/api/v1/friends/invitations/{old}").status_code == 404
    assert b.post("/api/v1/friends/accept", json={"token": old}).status_code == 404
    db.scalar(select(FriendInvitation)).expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert b.post("/api/v1/friends/accept", json={"token": new}).status_code == 404
    new = invite(a)
    assert a.delete("/api/v1/friends/invitations").status_code == 204
    assert b.get(f"/api/v1/friends/invitations/{new}").status_code == 404
    assert b.post("/api/v1/friends/accept", json={"token": "forged"}).status_code == 422
    assert b.get("/api/v1/friends/invitations/forged").status_code == 404


def test_friendship_not_transitive_and_duplicate_pair_is_safe(db, people):
    a, b, c, aa, bb, cc = people
    assert b.post("/api/v1/friends/accept", json={"token": invite(a)}).status_code == 200
    assert a.post("/api/v1/friends/accept", json={"token": invite(b)}).status_code == 200
    assert len(db.scalars(select(Friendship)).all()) == 1
    assert c.post("/api/v1/friends/accept", json={"token": invite(b)}).status_code == 200
    assert c.get(f"/api/v1/users/{aa['user']['id']}").status_code == 404
    assert a.get(f"/api/v1/users/{cc['user']['id']}").status_code == 404
    assert [u["id"] for u in a.get("/api/v1/users").json()] == [bb["user"]["id"]]


def test_invites_require_authentication_origin_and_csrf(people):
    a, b, _, _, _, _ = people
    token = invite(a)
    csrf = b.headers.pop("X-CSRF-Token")
    assert b.post("/api/v1/friends/accept", json={"token": token}).status_code == 403
    assert b.post("/api/v1/friends/invitations").status_code == 403
    b.headers["X-CSRF-Token"] = csrf
    assert b.post("/api/v1/friends/accept", json={"token": token}, headers={"Origin": "https://evil.test"}).status_code == 403
    with TestClient(app) as anon:
        assert anon.get(f"/api/v1/friends/invitations/{token}").status_code == 401
    assert b.post("/api/v1/friends/accept", json={"token": token}).status_code == 200


def test_bot_invitation_path_is_strict():
    token = "a" * 43
    assert invitation_path("/start friend_" + token) == "/friends?invite=" + token
    assert invitation_path("/start@test_bot friend_" + token) == "/friends?invite=" + token
    for invalid in (None, "/start", "/start friend_bad", "/start friend_" + token + "&evil=1"):
        assert invitation_path(invalid) is None


def test_friendship_never_exposes_group_surprises_or_their_media(db, people, monkeypatch):
    a, b, c, _, _, _ = people
    settings = get_settings()
    add_group(db, settings, monkeypatch)
    monkeypatch.setattr(auth_service, "check_membership", lambda *args: True)
    login(a, settings, 123)
    recipient = login(b, settings, 456)["user"]["id"]
    mid = a.post("/api/v1/media", files={"file": ("photo.png", photo(), "image/png")}).json()["id"]
    surprise = a.post("/api/v1/items", json={
        "recipient_id": recipient, "list_type": "surprise", "item_type": "idea", "title": "Секрет", "image_id": mid,
    }).json()
    assert c.post("/api/v1/friends/accept", json={"token": invite(b)}).status_code == 200
    assert c.get(f"/api/v1/users/{recipient}").status_code == 200
    assert c.get(f"/api/v1/items/{surprise['id']}").status_code == 404
    assert c.get(f"/api/v1/media/{mid}").status_code == 404
    assert c.get(f"/api/v1/users/{recipient}/items/surprise").json() == []
    assert b.get(f"/api/v1/items/{surprise['id']}").status_code == 404
    assert b.get(f"/api/v1/media/{mid}").status_code == 404
    # Group access is independent of explicit friendship.
    assert b.post("/api/v1/friends/accept", json={"token": invite(a)}).status_code == 200
    assert a.delete(f"/api/v1/friends/{recipient}").status_code == 204
    assert a.get(f"/api/v1/users/{recipient}").json()["is_friend"] is False
    assert a.get(f"/api/v1/users/{recipient}").json()["can_surprise"] is True
    assert a.get(f"/api/v1/items/{surprise['id']}").status_code == 200
