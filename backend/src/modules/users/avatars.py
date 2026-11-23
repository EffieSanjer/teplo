"""Import Telegram avatars into private, validated local media."""

import json
import threading
import time
from collections import OrderedDict
from datetime import timedelta
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from fastapi import HTTPException
from sqlalchemy import select

from src.infrastructure.database import AuthIdentity, Media, utcnow
from src.integrations.product_metadata.network import FetchError, fetch_public

_attempts = OrderedDict()
_attempts_lock = threading.Lock()


def telegram_avatar(db, user, settings, photo_url=None):
    existing = db.get(Media, user.avatar_media_id) if user.avatar_media_id else None
    if existing and existing.created_at > utcnow() - timedelta(days=1) and not photo_url:
        return existing
    if settings.telegram_mode == "disabled" or not settings.telegram_bot_token:
        return existing
    with _attempts_lock:
        now = time.monotonic()
        if now - _attempts.get(user.id, float("-inf")) < 300:
            return existing
        _attempts[user.id] = now
        _attempts.move_to_end(user.id)
        if len(_attempts) > 2000:
            _attempts.popitem(last=False)

    def telegram(method, payload):
        request = Request(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}",
            data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=3) as response:
            body = json.loads(response.read(65536))
        if not body.get("ok"):
            raise ValueError()
        return body["result"]

    try:
        # Mini App photo_url can be a small preview; prefer the largest Bot API size.
        try:
            identity = db.scalar(select(AuthIdentity).where(
                AuthIdentity.user_id == user.id, AuthIdentity.provider == "telegram",
            ))
            if not identity:
                return existing
            result = telegram("getUserProfilePhotos", {"user_id": int(identity.provider_user_id), "limit": 1})
            if not result.get("photos"):
                user.avatar_media_id = None
                db.commit()
                return None
            photo = max(result["photos"][0], key=lambda size: size.get("width", 0) * size.get("height", 0))
            file = telegram("getFile", {"file_id": photo["file_id"]})
            path = file["file_path"]
            if not isinstance(path, str) or any(part in {"", ".", ".."} for part in path.split("/")):
                raise ValueError()
            photo_url = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{path}"
        except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, IndexError):
            if not photo_url:
                return existing
        if not isinstance(photo_url, str):
            return existing
        parts = urlsplit(photo_url)
        host = parts.hostname or ""
        if parts.scheme != "https" or not (host == "telegram.org" or host.endswith(".telegram.org") or host == "t.me"):
            return existing
        data, _, _ = fetch_public(photo_url, settings.max_upload_bytes, 3)
        # Import locally to avoid the auth -> avatars -> media -> auth cycle.
        from src.modules.media.service import store_image

        media = store_image(db, user.id, data, settings)
        media.attached_at = utcnow()
        user.avatar_media_id = media.id
        db.commit()
        return media
    except (FetchError, HTTPException, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, IndexError):
        # Missing/private photos and Telegram outages must not prevent login.
        return existing
