from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from catalog import PartItem, obd_items

WEB_APP_URL = "https://jarvis-auto-psi.vercel.app"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton("Коды OBD"),
        KeyboardButton("Автосервисы"),
    )
    kb.add(
        KeyboardButton("🌐 Открыть веб-версию"),
        KeyboardButton("Справка"),
    )
    return kb


def main_inline_keyboard(parts: list[PartItem]) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    for part in obd_items(parts):
        markup.add(
            InlineKeyboardButton(
                text=f"Ошибка {part.id}",
                callback_data=f"sym_{part.id}",
            )
        )
    markup.add(
        InlineKeyboardButton(text="Автосервисы", callback_data="get_services"),
        InlineKeyboardButton(
            text="🌐 Полная версия (сайт)",
            url=WEB_APP_URL,
        ),
        InlineKeyboardButton(text="Главное меню", callback_data="main_menu"),
    )
    return markup
