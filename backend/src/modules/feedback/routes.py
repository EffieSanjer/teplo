import html

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import AuthIdentity, get_db
from src.infrastructure.rate_limit import limit
from src.integrations.telegram.client import send_message
from src.modules.auth.service import Context, get_context

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=1000)


def _format_feedback(ctx: Context, identity: AuthIdentity | None, text: str) -> str:
    who = html.escape(ctx.user.display_name)
    parts = ["<b>Предложение для «Кстати»</b>", f"От: {who}"]
    if identity:
        parts.append(f"Telegram ID: <code>{html.escape(identity.provider_user_id)}</code>")
        if identity.username:
            parts.append(f"Username: @{html.escape(identity.username)}")
    parts.append(f"User ID: <code>{html.escape(ctx.user.id)}</code>")
    parts.append("")
    parts.append(html.escape(text))
    return "\n".join(parts)


@router.post("", status_code=204)
def submit_feedback(
    body: FeedbackInput,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not settings.telegram_bot_token or settings.telegram_admin_id is None:
        raise HTTPException(503, "Обратная связь пока недоступна")
    limit(db, f"feedback:{ctx.user.id}", 3)
    identity = db.scalar(
        select(AuthIdentity).where(
            AuthIdentity.user_id == ctx.user.id,
            AuthIdentity.provider == "telegram",
        )
    )
    send_message(settings, settings.telegram_admin_id, _format_feedback(ctx, identity, body.message))
