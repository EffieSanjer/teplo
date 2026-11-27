"""Save a preview photo for the Telegram user who shared a link with the bot."""

from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from src.config import Settings
from src.infrastructure.database import AuthIdentity, get_engine
from src.integrations.product_metadata.network import FetchError, fetch_public
from src.modules.media.service import store_image


def store_preview_photo(
    settings: Settings,
    telegram_user_id: int,
    *,
    image_url: str | None = None,
    image_bytes: bytes | None = None,
) -> str | None:
    if not telegram_user_id:
        return None
    data = image_bytes
    if data is None:
        if not image_url or not isinstance(image_url, str):
            return None
        try:
            parts = urlsplit(image_url)
        except ValueError:
            return None
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            return None
        try:
            # fetch_public re-validates DNS and blocks private addresses.
            data, _, _ = fetch_public(image_url, settings.max_upload_bytes, settings.metadata_timeout_seconds)
        except FetchError:
            return None
    if not data:
        return None
    with sessionmaker(get_engine(), expire_on_commit=False)() as db:
        identity = db.scalar(
            select(AuthIdentity).where(
                AuthIdentity.provider == "telegram",
                AuthIdentity.provider_user_id == str(telegram_user_id),
            )
        )
        if not identity:
            return None
        try:
            return store_image(db, identity.user_id, data, settings).id
        except HTTPException:
            return None
