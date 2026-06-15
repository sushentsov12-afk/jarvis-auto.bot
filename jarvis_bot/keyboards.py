from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

BRANDS = [
    "Toyota", "BMW", "Mercedes-Benz", "Audi", "Volkswagen",
    "Hyundai", "Kia", "Nissan", "Honda", "Ford",
    "Lada", "Geely", "Chery", "BYD", "Tesla",
    "Mazda", "Skoda", "Renault", "Peugeot", "Mitsubishi"
]

MODELS = {
    "Toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser", "Highlander"],
    "BMW": ["3 Series", "5 Series", "X5", "X3", "7 Series"],
    "Mercedes-Benz": ["C-Class", "E-Class", "GLE", "A-Class", "S-Class"],
    "Audi": ["A4", "A6", "Q5", "Q7", "A3"],
    "Volkswagen": ["Golf", "Passat", "Tiguan", "Polo", "Touareg"],
    "Hyundai": ["Solaris", "Tucson", "Creta", "Santa Fe", "i30"],
    "Kia": ["Rio", "Sportage", "Cerato", "Sorento", "K5"],
    "Nissan": ["Qashqai", "X-Trail", "Almera", "Patrol", "Murano"],
    "Honda": ["Civic", "CR-V", "Accord", "HR-V", "Pilot"],
    "Ford": ["Focus", "Fusion", "Mondeo", "Kuga", "Explorer", "Ranger"],
    "Lada": ["Granta", "Vesta", "XRAY", "Largus", "Niva"],
    "Geely": ["Atlas", "Coolray", "Emgrand", "Tugella", "Monjaro"],
    "Chery": ["Tiggo 7", "Tiggo 4", "Tiggo 8", "Arrizo 5", "Omoda 5"],
    "BYD": ["Han", "Tang", "Seal", "Atto 3", "Dolphin"],
    "Tesla": ["Model 3", "Model Y", "Model S", "Model X", "Cybertruck"],
    "Mazda": ["CX-5", "3", "6", "CX-9", "MX-5"],
    "Skoda": ["Octavia", "Kodiaq", "Superb", "Rapid", "Fabia"],
    "Renault": ["Logan", "Duster", "Sandero", "Arkana", "Kaptur"],
    "Peugeot": ["408", "3008", "5008", "2008", "508"],
    "Mitsubishi": ["Outlander", "ASX", "Eclipse Cross", "L200", "Pajero"],
}

YEARS = [str(y) for y in range(2024, 1985, -1)]


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🔍 ДИАГНОСТИКА"),
        KeyboardButton("🚗 Моё авто"),
        KeyboardButton("📋 История"),
        KeyboardButton("🏪 Сервисы"),
        KeyboardButton("🆘 SOS"),
        KeyboardButton("ℹ️ Справка"),
        KeyboardButton("💬 Обратная связь"),
        KeyboardButton("🔧 Спросить механика"),
        KeyboardButton("📚 FAQ — частые вопросы"),
    )
    return kb


def back_to_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(KeyboardButton("🏠 Главное меню"))
    return kb


def diagnostic_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("✍️ Описать симптом"),
        KeyboardButton("💻 Ввести код OBD"),
        KeyboardButton("🏠 Главное меню"),
    )
    return kb


def my_car_menu_keyboard(has_car: bool) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if has_car:
        kb.add(
            KeyboardButton("📌 Типичные ошибки"),
            KeyboardButton("🔄 Изменить авто"),
            KeyboardButton("❌ Удалить авто"),
            KeyboardButton("🏠 Главное меню"),
        )
    else:
        kb.add(
            KeyboardButton("➕ Выбрать авто"),
            KeyboardButton("🏠 Главное меню"),
        )
    return kb


def brand_inline_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(b, callback_data=f"brand_{b}") for b in BRANDS]
    kb.add(*buttons)
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb


def model_inline_keyboard(brand: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    models = MODELS.get(brand, ["Другая"])
    buttons = [InlineKeyboardButton(m, callback_data=f"model_{brand}_{m}") for m in models]
    kb.add(*buttons)
    kb.add(
        InlineKeyboardButton("⬅️ К маркам", callback_data="select_brand"),
        InlineKeyboardButton("🏠 Меню", callback_data="main_menu"),
    )
    return kb


def year_inline_keyboard(brand: str, model: str, page: int = 0) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=4)
    page_size = 16
    start = page * page_size
    end = start + page_size
    page_years = YEARS[start:end]
    # Используем | как разделитель чтобы не резать бренды с пробелами
    buttons = [InlineKeyboardButton(y, callback_data=f"year|{brand}|{model}|{y}") for y in page_years]
    kb.add(*buttons)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Новее", callback_data=f"ypage|{brand}|{model}|{page-1}"))
    if end < len(YEARS):
        nav.append(InlineKeyboardButton("Старше ▶️", callback_data=f"ypage|{brand}|{model}|{page+1}"))
    if nav:
        kb.add(*nav)
    kb.add(
        InlineKeyboardButton("⬅️ К моделям", callback_data=f"select_model_{brand}"),
        InlineKeyboardButton("🏠 Меню", callback_data="main_menu"),
    )
    return kb


