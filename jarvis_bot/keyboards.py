from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from catalog import PartItem

WEB_APP_URL = "https://jarvis-auto-psi.vercel.app"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура — 5 кнопок."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🔍 Диагностика"),
        KeyboardButton("🏪 Автосервисы"),
    )
    kb.add(
        KeyboardButton("🆘 SOS"),
        KeyboardButton("📋 Моя история"),
    )
    kb.add(
        KeyboardButton("❓ Справка"),
    )
    return kb


def sos_location_keyboard() -> ReplyKeyboardMarkup:
    """Запрос геолокации для SOS."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    kb.add(KeyboardButton("📍 Отправить моё местоположение", request_location=True))
    kb.add(KeyboardButton("🔙 Без геолокации (федеральные номера)"))
    return kb


def main_inline_keyboard(parts: list[PartItem] = None, city_key: str = "") -> InlineKeyboardMarkup:
    """
    Главное инлайн-меню — без OBD-кнопок.
    Золотая кнопка СТО-спонсора если задан city_key.
    """
    markup = InlineKeyboardMarkup(row_width=1)

    # Золотая кнопка спонсора СТО
    if city_key:
        try:
            from sponsors import get_gold_sto
            gold = get_gold_sto(city_key)
            if gold:
                markup.add(
                    InlineKeyboardButton(
                        text=f"🥇 {gold.name} — Рекомендуем!",
                        callback_data=f"sponsor_sto_{city_key}",
                    )
                )
        except ImportError:
            pass

    markup.add(
        InlineKeyboardButton(text="🏪 Автосервисы",  callback_data="get_services"),
        InlineKeyboardButton(text="🆘 SOS / Авария", callback_data="sos_ask"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
    )
    return markup


def dialog_options_keyboard(options: list[str], tree_id: str) -> InlineKeyboardMarkup:
    """Кнопки вариантов ответа в диалоге диагностики."""
    markup = InlineKeyboardMarkup(row_width=1)
    for opt in options:
        btn_text = opt if len(opt) <= 45 else opt[:42] + "..."
        markup.add(
            InlineKeyboardButton(
                text=btn_text,
                callback_data=f"diag_{tree_id}::{opt[:60]}",
            )
        )
    markup.add(
        InlineKeyboardButton(text="❌ Отменить", callback_data="diag_cancel"),
    )
    return markup


def after_diagnostic_keyboard(city_key: str = "yoshkar_ola") -> InlineKeyboardMarkup:
    """Кнопки под результатом диагностики."""
    markup = InlineKeyboardMarkup(row_width=1)

    if city_key:
        try:
            from sponsors import get_gold_sto
            gold = get_gold_sto(city_key)
            if gold:
                markup.add(
                    InlineKeyboardButton(
                        text=f"🥇 Записаться: {gold.name} ({gold.phone})",
                        callback_data=f"sponsor_sto_{city_key}",
                    )
                )
        except ImportError:
            pass

    markup.add(
        InlineKeyboardButton(text="🏪 Автосервисы",  callback_data="get_services"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
    )
    return markup


def sos_inline_keyboard(city_key: str = "") -> InlineKeyboardMarkup:
    """Кнопки под SOS-сообщением."""
    markup = InlineKeyboardMarkup(row_width=1)

    if city_key:
        try:
            from sponsors import get_gold_komissar
            gold = get_gold_komissar(city_key)
            if gold:
                markup.add(
                    InlineKeyboardButton(
                        text=f"🥇 Позвонить: {gold.name}",
                        callback_data=f"sponsor_kom_{city_key}",
                    )
                )
        except ImportError:
            pass

    markup.add(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
    )
    return markup
