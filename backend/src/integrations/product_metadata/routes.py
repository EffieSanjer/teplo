import threading
import time
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import get_db
from src.infrastructure.rate_limit import limit
from src.integrations.product_metadata.network import FetchError, fetch_public
from src.integrations.product_metadata.parser import parse_metadata, parse_telegram_post
from src.integrations.product_metadata.sources import preview_url, telegram_fallback_url, telegram_post
from src.modules.auth.service import Context, get_context
from src.modules.gifts.schemas import valid_url
from src.modules.media.service import store_image

router = APIRouter(prefix="/metadata", tags=["metadata"])
slots = threading.BoundedSemaphore(3)


class MetadataInput(BaseModel):
    url: str = Field(max_length=2048)

    @field_validator("url")
    @classmethod
    def check_url(cls, value):
        return valid_url(value)


class MetadataOut(BaseModel):
    title: str | None = None
    description: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    image_id: str | None = None
    warning: str | None = None


@router.post("", response_model=MetadataOut)
def metadata(
    body: MetadataInput,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    limit(db, f"metadata:{ctx.user.id}", 6)
    if not slots.acquire(blocking=False):
        raise HTTPException(429, "Автозаполнение занято. Попробуйте позже")
    try:
        if post := telegram_post(body.url):
            return telegram_metadata(body.url, post, db, ctx, settings)
        html, content_type, final_url = fetch_public(
            preview_url(body.url),
            settings.metadata_max_bytes,
            settings.metadata_timeout_seconds,
        )
        if content_type.split(";")[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
            raise FetchError("Ссылка не содержит HTML-страницу")
        draft = parse_metadata(html, final_url)
        image_url = draft.pop("image_url")
        if image_url:
            try:
                data, _, _ = fetch_public(
                    image_url, settings.max_upload_bytes, settings.metadata_timeout_seconds
                )
                draft["image_id"] = store_image(db, ctx.user.id, data, settings).id
            except (FetchError, HTTPException):
                draft["warning"] = "Не удалось загрузить фото. Можно добавить своё"
        else:
            draft["warning"] = (
                "Страница не предоставила фото. Закрытые публикации и страницы с требованием входа "
                "могут быть недоступны. Ссылку можно сохранить, а фото добавить вручную."
            )
        return MetadataOut(**draft)
    except FetchError as exc:
        raise HTTPException(422, str(exc)) from None
    finally:
        slots.release()


def telegram_metadata(url: str, post: tuple[str, str], db: Session, ctx: Context, settings: Settings):
    # At most two HTML pages and two first-photo attempts, within a shared time budget.
    deadline = time.monotonic() + settings.metadata_timeout_seconds * 2
    result = MetadataOut()
    fallback_used = False

    def fetch(url: str, max_bytes: int):
        remaining = min(settings.metadata_timeout_seconds, deadline - time.monotonic())
        if remaining <= 0:
            raise FetchError("Telegram не ответил вовремя")
        return fetch_public(url, max_bytes, remaining)

    for index, candidate in enumerate([preview_url(url), telegram_fallback_url(url)]):
        try:
            html, content_type, final_url = fetch(candidate, settings.metadata_max_bytes)
            if content_type.split(";")[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
                raise FetchError("Ссылка не содержит HTML-страницу")
            draft = parse_telegram_post(html, final_url, *post)
            if draft["title"] and not result.title:
                result.title = draft["title"]
            if draft["image_url"] and not result.image_id:
                try:
                    data, _, _ = fetch(draft["image_url"], settings.max_upload_bytes)
                    result.image_id = store_image(db, ctx.user.id, data, settings).id
                except (FetchError, HTTPException):
                    pass
            if index and (draft["title"] or result.image_id):
                fallback_used = True
            if result.title and result.image_id:
                break
        except FetchError:
            continue
    if result.image_id:
        result.warning = (
            "Загружено первое фото из поста Telegram; название — имя канала. Проверьте перед сохранением."
            if fallback_used else "Загружено первое фото из поста Telegram и название канала."
        )
    else:
        result.warning = (
            "Не удалось загрузить фото поста Telegram. Публикация может быть закрыта, недоступна "
            "или не содержать фотографий. Ссылку можно сохранить, а фото добавить вручную."
        )
    return result
