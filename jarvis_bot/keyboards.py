from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from catalog import PartItem

WEB_APP_URL = "https://jarvis-auto-psi.vercel.app"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура — 6 кнопок."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🚗 Моё авто"),
        KeyboardButton("🔍 Диагностика"),
    )
    kb.add(
        KeyboardButton("🏪 Автосервисы"),
        KeyboardButton("🆘 SOS"),
    )
    kb.add(
        KeyboardButton("📋 Моя история"),
        KeyboardButton("❓ Справка"),
    )
    return kb


def sos_location_keyboard() -> ReplyKeyboardMarkup:
    """Запрос геолокации для SOS."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    kb.add(KeyboardButton("📍 Отправить моё местоположение", request_location=True))
    kb.add(KeyboardButton("🔙 Без геолокации (федеральные номера)"))
    return kb


def vehicle_brands_keyboard(brands: list[str]) -> ReplyKeyboardMarkup:
    """Выбор марки авто."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, one_time_keyboard=True)
    
    # Добавляем бренды по 2 в ряд
    for i in range(0, len(brands), 2):
        if i + 1 < len(brands):
            kb.add(
                KeyboardButton(brands[i]),
                KeyboardButton(brands[i + 1])
            )
        else:
            kb.add(KeyboardButton(brands[i]))
    
    kb.add(KeyboardButton("🔙 Отмена"))
    return kb


def vehicle_models_keyboard(models: list[dict]) -> ReplyKeyboardMarkup:
    """Выбор модели авто."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    
    for model in models:
        kb.add(KeyboardButton(f"{model.get('model', '')} ({model.get('years', [2000, 2030])[0]}-{model.get('years', [2000, 2030])[1]})"))
    
    kb.add(KeyboardButton("🔙 Отмена"))
    return kb


def vehicle_years_keyboard(start_year: int, end_year: int) -> ReplyKeyboardMarkup:
    """Выбор года выпуска авто."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3, one_time_keyboard=True)
    
    # Показываем последние 15 лет с шагом 1
    current_year = min(2026, end_year)
    years = list(range(current_year, max(start_year - 1, current_year - 15), -1))
    
    for i in range(0, len(years), 3):
        row_years = years[i:i+3]
        kb.add(*[KeyboardButton(str(y)) for y in row_years])
    
    kb.add(KeyboardButton("🔙 Отмена"))
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
