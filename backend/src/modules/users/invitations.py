import re
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import FriendInvitation, Friendship, User, get_db, utcnow
from src.infrastructure.rate_limit import limit
from src.modules.auth.service import Context, get_context, token_hash
from src.modules.users.schemas import UserOut

router = APIRouter(prefix="/friends", tags=["friends"])


class InvitationOut(BaseModel):
    url: str
    expires_at: datetime


class InvitationInput(BaseModel):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class InvitationPreview(BaseModel):
    inviter: UserOut
    own: bool


def find_invitation(db, token, settings):
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(404, "Приглашение недействительно или уже использовано")
    invite = db.get(FriendInvitation, token_hash(token, settings))
    if not invite or invite.accepted_by is not None or invite.expires_at <= utcnow():
        raise HTTPException(404, "Приглашение недействительно или уже использовано")
    return invite


@router.post("/invitations", response_model=InvitationOut, status_code=201)
def create_invitation(
    ctx: Context = Depends(get_context), db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", settings.telegram_bot_username or ""):
        raise HTTPException(409, "Для приглашений нужно настроить имя бота")
    limit(db, f"invite-create:{ctx.user.id}", 10)
    # Drop spent or expired links for this owner; active ones stay valid until
    # a friend accepts them, they expire, or the owner revokes them.
    db.execute(
        delete(FriendInvitation).where(
            FriendInvitation.owner_id == ctx.user.id,
            (FriendInvitation.accepted_by.is_not(None)) | (FriendInvitation.expires_at <= utcnow()),
        )
    )
    token = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(days=7)
    # Raw tokens never enter the DB — only a peppered hash is stored.
    db.add(FriendInvitation(token_hash=token_hash(token, settings), owner_id=ctx.user.id, expires_at=expires))
    db.commit()
    # Use the private bot's /start flow; it works without a Main Mini App.
    # The bot replies with a WebApp button carrying the explicit invite query.
    return InvitationOut(url=f"https://t.me/{settings.telegram_bot_username}?start=friend_{token}", expires_at=expires)


@router.get("/invitations/{token}", response_model=InvitationPreview)
def preview(
    token: str, ctx: Context = Depends(get_context), db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    limit(db, f"invite-preview:{ctx.user.id}", 60)
    invite = find_invitation(db, token, settings)
    return InvitationPreview(inviter=UserOut.model_validate(db.get(User, invite.owner_id)), own=invite.owner_id == ctx.user.id)


@router.delete("/invitations/{token}", status_code=204)
def revoke_invitation(
    token: str, ctx: Context = Depends(get_context), db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(404, "Приглашение недействительно или уже использовано")
    # Only the shown link is revoked; other pending invites stay valid.
    db.execute(
        delete(FriendInvitation).where(
            FriendInvitation.token_hash == token_hash(token, settings),
            FriendInvitation.owner_id == ctx.user.id,
        )
    )
    db.commit()


@router.post("/accept", response_model=UserOut)
def accept(
    body: InvitationInput, ctx: Context = Depends(get_context), db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    limit(db, f"invite-accept:{ctx.user.id}", 20)
    invite = find_invitation(db, body.token, settings)
    if invite.owner_id == ctx.user.id:
        raise HTTPException(409, "Это ваше приглашение. Отправьте его другу")
    # Conditional update makes a link single-use even for concurrent acceptances.
    owner = db.scalar(update(FriendInvitation).where(
        FriendInvitation.token_hash == invite.token_hash,
        FriendInvitation.accepted_by.is_(None), FriendInvitation.expires_at > utcnow(),
    ).values(accepted_by=ctx.user.id).returning(FriendInvitation.owner_id))
    if not owner:
        raise HTTPException(404, "Приглашение недействительно или уже использовано")
    first, second = sorted((ctx.user.id, owner))
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    db.execute(insert(Friendship).values(user_id=first, friend_id=second, created_at=utcnow()).on_conflict_do_nothing())
    db.commit()
    user = db.get(User, owner)
    return UserOut(id=user.id, display_name=user.display_name, avatar_media_id=user.avatar_media_id, is_friend=True, can_surprise=True)


@router.delete("/{user_id}", status_code=204)
def remove_friend(user_id: str, ctx: Context = Depends(get_context), db: Session = Depends(get_db)):
    first, second = sorted((ctx.user.id, user_id))
    db.execute(delete(Friendship).where(Friendship.user_id == first, Friendship.friend_id == second))
    db.commit()
