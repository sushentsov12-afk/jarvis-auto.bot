from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from vehicle_db import vehicle_db
from user_vehicle import user_vehicle


def main_menu():
    """Главное меню."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🚗 Моё авто"))
    kb.add(KeyboardButton("🔧 Диагностика"))
    kb.add(KeyboardButton("ℹ️ Помощь"))
    return kb


def brand_keyboard():
    """Клавиатура выбора бренда."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    brands = vehicle_db.get_brands()

    row = []
    for brand in brands:
        row.append(KeyboardButton(brand))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)

    kb.add(KeyboardButton("⬅️ Назад"))
    return kb


def model_keyboard(brand: str):
    """Клавиатура выбора модели по бренду."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    models = vehicle_db.get_models(brand)

    row = []
    for model in models:
        row.append(KeyboardButton(model))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)

    kb.add(KeyboardButton("⬅️ Назад"))
    return kb


def my_car_menu(user_id: int):
    """Меню 'Моё авто' — показывает текущее авто или предлагает выбрать."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    if user_vehicle.has_vehicle(user_id):
        car = user_vehicle.get_vehicle(user_id)
        kb.add(KeyboardButton(f"🚗 {car['brand']} {car['model']}"))
        kb.add(KeyboardButton("🔄 Изменить авто"))
        kb.add(KeyboardButton("❌ Удалить авто"))
    else:
        kb.add(KeyboardButton("➕ Добавить авто"))

    kb.add(KeyboardButton("⬅️ Назад"))
    return kb


def confirm_vehicle_keyboard():
    """Подтверждение выбора авто."""
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✔ Подтвердить", callback_data="confirm_vehicle"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_vehicle")
    )
    return kb

