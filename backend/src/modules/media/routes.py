import threading

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import get_db
from src.infrastructure.rate_limit import limit
from src.integrations.product_metadata.network import FetchError, fetch_public
from src.modules.auth.service import Context, get_context
from src.modules.gifts.service import missing
from src.modules.gifts.schemas import valid_url
from src.modules.media.service import authorized_media, store_image

router = APIRouter(prefix="/media", tags=["media"])
url_slots = threading.BoundedSemaphore(3)


class MediaOut(BaseModel):
    id: str


class ImageUrlInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def check_url(cls, value: str) -> str:
        return valid_url(value.strip())


@router.post("", response_model=MediaOut, status_code=201)
def upload(
    file: UploadFile,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    limit(db, f"upload:{ctx.user.id}", 15)
    data = file.file.read(settings.max_upload_bytes + 1)
    return MediaOut(id=store_image(db, ctx.user.id, data, settings).id)


@router.post("/from-url", response_model=MediaOut, status_code=201)
def upload_from_url(
    body: ImageUrlInput,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    limit(db, f"upload:{ctx.user.id}", 15)
    if not url_slots.acquire(blocking=False):
        raise HTTPException(429, "Загрузка изображений занята. Попробуйте позже")
    try:
        data, _, _ = fetch_public(body.url, settings.max_upload_bytes, settings.metadata_timeout_seconds)
        # Validate the actual bytes, not the URL extension or the site's Content-Type.
        return MediaOut(id=store_image(db, ctx.user.id, data, settings).id)
    except FetchError as exc:
        raise HTTPException(422, str(exc)) from None
    finally:
        url_slots.release()


@router.get("/{media_id}", response_class=FileResponse)
def download(
    media_id: str,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    media = authorized_media(db, ctx, media_id, settings)
    path = settings.media_root / media.storage_key
    if not path.is_file():
        missing()
    return FileResponse(
        path,
        media_type=media.mime_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