def main_inline_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔍 Новая диагностика", callback_data="new_diagnostic"),
        InlineKeyboardButton("🏪 Сервисы рядом", callback_data="get_services"),
    )
    return kb


def after_diagnostic_keyboard(show_simplify: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    if show_simplify:
        kb.add(InlineKeyboardButton("🔄 Объясни проще", callback_data="explain_simpler"))
    kb.add(
        InlineKeyboardButton("🔍 Ещё диагностика", callback_data="new_diagnostic"),
        InlineKeyboardButton("🏪 Найти сервис", callback_data="get_services"),
        InlineKeyboardButton("📋 История", callback_data="show_history"),
    )
    return kb


def sos_location_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    kb.add(
        KeyboardButton("📍 Отправить геолокацию", request_location=True),
        KeyboardButton("🔙 Без геолокации (федеральные номера)"),
        KeyboardButton("🏠 Главное меню"),
    )
    return kb


def sos_inline_keyboard(city_key: str = "") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    if city_key:
        kb.add(
            InlineKeyboardButton("🥇 СТО партнёры рядом", callback_data=f"sponsor_sto_{city_key}"),
            InlineKeyboardButton("🚗 Эвакуатор партнёры", callback_data=f"sponsor_kom_{city_key}"),
        )
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb


def dialog_options_keyboard(options: list, tree_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for opt in options:
        kb.add(InlineKeyboardButton(opt, callback_data=f"diag_{tree_id}::{opt[:50]}"))
    kb.add(InlineKeyboardButton("❌ Отменить", callback_data="diag_cancel"))
    return kb


def confirm_vehicle_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Сохранить", callback_data="confirm_vehicle"),
        InlineKeyboardButton("🔄 Изменить", callback_data="select_brand"),
    )
    return kb


# Legacy aliases
def brand_keyboard(brands): return brand_inline_keyboard()
def model_keyboard(models): return main_inline_keyboard()
def year_keyboard(): return main_inline_keyboard()


def admin_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("🔍 ДИАГНОСТИКА"),
        KeyboardButton("🚗 Моё авто"),
        KeyboardButton("📋 История"),
        KeyboardButton("🏪 Сервисы"),
        KeyboardButton("🆘 SOS"),
        KeyboardButton("ℹ️ Справка"),
        KeyboardButton("💬 Обратная связь"),
        KeyboardButton("🛠 Админ панель"),
    )
    return kb


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👥 Пользователи", callback_data="admin_stats"),
        InlineKeyboardButton("❓ Нераспознанные", callback_data="admin_unknown"),
        InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton("🗄 База диагностики", callback_data="admin_db_info"),
        InlineKeyboardButton("🔧 Вопросы механику", callback_data="admin_mechanic"),
        InlineKeyboardButton("🏆 Эксперты", callback_data="admin_experts"),
    )
    return kb

def level_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора уровня знания авто."""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🔰 Новичок — пользуюсь меньше года", callback_data="level_novice"),
        InlineKeyboardButton("🚗 Автолюбитель — знаю базовые вещи", callback_data="level_driver"),
        InlineKeyboardButton("🔧 Автогараж — делаю несложный ремонт", callback_data="level_garage"),
        InlineKeyboardButton("⚙️ Автомеханик — могу починить машину", callback_data="level_mechanic"),
        InlineKeyboardButton("🏆 Автоэксперт — знаю всё об авто", callback_data="level_expert"),
    )
    return kb


def expert_question_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Кнопки для эксперта — взять вопрос или пропустить."""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Ответить", callback_data=f"eq_take_{question_id}"),
        InlineKeyboardButton("➡️ Пропустить", callback_data=f"eq_skip_{question_id}"),
    )
    return kb


def rate_answer_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Пользователь оценивает ответ эксперта."""
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("👍 Помогло!", callback_data=f"rate_good_{question_id}"),
        InlineKeyboardButton("🤔 Частично", callback_data=f"rate_partial_{question_id}"),
        InlineKeyboardButton("👎 Не помогло", callback_data=f"rate_bad_{question_id}"),
    )
    return kb



def faq_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура FAQ для новичков."""
    from faq import FAQ
    kb = InlineKeyboardMarkup(row_width=1)
    for i, item in enumerate(FAQ):
        kb.add(InlineKeyboardButton(item["question"], callback_data=f"faq_{i}"))
    return kb


def faq_back_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("◀️ Назад к FAQ", callback_data="faq_menu"),
        InlineKeyboardButton("🔍 Диагностика", callback_data="new_diagnostic"),
    )
    return kb
