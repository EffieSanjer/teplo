import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from src.config import Settings


def check_membership(settings: Settings, chat_id: int, telegram_user_id: int) -> bool:
    if not settings.telegram_bot_token or settings.telegram_mode == "disabled":
        raise HTTPException(503, "Проверка Telegram временно недоступна")
    request = Request(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/getChatMember",
        data=json.dumps({"chat_id": chat_id, "user_id": telegram_user_id}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=5) as response:
            body = json.load(response)
        if not body.get("ok"):
            raise ValueError()
        member = body["result"]
        return member["status"] in {"creator", "administrator", "member"} or (
            member["status"] == "restricted" and member.get("is_member") is True
        )
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError):
        raise HTTPException(503, "Проверка Telegram временно недоступна. Попробуйте ещё раз") from None
