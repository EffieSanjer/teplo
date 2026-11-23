import threading
import time
from decimal import Decimal
from urllib.parse import urljoin, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import get_db
from src.infrastructure.rate_limit import limit
from src.integrations.product_metadata.network import FetchError, fetch_public
from src.integrations.product_metadata.afisha import fetch_session, session_api_url
from src.integrations.product_metadata.avito import is_avito, parse_avito
from src.integrations.product_metadata.marketplaces import (
    marketplace_title, merge_product, prefer_large_image, product_ref, public_product,
    reject_marketplace_challenge, reject_yandex_challenge, site_of, state_product,
)
from src.integrations.product_metadata.parser import parse_instagram_post, parse_logos, parse_metadata, parse_telegram_post
from src.integrations.product_metadata.sources import (
    instagram_post_url, preview_url, telegram_fallback_url, telegram_post,
)
from src.modules.auth.service import Context, get_context
from src.modules.gifts.schemas import valid_url
from src.modules.media.service import store_image

router = APIRouter(prefix="/metadata", tags=["metadata"])
slots = threading.BoundedSemaphore(3)


class MetadataInput(BaseModel):
    url: str = Field(max_length=2048)
    prefer_logo: bool = False

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
    image_is_icon: bool = False
    warning: str | None = None


def _absolute_images(values, base_url):
    result = []
    for value in values:
        if not isinstance(value, str):
            continue
        try:
            url = urljoin(base_url, value.strip())
            parts = urlsplit(url)
        except ValueError:
            continue
        if (parts.scheme in {"http", "https"} and parts.hostname
                and not parts.username and not parts.password and url not in result):
            result.append(url)
        if len(result) >= 12:
            break
    return result


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
            return telegram_metadata(body.url, post, db, ctx, settings, body.prefer_logo)
        if post_url := instagram_post_url(body.url):
            return instagram_metadata(post_url, db, ctx, settings, body.prefer_logo)
        deadline = time.monotonic() + settings.metadata_timeout_seconds * 3

        def fetch(url, max_bytes):
            remaining = min(settings.metadata_timeout_seconds, deadline - time.monotonic())
            if remaining <= 0:
                raise FetchError("Сайт не ответил вовремя")
            return fetch_public(url, max_bytes, remaining)

        html, final_url, failure = b"", body.url, None
        draft = {}
        requested_ref = product_ref(body.url)
        try:
            if endpoint := session_api_url(body.url):
                draft = fetch_session(endpoint, fetch, settings.metadata_max_bytes)
            else:
                html, content_type, final_url = fetch(preview_url(body.url), settings.metadata_max_bytes)
                if content_type.split(";")[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
                    raise FetchError("Ссылка не содержит HTML-страницу")
                final_ref = product_ref(final_url)
                if requested_ref and final_ref and requested_ref != final_ref:
                    raise FetchError("Сайт перенаправил на другой товар")
                reject_marketplace_challenge(html, final_url)
                reject_yandex_challenge(html, final_url)
                draft = (parse_avito(html, final_url, body.url) if is_avito(body.url)
                         else parse_metadata(html, final_url))
                if not body.prefer_logo and not is_avito(body.url):
                    merge_product(draft, state_product(html, final_url))
        except FetchError as exc:
            failure = exc
            html = getattr(exc, "body", b"") or b""
            err_url = getattr(exc, "url", final_url) or final_url
            if not draft and html and is_avito(body.url):
                try:
                    draft = parse_avito(html, err_url, body.url)
                    failure = None
                except FetchError as av_exc:
                    failure = av_exc
            elif not draft and is_avito(body.url):
                failure = FetchError(
                    "Авито ограничил доступ или запросил проверку безопасности. "
                    "Ссылку можно сохранить, добавьте название и фото вручную"
                )
            if not draft:
                html = b""
        site = site_of(final_url)
        if not body.prefer_logo and (
            not draft.get("title") or not draft.get("image_url") or draft.get("price") is None
        ):
            merge_product(
                draft,
                public_product(final_url, fetch, settings.metadata_max_bytes, html=html),
            )
        if draft.get("title"):
            draft["title"] = marketplace_title(draft["title"], site)
        if failure and draft.get("title"):
            failure = None  # Partial product data is useful even without a downloadable photo.
        image_url = draft.pop("image_url", None)
        image_urls = draft.pop("image_urls", [])
        if image_url and image_url not in image_urls:
            image_urls.insert(0, image_url)
        image_urls = _absolute_images(image_urls, final_url)
        image_urls = list(dict.fromkeys(prefer_large_image(url, site) for url in image_urls))

        def store(url, logo=False):
            try:
                data, _, _ = fetch(url, settings.max_upload_bytes)
                draft["image_id"] = store_image(db, ctx.user.id, data, settings, allow_icon=logo).id
                draft["image_is_icon"] = logo
                if logo:
                    draft["warning"] = "Вместо фото использован логотип или значок сайта."
                return True
            except (FetchError, HTTPException):
                return False

        logos = parse_logos(html, final_url)
        if not body.prefer_logo:
            # A site can also advertise its icon as a preview image.
            image_urls = [url for url in image_urls if url not in logos]
        attempted = set()

        def try_logos(urls):
            for url in urls:
                if len(attempted) >= 4 or time.monotonic() >= deadline:
                    break
                if url in attempted:
                    continue
                attempted.add(url)
                if store(url, logo=True):
                    return True
            return False

        def try_photos():
            for url in image_urls[:4]:
                if time.monotonic() >= deadline:
                    break
                if store(url):
                    return True
            return False

        if body.prefer_logo:
            try_logos(logos)
        else:
            try_photos()
        if body.prefer_logo and not draft.get("image_id"):
            # A product page can omit brand markup present on the site's home page.
            parts = urlsplit(final_url)
            root = urlunsplit((parts.scheme, parts.netloc, "/", "", ""))
            if not draft.get("image_id") and root != final_url and time.monotonic() < deadline:
                try:
                    home, kind, home_url = fetch(root, settings.metadata_max_bytes)
                    if kind.split(";")[0].strip().lower() in {"text/html", "application/xhtml+xml"}:
                        try_logos(parse_logos(home, home_url))
                except FetchError:
                    pass
            if not draft.get("image_id"):
                try_logos([urlunsplit((parts.scheme, parts.netloc, "/favicon.ico", "", ""))])
            if body.prefer_logo and not draft.get("image_id"):
                try_photos()
        if failure and not draft.get("image_id"):
            raise failure
        if not draft.get("image_id"):
            draft["warning"] = (
                "Не удалось загрузить фото или логотип сайта. Ссылку можно сохранить, а фото добавить вручную."
                if body.prefer_logo else
                "Не удалось загрузить фото. Ссылку можно сохранить, а фото добавить вручную."
            )
        return MetadataOut(**draft)
    except FetchError as exc:
        raise HTTPException(422, str(exc)) from None
    finally:
        slots.release()


def telegram_metadata(url: str, post: tuple[str, str], db: Session, ctx: Context, settings: Settings, prefer_logo=False):
    # At most two HTML pages and two first-photo attempts, within a shared time budget.
    deadline = time.monotonic() + settings.metadata_timeout_seconds * 2
    result = MetadataOut()
    fallback_used = False
    logos = []

    def fetch(url: str, max_bytes: int):
        remaining = min(settings.metadata_timeout_seconds, deadline - time.monotonic())
        if remaining <= 0:
            raise FetchError("Сайт не ответил вовремя")
        return fetch_public(url, max_bytes, remaining)

    for index, candidate in enumerate([preview_url(url), telegram_fallback_url(url)]):
        try:
            html, content_type, final_url = fetch(candidate, settings.metadata_max_bytes)
            if content_type.split(";")[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
                raise FetchError("Ссылка не содержит HTML-страницу")
            draft = parse_telegram_post(html, final_url, *post)
            if telegram_post(final_url) == post:
                logos.extend(parse_logos(html, final_url))
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
            "Загружено первое фото публикации; название — имя автора. Проверьте перед сохранением."
            if fallback_used else "Загружено первое фото публикации и имя автора."
        )
    elif prefer_logo and store_preview_logo(result, url, logos, fetch, db, ctx, settings):
        pass
    else:
        result.warning = (
            "Не удалось загрузить фото публикации. Она может быть закрыта, недоступна "
            "или не содержать фотографий. Ссылку можно сохранить, а фото добавить вручную."
        )
    return result


def instagram_metadata(post_url: str, db: Session, ctx: Context, settings: Settings, prefer_logo=False):
    # Strip share tracking only for the preview; the item keeps the original URL.
    deadline = time.monotonic() + settings.metadata_timeout_seconds * 2
    result = MetadataOut()
    logos = []

    def fetch(url: str, max_bytes: int):
        remaining = min(settings.metadata_timeout_seconds, deadline - time.monotonic())
        if remaining <= 0:
            raise FetchError("Сайт не ответил вовремя")
        return fetch_public(url, max_bytes, remaining)

    for candidate in [post_url, f"{post_url}embed/captioned/"]:
        if time.monotonic() >= deadline:
            break
        try:
            html, content_type, final_url = fetch(candidate, settings.metadata_max_bytes)
            if content_type.split(";")[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
                raise FetchError("Ссылка не содержит HTML-страницу")
            # Do not import a different post, profile, or login screen after redirect.
            final_post = instagram_post_url(final_url.removesuffix("embed/captioned/").removesuffix("embed/"))
            if final_post != post_url:
                continue
            logos.extend(parse_logos(html, final_url))
            draft = parse_instagram_post(html, final_url)
            if draft["title"] and not result.title:
                result.title = draft["title"]
            if draft["image_url"] and not result.image_id and (prefer_logo or draft["image_url"] not in logos):
                try:
                    data, _, _ = fetch(draft["image_url"], settings.max_upload_bytes)
                    result.image_id = store_image(db, ctx.user.id, data, settings).id
                except (FetchError, HTTPException):
                    pass
            if result.image_id:
                break
        except FetchError:
            continue
    if not result.image_id and not (prefer_logo and store_preview_logo(result, post_url, logos, fetch, db, ctx, settings)):
        result.warning = (
            "Сайт не предоставил фото. Даже публичные публикации могут требовать входа. "
            "Ссылку можно сохранить — добавьте фото вручную."
        )
    return result


def store_preview_logo(result, url, logos, fetch, db, ctx, settings):
    parts = urlsplit(url)
    candidates = list(dict.fromkeys(logos))[:3]
    candidates.append(urlunsplit((parts.scheme, parts.netloc, "/favicon.ico", "", "")))
    for candidate in candidates:
        try:
            data, _, _ = fetch(candidate, settings.max_upload_bytes)
            result.image_id = store_image(db, ctx.user.id, data, settings, allow_icon=True).id
            result.image_is_icon = True
            result.warning = "Вместо фото использован логотип или значок сайта."
            return True
        except (FetchError, HTTPException):
            pass
    return False
