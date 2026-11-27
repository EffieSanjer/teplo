from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import Friendship, Membership, get_db
from src.modules.users.avatars import telegram_avatar
from src.modules.auth.service import Context, get_context
from src.modules.users.schemas import UserOut
from src.modules.users.access import can_share_surprises, friendship, require_visible_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def friends(
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    ids = set(
        db.scalars(
            select(Membership.user_id).where(
                Membership.community_id == ctx.community_id,
                Membership.status == "active",
                Membership.user_id != ctx.user.id,
            )
        )
    )
    for row in db.scalars(select(Friendship).where(or_(
        Friendship.user_id == ctx.user.id, Friendship.friend_id == ctx.user.id,
    ))):
        ids.add(row.friend_id if row.user_id == ctx.user.id else row.user_id)
    users = []
    for user_id in ids:
        try:
            user = require_visible_user(db, ctx.user.id, user_id, ctx.community_id, settings)
            users.append(user)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
    return [user_out(db, ctx, user, settings) for user in sorted(users, key=lambda u: (u.display_name.casefold(), u.id))]


def user_out(db, ctx, user, settings):
    return UserOut(
        id=user.id, display_name=user.display_name, avatar_media_id=user.avatar_media_id,
        is_friend=bool(friendship(db, ctx.user.id, user.id)),
        can_surprise=user.id != ctx.user.id and can_share_surprises(db, user.id, ctx.community_id, settings, ctx.user.id),
    )


@router.get("/{user_id}", response_model=UserOut)
def profile(
    user_id: str,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = require_visible_user(db, ctx.user.id, user_id, ctx.community_id, settings)
    return user_out(db, ctx, user, settings)


@router.get("/{user_id}/avatar", response_class=FileResponse)
def avatar(
    user_id: str, ctx: Context = Depends(get_context), db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = require_visible_user(db, ctx.user.id, user_id, ctx.community_id, settings)
    media = telegram_avatar(db, user, settings)
    if not media or not (settings.media_root / media.storage_key).is_file():
        raise HTTPException(404, "Фото профиля недоступно")
    return FileResponse(
        settings.media_root / media.storage_key, media_type=media.mime_type,
        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )
