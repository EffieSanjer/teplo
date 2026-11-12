import json

from fastapi import HTTPException
from sqlalchemy import select

from src.cli import REAL_COMMUNITY
from src.config import get_settings
from src.infrastructure.database import AuthIdentity, Community, CommunityIntegration, Membership, User
from src.modules.auth import service
from test_auth import signed_data


def test_telegram_registration_and_reentry(db, monkeypatch):
    settings = get_settings().model_copy(
        update={
            "dev_login_enabled": False,
            "telegram_mode": "polling",
            "telegram_bot_token": "123:secret",
            "telegram_chat_id": -100123,
        }
    )
    db.add(Community(id=REAL_COMMUNITY, name="Реальные друзья"))
    db.flush()
    db.add(CommunityIntegration(community_id=REAL_COMMUNITY, telegram_chat_id=-100123))
    db.commit()
    monkeypatch.setattr(service, "check_membership", lambda *args: True)
    user, community_id = service.telegram_login(db, signed_data(settings), settings)
    assert user.display_name == "Аня"
    assert community_id == REAL_COMMUNITY
    assert user.id != "123"
    member = db.get(Membership, (community_id, user.id))
    member.status = "left"
    db.commit()
    raw = signed_data(settings, user=json.dumps({"id": 123, "first_name": "Новое имя", "username": "new"}))
    again, _ = service.telegram_login(db, raw, settings)
    assert again.id == user.id
    assert again.display_name == "Новое имя"
    assert member.status == "active"
    assert db.scalar(select(AuthIdentity).where(AuthIdentity.user_id == user.id)).username == "new"


def test_nonmember_never_registered(db, monkeypatch):
    import pytest

    settings = get_settings().model_copy(
        update={
            "telegram_mode": "polling",
            "telegram_bot_token": "123:secret",
            "telegram_chat_id": -123,
        }
    )
    db.add(Community(id=REAL_COMMUNITY, name="Настоящее сообщество"))
    db.flush()
    db.add(CommunityIntegration(community_id=REAL_COMMUNITY, telegram_chat_id=-123))
    db.commit()
    before = len(db.scalars(select(User)).all())
    monkeypatch.setattr(service, "check_membership", lambda *args: False)
    with pytest.raises(HTTPException) as exc:
        service.telegram_login(db, signed_data(settings), settings)
    assert exc.value.status_code == 403
    assert len(db.scalars(select(User)).all()) == before
