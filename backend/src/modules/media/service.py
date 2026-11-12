import io
import warnings
from datetime import timedelta

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings
from src.infrastructure.database import Item, Media, new_id, utcnow
from src.modules.auth.service import Context
from src.modules.gifts.service import accessible, missing


def store_image(db: Session, owner_id: str, data: bytes, settings: Settings) -> Media:
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "Изображение больше допустимого размера")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError()
                if source.width * source.height > settings.max_image_pixels:
                    raise ValueError()
                source.verify()
            with Image.open(io.BytesIO(data)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((2400, 2400))
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=88)
                clean = output.getvalue()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise HTTPException(
            422, "Нужна неповреждённая фотография JPEG, PNG или WebP допустимых размеров"
        ) from None
    settings.media_root.mkdir(parents=True, exist_ok=True)
    key = f"{new_id()}.jpg"
    path = settings.media_root / key
    path.write_bytes(clean)
    media = Media(storage_key=key, owner_id=owner_id, mime_type="image/jpeg", size=len(clean))
    try:
        db.add(media)
        db.commit()
        db.refresh(media)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return media


def authorized_media(db: Session, ctx: Context, media_id: str, settings: Settings) -> Media:
    media = db.get(Media, media_id)
    if not media:
        missing()
    items = db.scalars(select(Item).where(Item.image_id == media.id)).all()
    if items:
        if any(accessible(db, ctx, item, settings) for item in items):
            return media
        missing()
    if (
        media.attached_at is None
        and media.owner_id == ctx.user.id
        and media.created_at > utcnow() - timedelta(hours=settings.unattached_media_ttl_hours)
    ):
        return media
    missing()


def cleanup(db: Session, settings: Settings) -> int:
    cutoff = utcnow() - timedelta(hours=settings.unattached_media_ttl_hours)
    rows = db.scalars(
        select(Media).where(
            Media.created_at < cutoff,
            ~select(Item.id).where(Item.image_id == Media.id).exists(),
        )
    ).all()
    for media in rows:
        (settings.media_root / media.storage_key).unlink(missing_ok=True)
        db.delete(media)
    db.commit()
    return len(rows)
