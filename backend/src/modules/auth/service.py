import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import parse_qsl

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import (
    AuthIdentity,
    AuthSession,
    Community,
    CommunityIntegration,
    Membership,
    PersonalWorkspace,
    User,
    get_db,
    utcnow,
)
from src.integrations.telegram.client import check_membership
from src.modules.communities.service import require_member


def token_hash(token: str, settings: Settings) -> str:
    return hmac.new(settings.session_secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def verify_init_data(raw: str, settings: Settings) -> dict:
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
        data = dict(pairs)
        if len(pairs) != len(data):
            raise ValueError()
        supplied = data.pop("hash")
        secret = hmac.new(b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256).digest()
        check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            raise ValueError()
        age = time.time() - int(data["auth_date"])
        if age < -30 or age > settings.init_data_ttl_seconds:
            raise ValueError()
        user = json.loads(data["user"])
        if type(user.get("id")) is not int or user["id"] <= 0:
            raise ValueError()
        return user
    except (ValueError, KeyError, TypeError):
        raise HTTPException(401, "Недействительные данные входа") from None


def telegram_login(db: Session, raw: str, settings: Settings) -> tuple[User, str]:
    if settings.telegram_mode == "disabled":
        raise HTTPException(404, "Не найдено")
    tg = verify_init_data(raw, settings)
    integration = db.scalar(
        select(CommunityIntegration).where(
            CommunityIntegration.telegram_chat_id == settings.telegram_chat_id,
        )
    ) if settings.telegram_chat_id else None
    group_access = False
    if integration:
        try:
            group_access = check_membership(settings, integration.telegram_chat_id, tg["id"])
        except HTTPException as exc:
            # A failed group check never grants group access. Private access is isolated.
            if exc.status_code != 503 or not settings.telegram_allow_private_login:
                raise
    if not integration and not settings.telegram_allow_private_login:
        raise HTTPException(503, "Сообщество ещё не настроено")
    if not group_access and not settings.telegram_allow_private_login:
        raise HTTPException(403, "Войти могут только участники настроенного чата")
    identity = db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.provider == "telegram",
            AuthIdentity.provider_user_id == str(tg["id"]),
        )
    )
    display_name = " ".join(str(tg.get(k) or "") for k in ("first_name", "last_name")).strip()[:120] or "Друг"
    if identity:
        user = db.get(User, identity.user_id)
        user.display_name = display_name
        identity.username = (tg.get("username") or "")[:120] or None
    else:
        user = User(display_name=display_name)
        db.add(user)
        db.flush()
        db.add(
            AuthIdentity(
                user_id=user.id,
                provider="telegram",
                provider_user_id=str(tg["id"]),
                username=(tg.get("username") or "")[:120] or None,
            )
        )
    if group_access:
        community_id = integration.community_id
    else:
        personal = db.scalar(select(PersonalWorkspace).where(PersonalWorkspace.user_id == user.id))
        if not personal:
            community = Community(name="Личный вишлист")
            db.add(community)
            db.flush()
            personal = PersonalWorkspace(community_id=community.id, user_id=user.id)
            db.add(personal)
        community_id = personal.community_id
    member = db.get(Membership, (community_id, user.id))
    if member:
        member.status, member.checked_at = "active", utcnow()
    else:
        db.add(Membership(community_id=community_id, user_id=user.id, status="active"))
    db.commit()
    from src.modules.users.avatars import telegram_avatar

    telegram_avatar(db, user, settings, tg.get("photo_url"))
    return user, community_id


def create_session(db: Session, response: Response, user_id: str, community_id: str, settings: Settings):
    raw = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=token_hash(raw, settings),
            user_id=user_id,
            community_id=community_id,
            csrf_token=csrf,
            expires_at=utcnow() + timedelta(seconds=settings.session_ttl_seconds),
        )
    )
    db.commit()
    response.set_cookie(
        "wishlist_session",
        raw,
        httponly=True,
        secure=settings.secure_cookie,
        samesite="lax",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    return csrf


@dataclass
class Context:
    user: User
    community_id: str
    session: AuthSession


def get_context(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    raw = request.cookies.get("wishlist_session", "")
    session = db.get(AuthSession, token_hash(raw, settings)) if raw else None
    if not session or session.expires_at <= utcnow():
        raise HTTPException(401, "Войдите в приложение")
    integration = db.get(CommunityIntegration, session.community_id)
    personal = db.get(PersonalWorkspace, session.community_id)
    if settings.telegram_mode != "disabled":
        identity = db.scalar(select(AuthIdentity).where(
            AuthIdentity.user_id == session.user_id,
            AuthIdentity.provider == "telegram",
        ))
        private_access = (
            personal and personal.user_id == session.user_id
            and settings.telegram_allow_private_login and identity
        )
        group_access = (
            not personal and integration and settings.telegram_chat_id is not None
            and integration.telegram_chat_id == settings.telegram_chat_id
        )
        if not private_access and not group_access:
            raise HTTPException(403, "Нет доступа к сообществу")
    elif not settings.dev_login_enabled or personal:
        raise HTTPException(403, "Нет доступа к сообществу")
    require_member(db, session.user_id, session.community_id, settings)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), session.csrf_token):
            raise HTTPException(403, "Обновите страницу и попробуйте ещё раз")
    return Context(db.get(User, session.user_id), session.community_id, session)
