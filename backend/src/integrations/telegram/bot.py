import asyncio
import html
import re
from urllib.parse import quote

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    MenuButtonDefault,
    Message,
    WebAppInfo,
)

from src.config import get_settings
from src.integrations.telegram.link_preview import preview_link
from src.integrations.telegram.preview_media import store_preview_photo

URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
MAX_URL_LENGTH = 2048


def _extract_url(message: Message) -> str | None:
    candidates: list[str] = []
    if message.text:
        candidates.append(message.text)
    if message.caption:
        candidates.append(message.caption)

    # Сначала проверяем сущности url / text_link, если они есть в сообщении
    for source_text, entities in (
            (message.text, message.entities),
            (message.caption, message.caption_entities),
    ):
        if not source_text or not entities:
            continue
        for entity in entities:
            if entity.type == "url":
                raw = source_text[entity.offset: entity.offset + entity.length]
                candidates.insert(0, raw)
            elif entity.type == "text_link" and entity.url:
                candidates.insert(0, entity.url)

    for raw_candidate in candidates:
        match = URL_RE.search(raw_candidate.strip())
        if not match:
            continue
        cleaned = match.group(0).rstrip(".,!?;:")
        if cleaned.startswith(("http://", "https://")) and len(
                cleaned) <= MAX_URL_LENGTH:
            return cleaned
    return None


_CURRENCY_LABEL = {"RUB": "₽", "USD": "$", "EUR": "€", "GEL": "₾", "KZT": "₸", "BYN": "Br"}


_IMAGE_ID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _build_mini_app_url(
        base_url: str,
        url: str,
        title: str | None = None,
        price: str | None = None,
        currency: str | None = None,
        image_id: str | None = None,
) -> str:
    params = [f"url={quote(url, safe='')}"]
    if title:
        params.append(f"title={quote(title[:200], safe='')}")
    if price and currency:
        params.append(f"price={quote(price, safe='')}")
        params.append(f"currency={quote(currency, safe='')}")
    if image_id and _IMAGE_ID.fullmatch(image_id):
        params.append(f"image_id={quote(image_id, safe='')}")
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{'&'.join(params)}"


def _format_price(price: str, currency: str | None) -> str:
    label = _CURRENCY_LABEL.get(currency or "", currency or "")
    return f"{price} {label}".strip()


def wish_offer(origin: str, url: str, preview: dict, image_id: str | None = None) -> tuple[str, str]:
    title = preview.get("title") or None
    price = preview.get("price") or None
    currency = preview.get("currency") or None
    target = _build_mini_app_url(
        origin, url, title=title, price=price, currency=currency, image_id=image_id,
    )
    lines = ["Ссылка получена."]
    if title:
        lines.append(f"Название: <b>{html.escape(title)}</b>")
    if price:
        lines.append(f"Цена: {html.escape(_format_price(price, currency))}")
    if image_id:
        lines.append("Первое фото поста добавлю в форму желания.")
    if not title and not price and not image_id:
        lines.append(
            "Автоматически подтянуть данные не удалось (возможно, сайт запросил проверку или закрыл доступ). "
            "Открой форму — ссылку уже подставил, остальное можно заполнить вручную."
        )
    return "\n".join(lines), target


async def _message_photo_bytes(message: Message) -> bytes | None:
    if not message.photo:
        return None
    try:
        buffer = await message.bot.download(message.photo[-1])
    except Exception:
        return None
    if buffer is None:
        return None
    try:
        data = buffer.read()
    except Exception:
        return None
    return data or None


def wish_button(target: str, *, https: bool) -> InlineKeyboardButton:
    if https:
        return InlineKeyboardButton(text="Добавить желание", web_app=WebAppInfo(url=target))
    return InlineKeyboardButton(text="Добавить желание", url=target)


def invitation_path(text: str | None) -> str | None:
    match = re.fullmatch(
        r"/start(?:@[A-Za-z0-9_]+)?\s+friend_([A-Za-z0-9_-]{43})", text or "")
    return "/friends?invite=" + match[1] if match else None


async def main():
    settings = get_settings()
    if settings.telegram_mode != "polling":
        raise SystemExit("Set TELEGRAM_MODE=polling to run the bot")
    bot = Bot(settings.telegram_bot_token)
    dp = Dispatcher()
    public = settings.origin.startswith("https://")

    @dp.message(CommandStart(), F.chat.type == "private")
    async def start(message: Message):
        if not public:
            await message.answer(
                "Привет! Локальный интерфейс нужно открыть в браузере на компьютере, "
                "где запущен проект. Mini App будет доступен после настройки публичного HTTPS."
            )
            return
        invite = invitation_path(message.text)
        if invite:
            await message.answer(
                "Вас пригласили в друзья. Откройте приложение, чтобы посмотреть приглашение и подтвердить его.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="Посмотреть приглашение",
                                         web_app=WebAppInfo(
                                             url=settings.origin + invite)),
                ]]),
            )
            return
        await message.answer(
            "Подарки, которые действительно порадуют ✨",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Мой вишлист",
                            web_app=WebAppInfo(url=settings.origin + "/me")
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="Друзья",
                            web_app=WebAppInfo(url=settings.origin + "/friends")
                        )
                    ],
                ],
            ),
        )

    @dp.message(F.chat.type == "private", F.text | F.caption)
    async def handle_shared_link(message: Message):
        if (message.text or "").startswith("/"):
            return
        url = _extract_url(message)
        if not url:
            await message.answer(
                "Пришли ссылку на товар или страницу — попробую подтянуть данные и открою форму желания."
            )
            return
        try:
            await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        except Exception:
            pass
        try:
            preview = await asyncio.to_thread(preview_link, url, settings)
        except Exception:
            preview = {}
        photo_bytes = await _message_photo_bytes(message)
        image_id = None
        if message.from_user and (photo_bytes or preview.get("image_url")):
            try:
                image_id = await asyncio.to_thread(
                    store_preview_photo,
                    settings,
                    message.from_user.id,
                    image_url=None if photo_bytes else preview.get("image_url"),
                    image_bytes=photo_bytes,
                )
            except Exception:
                image_id = None
        text, target = wish_offer(settings.origin, url, preview, image_id=image_id)
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[wish_button(target, https=public)]]),
            parse_mode="HTML",
        )

    @dp.message(Command("app"), F.chat.type.in_({"group", "supergroup"}))
    async def group_entry(message: Message):
        if message.chat.id != settings.telegram_chat_id:
            return
        if not public or not settings.telegram_bot_username or not settings.telegram_app_name:
            await message.answer(
                "Mini App пока не настроен. Локальная версия открывается на компьютере запуска."
            )
            return
        url = f"https://t.me/{settings.telegram_bot_username}/{settings.telegram_app_name}?startapp=friends"
        await message.answer(
            "Наши вишлисты — все пожелания в одном месте 🎁",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Открыть вишлисты", url=url)]],
            ),
        )

    async with bot:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Открыть вишлисты"),
                BotCommand(command="app",
                           description="Ссылка на приложение в группе"),
            ]
        )
        if public:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Вишлисты",
                    web_app=WebAppInfo(url=settings.origin),
                )
            )
        else:
            await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        # Explicit polling; don't silently delete an existing webhook.
        if (await bot.get_webhook_info()).url:
            raise RuntimeError(
                "Webhook is configured; explicitly remove it before enabling polling")
        await dp.start_polling(bot,
                               allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
