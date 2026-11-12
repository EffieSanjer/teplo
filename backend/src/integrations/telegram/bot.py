import asyncio

from aiogram import Bot, Dispatcher, F
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
        await message.answer(
            "Подарки, которые действительно порадуют ✨",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Мой вишлист", web_app=WebAppInfo(url=settings.origin + "/me")
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="Друзья", web_app=WebAppInfo(url=settings.origin + "/friends")
                        )
                    ],
                ],
            ),
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
                inline_keyboard=[[InlineKeyboardButton(text="Открыть вишлисты", url=url)]],
            ),
        )

    async with bot:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Открыть вишлисты"),
                BotCommand(command="app", description="Ссылка на приложение в группе"),
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
            raise RuntimeError("Webhook is configured; explicitly remove it before enabling polling")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
