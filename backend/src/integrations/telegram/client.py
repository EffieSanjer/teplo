import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from src.config import Settings


def _telegram_api(settings: Settings, method: str, payload: dict, *, timeout: float = 5) -> dict:
    if not settings.telegram_bot_token:
        raise HTTPException(503, "Telegram временно недоступен")
    request = Request(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.load(response)
        if not body.get("ok"):
            raise ValueError()
        return body["result"]
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError, TypeError):
        raise HTTPException(503, "Telegram временно недоступен. Попробуйте ещё раз") from None


def check_membership(settings: Settings, chat_id: int, telegram_user_id: int) -> bool:
    if not settings.telegram_bot_token or settings.telegram_mode == "disabled":
        raise HTTPException(503, "Проверка доступа временно недоступна")
    try:
        member = _telegram_api(
            settings, "getChatMember", {"chat_id": chat_id, "user_id": telegram_user_id},
        )
        return member["status"] in {"creator", "administrator", "member"} or (
            member["status"] == "restricted" and member.get("is_member") is True
        )
    except HTTPException as exc:
        if exc.status_code == 503:
            raise HTTPException(
                503, "Проверка доступа временно недоступна. Попробуйте ещё раз",
            ) from None
        raise
    except (KeyError, TypeError):
        raise HTTPException(503, "Проверка доступа временно недоступна. Попробуйте ещё раз") from None


def send_message(
    settings: Settings,
    chat_id: int,
    text: str,
    *,
    parse_mode: str | None = "HTML",
    disable_web_page_preview: bool = True,
) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    _telegram_api(settings, "sendMessage", payload)
