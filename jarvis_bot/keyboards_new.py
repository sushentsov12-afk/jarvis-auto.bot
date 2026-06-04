from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_reply_keyboard():
    """
    ГЛАВНОЕ МЕНЮ — красивая панель с большой кнопкой Диагностика в центре.
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Большая кнопка диагностики занимает всю ширину
    kb.add(KeyboardButton("🔍 ДИАГНОСТИКА"))
    
    # Второй ряд: Мое авто | Справка
    kb.add(
        KeyboardButton("🚗 Моё авто"),
        KeyboardButton("ℹ️ Справка")
    )
    
    # Третий ряд: История | Сервисы
    kb.add(
        KeyboardButton("📋 История"),
        KeyboardButton("🏪 Сервисы")
    )
    
    # Четвертый ряд: SOS
    kb.add(KeyboardButton("🆘 SOS"))
    
    return kb


def back_to_menu_keyboard():
    """Простая кнопка Назад в главное меню."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🏠 Главное меню"))
    return kb


def diagnostic_menu_keyboard():
    """Меню диагностики с вариантами ввода."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✍️ Описать симптом"))
    kb.add(KeyboardButton("💻 Ввести код OBD"))
    kb.add(KeyboardButton("🏠 Главное меню"))
    return kb


def brand_keyboard(brands: list):
    """Клавиатура выбора бренда."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    for brand in brands:
        kb.add(KeyboardButton(brand))
    
    kb.add(KeyboardButton("🏠 Главное меню"))
    return kb


def model_keyboard(models: list):
    """Клавиатура выбора модели."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    for model in models:
        kb.add(KeyboardButton(model))
    
    kb.add(KeyboardButton("⬅️ Вернуться к маркам"))
    kb.add(KeyboardButton("🏠 Главное меню"))
    return kb


def year_keyboard():
    """Клавиатура выбора года выпуска."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    current_year = 2026
    for year in range(current_year, 1989, -1):
        kb.add(KeyboardButton(str(year)))
        if current_year - year >= 24:  # Показываем последние 24 года
            break
    
    kb.add(KeyboardButton("⬅️ Вернуться к моделям"))
    kb.add(KeyboardButton("🏠 Главное меню"))
    return kb


def my_car_menu_keyboard(has_car: bool):
    """Меню управления автомобилем."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    
    if has_car:
        kb.add(KeyboardButton("🔄 Изменить авто"))
        kb.add(KeyboardButton("📌 Типичные ошибки"))
        kb.add(KeyboardButton("❌ Удалить авто"))
    else:
        kb.add(KeyboardButton("➕ Выбрать авто"))
    
    kb.add(KeyboardButton("🏠 Главное меню"))
    return kb


def confirm_vehicle_keyboard():
    """Инлайн-кнопки подтверждения авто."""
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✔️ Подтвердить", callback_data="confirm_vehicle"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_vehicle")
    )
    return kb


def main_inline_keyboard(city_key: str = ""):
    """Инлайн-меню с быстрыми действиями."""
    kb = InlineKeyboardMarkup()
    
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    kb.add(InlineKeyboardButton("🏪 Автосервисы", callback_data="get_services"))
    kb.add(InlineKeyboardButton("🆘 SOS", callback_data="sos_ask"))
    
    if city_key:
        kb.add(
            InlineKeyboardButton("🥇 Спонсорские СТО", callback_data=f"sponsor_sto_{city_key}"),
            InlineKeyboardButton("🥇 Топ комиссар", callback_data=f"sponsor_kom_{city_key}")
        )
    
    return kb


def sos_location_keyboard():
    """Меню выбора геолокации при SOS."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📍 Отправить геолокацию", request_location=True))
    kb.add(KeyboardButton("🔙 Без геолокации (федеральные номера)"))
    kb.add(KeyboardButton("🏠 Главное меню"))
    return kb


def sos_inline_keyboard(city_key: str = ""):
    """Инлайн-меню SOS с номерами и ссылками."""
    kb = InlineKeyboardMarkup()
    
    if city_key:
        kb.add(InlineKeyboardButton("🥇 Локальный комиссар", callback_data=f"sponsor_kom_{city_key}"))
        kb.add(InlineKeyboardButton("🏪 СТО рядом", callback_data=f"sponsor_sto_{city_key}"))
    
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb


def after_diagnostic_keyboard():
    """Меню после завершения диагностики."""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔍 Новая диагностика", callback_data="new_diagnostic"))
    kb.add(InlineKeyboardButton("🏪 Найти СТО", callback_data="get_services"))
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb


def dialog_options_keyboard(options: list, tree_id: str):
    """Инлайн-кнопки для выбора ответа в диалоге."""
    kb = InlineKeyboardMarkup()
    
    for option in options:
        # Обрезаем текст чтобы уместился на кнопке
        btn_text = option[:30] + "..." if len(option) > 30 else option
        callback_data = f"diag_{tree_id}::{option}"
        kb.add(InlineKeyboardButton(btn_text, callback_data=callback_data))
    
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="diag_cancel"))
    return kb
