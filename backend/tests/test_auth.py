import hashlib
import hmac
import json
import time
from datetime import timedelta
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.config import Settings, get_settings
from src.infrastructure.database import AuthSession, utcnow
from src.main import app
from src.modules.auth.service import verify_init_data


def signed_data(settings, **changes):
    data = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": 123, "first_name": "Аня"}),
        "query_id": "abc",
    } | changes
    secret = hmac.new(b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(
        secret, "\n".join(f"{k}={v}" for k, v in sorted(data.items())).encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(data)


def test_init_data():
    settings = get_settings().model_copy(update={"telegram_bot_token": "123:secret"})
    raw = signed_data(settings)
    assert verify_init_data(raw, settings)["id"] == 123
    for invalid in [
        raw.replace("hash=", "hash=0"),
        raw + "&auth_date=1",
        signed_data(settings, auth_date="1"),
        signed_data(settings, auth_date=str(int(time.time()) + 100)),
        signed_data(settings, user='{"id":"123"}'),
    ]:
        with pytest.raises(HTTPException) as exc:
            verify_init_data(invalid, settings)
        assert exc.value.status_code == 401


def test_production_dev_login_rejected():
    with pytest.raises(ValidationError):
        Settings(app_env="production", dev_login_enabled=True, public_base_url="https://example.com")
    with pytest.raises(ValidationError):
        Settings(dev_login_enabled=True, public_base_url="https://public.example.com")
    with pytest.raises(ValidationError):
        Settings(
            dev_login_enabled=True, telegram_mode="polling", telegram_bot_token="123", telegram_chat_id=-100
        )


def test_origin_csrf_and_cookie(client):
    assert client.post("/api/v1/items", json={}, headers={"Origin": "https://evil.test"}).status_code == 403
    client.headers.pop("X-CSRF-Token")
    assert client.post("/api/v1/items", json={}).status_code == 403
    assert client.get("/api/v1/auth/session").status_code == 200
    result = client.post("/api/v1/auth/dev")
    cookie = result.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert result.headers["cache-control"] == "private, no-store"
    assert "x-request-id" in result.headers
    client.headers.pop("Origin")
    assert client.post("/api/v1/auth/dev").status_code == 403


def test_host_and_anonymous(db):
    with TestClient(app, base_url="http://evil.test") as client:
        assert client.get("/api/v1/users").status_code == 400
    with TestClient(app, base_url="http://testserver") as client:
        assert client.get("/api/v1/users").status_code == 401
        assert client.get("/api/v1/media/unknown").status_code == 401


def test_expired_session_and_logout(client, db):
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/session").status_code == 401
    client.post("/api/v1/auth/dev")
    from sqlalchemy import select

    for session in db.scalars(select(AuthSession)):
        session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.get("/api/v1/auth/session").status_code == 401


def test_dev_login_cannot_select_identity(client):
    result = client.post("/api/v1/auth/dev", json={"user_id": "33333333-3333-4333-8333-333333333333"})
    assert result.json()["user"]["id"] == get_settings().dev_user_id


def test_validation_omits_private_input(client):
    result = client.post("/api/v1/auth/telegram", json={"init_data": "x" * 17000})
    assert result.status_code == 422
    assert "xxxxxx" not in result.text


def test_login_rate_limit(client):
    for _ in range(25):
        result = client.post("/api/v1/auth/dev")
    assert result.status_code == 429


def test_membership_expiry_fail_closed(client, db, monkeypatch):
    from src.cli import LOCAL_COMMUNITY
    from src.infrastructure.database import AuthIdentity, CommunityIntegration, Membership
    from src.modules.communities import service

    uid = get_settings().dev_user_id
    db.add(CommunityIntegration(community_id=LOCAL_COMMUNITY, telegram_chat_id=-123))
    db.add(AuthIdentity(user_id=uid, provider="telegram", provider_user_id="123"))
    member = db.get(Membership, (LOCAL_COMMUNITY, uid))
    member.checked_at = utcnow() - timedelta(hours=1)
    db.commit()

    def unavailable(*args):
        raise HTTPException(503, "Недоступно")

    monkeypatch.setattr(service, "check_membership", unavailable)
    assert client.get("/api/v1/users").status_code == 503
    monkeypatch.setattr(service, "check_membership", lambda *args: False)
    assert client.get("/api/v1/users").status_code == 403
    assert member.status == "left"
