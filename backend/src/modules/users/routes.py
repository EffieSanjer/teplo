from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import Membership, get_db
from src.modules.auth.service import Context, get_context
from src.modules.communities.service import require_recipient
from src.modules.users.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def friends(
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    ids = list(
        db.scalars(
            select(Membership.user_id).where(
                Membership.community_id == ctx.community_id,
                Membership.status == "active",
                Membership.user_id != ctx.user.id,
            )
        )
    )
    users = []
    for user_id in ids:
        try:
            users.append(require_recipient(db, user_id, ctx.community_id, settings))
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
    return sorted(users, key=lambda u: (u.display_name.casefold(), u.id))


@router.get("/{user_id}", response_model=UserOut)
def profile(
    user_id: str,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return require_recipient(db, user_id, ctx.community_id, settings)
