from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from catalog import PartItem, obd_items

WEB_APP_URL = "https://jarvis-auto-psi.vercel.app"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Компактная клавиатура: 5 кнопок."""
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
    """Клавиатура с кнопкой отправки геолокации."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    kb.add(KeyboardButton("📍 Отправить моё местоположение", request_location=True))
    kb.add(KeyboardButton("🔙 Без геолокации (федеральные номера)"))
    return kb


def main_inline_keyboard(parts: list[PartItem], city_key: str = "") -> InlineKeyboardMarkup:
    """
    Инлайн-меню: OBD-коды + автосервисы + SOS.
    Если city_key передан — добавляет золотую кнопку спонсора-СТО.
    """
    markup = InlineKeyboardMarkup(row_width=1)

    # OBD коды
    for part in obd_items(parts):
        markup.add(
            InlineKeyboardButton(
                text=f"⚠️ {part.id} — {part.name}",
                callback_data=f"sym_{part.id}",
            )
        )

    # Золотая кнопка СТО-спонсора если есть
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
        InlineKeyboardButton(text="🏪 Автосервисы рядом", callback_data="get_services"),
        InlineKeyboardButton(text="🆘 SOS / Авария",      callback_data="sos_ask"),
        InlineKeyboardButton(text="🌐 Полная версия",      url=WEB_APP_URL),
        InlineKeyboardButton(text="🏠 Главное меню",       callback_data="main_menu"),
    )
    return markup


def after_diagnostic_keyboard(city_key: str = "yoshkar_ola") -> InlineKeyboardMarkup:
    """
    Кнопки под результатом диагностики:
    золотое СТО-спонсор + список всех сервисов + главное меню.
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
                        text=f"🥇 Записаться: {gold.name} ({gold.phone})",
                        callback_data=f"sponsor_sto_{city_key}",
                    )
                )
        except ImportError:
            pass

    markup.add(
        InlineKeyboardButton(text="🏪 Все автосервисы",   callback_data="get_services"),
        InlineKeyboardButton(text="🆘 SOS / Авария",      callback_data="sos_ask"),
        InlineKeyboardButton(text="🏠 Главное меню",       callback_data="main_menu"),
    )
    return markup


def sos_inline_keyboard(city_key: str = "") -> InlineKeyboardMarkup:
    """
    Инлайн под SOS-сообщением.
    Если есть золотой комиссар — выделенная кнопка первой.
    """
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
