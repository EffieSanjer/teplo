from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import Membership, User, get_db
from src.infrastructure.rate_limit import limit
from src.modules.auth.service import Context, create_session, get_context, telegram_login
from src.modules.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramInput(BaseModel):
    init_data: str = Field(min_length=1, max_length=16384)


class SessionOut(BaseModel):
    user: UserOut
    community_id: str
    csrf_token: str


def login_limit(request: Request, db: Session):
    limit(db, f"login:{request.client.host}", 20)


@router.get("/config")
def config(settings: Settings = Depends(get_settings)) -> dict[str, bool]:
    return {
        "dev_login_enabled": settings.dev_login_enabled,
        "telegram_enabled": settings.telegram_mode != "disabled",
    }


@router.post("/dev", response_model=SessionOut)
def dev_login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not settings.dev_login_enabled:
        raise HTTPException(404, "Не найдено")
    login_limit(request, db)
    user = db.get(User, settings.dev_user_id)
    # Fixed local seed community; no caller-controlled user ID.
    member = db.scalar(
        select(Membership).where(
            Membership.user_id == settings.dev_user_id,
            Membership.community_id == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            Membership.status == "active",
        )
    )
    if not user or not member:
        raise HTTPException(503, "Сначала выполните команду seed")
    csrf = create_session(db, response, user.id, member.community_id, settings)
    return SessionOut(user=UserOut.model_validate(user), community_id=member.community_id, csrf_token=csrf)


@router.post("/telegram", response_model=SessionOut)
def tg_login(
    body: TelegramInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    login_limit(request, db)
    user, community_id = telegram_login(db, body.init_data, settings)
    csrf = create_session(db, response, user.id, community_id, settings)
    return SessionOut(user=UserOut.model_validate(user), community_id=community_id, csrf_token=csrf)


@router.get("/session", response_model=SessionOut)
def current(ctx: Context = Depends(get_context)):
    return SessionOut(
        user=UserOut.model_validate(ctx.user),
        community_id=ctx.community_id,
        csrf_token=ctx.session.csrf_token,
    )


@router.post("/logout", status_code=204)
def logout(response: Response, ctx: Context = Depends(get_context), db: Session = Depends(get_db)):
    db.delete(ctx.session)
    db.commit()
    response.delete_cookie("wishlist_session", path="/")
