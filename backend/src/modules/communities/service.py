from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings
from src.infrastructure.database import AuthIdentity, CommunityIntegration, Membership, User, utcnow
from src.integrations.telegram.client import check_membership


def require_member(db: Session, user_id: str, community_id: str, settings: Settings) -> Membership:
    member = db.get(Membership, (community_id, user_id))
    if not member or member.status != "active":
        raise HTTPException(403, "Нет доступа к сообществу")
    integration = db.get(CommunityIntegration, community_id)
    if integration and member.checked_at < utcnow() - timedelta(seconds=settings.membership_ttl_seconds):
        identity = db.scalar(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user_id,
                AuthIdentity.provider == "telegram",
            )
        )
        if not identity:
            raise HTTPException(403, "Нет доступа к сообществу")
        active = check_membership(settings, integration.telegram_chat_id, int(identity.provider_user_id))
        member.checked_at = utcnow()
        member.status = "active" if active else "left"
        db.commit()
        if not active:
            raise HTTPException(403, "Нет доступа к сообществу")
    return member


def require_recipient(db: Session, user_id: str, community_id: str, settings: Settings) -> User:
    try:
        require_member(db, user_id, community_id, settings)
    except HTTPException as exc:
        if exc.status_code == 403:
            raise HTTPException(404, "Не найдено") from None
        raise
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Не найдено")
    return user
