from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.config import Settings
from src.infrastructure.database import Friendship, User
from src.modules.communities.service import require_recipient


def friendship(db: Session, first: str, second: str) -> Friendship | None:
    return db.get(Friendship, tuple(sorted((first, second)))) if first != second else None


def require_visible_user(db: Session, viewer_id: str, user_id: str, community_id: str, settings: Settings) -> User:
    # Explicit friendship grants only a wishlist/profile, never group membership.
    if friendship(db, viewer_id, user_id):
        user = db.get(User, user_id)
        if user:
            return user
    return require_recipient(db, user_id, community_id, settings)


def can_share_surprises(db: Session, user_id: str, community_id: str, settings: Settings, viewer_id: str | None = None) -> bool:
    if viewer_id and friendship(db, viewer_id, user_id):
        return True
    try:
        require_recipient(db, user_id, community_id, settings)
        return True
    except HTTPException as exc:
        if exc.status_code == 404:
            return False
        raise
