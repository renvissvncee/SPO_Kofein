import asyncio

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from .config import get_settings


router = Router()


def mini_app_url() -> str:
    return get_settings().mini_app_url.rstrip("/") + "/"


@router.message(CommandStart())
async def start(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть Кофеин",
                    web_app=WebAppInfo(url=mini_app_url()),
                )
            ]
        ]
    )
    await message.answer(
        "Найди кофейню и посмотри её меню.",
        reply_markup=keyboard,
    )


async def main() -> None:
    settings = get_settings()
    settings.validate_bot()

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    await bot.delete_webhook(drop_pending_updates=False)
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Открыть Кофеин",
            web_app=WebAppInfo(url=mini_app_url()),
        )
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
