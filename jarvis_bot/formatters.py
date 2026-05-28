from catalog import PartItem, ServiceItem


def welcome_text() -> str:
    return (
        "<b>Jarvis Auto</b> — ваш автопомощник.\n\n"
        "🔍 <b>Диагностика</b> — введите код OBD или опишите симптом\n"
        "🏪 <b>Автосервисы</b> — ближайшие СТО с рейтингом\n"
        "🆘 <b>SOS</b> — номера ГИБДД и аварийных комиссаров\n\n"
        "Просто напишите проблему — я помогу."
    )


def help_text(ai_enabled: bool) -> str:
    lines = [
        "<b>Как пользоваться Jarvis Auto</b>\n",
        "<b>Команды</b>",
        "/start — главное меню",
        "/services — список автосервисов",
        "/sos — экстренные номера",
        "/help — эта справка",
        "",
        "<b>Примеры запросов</b>",
        "• <code>P0301</code> — диагностика по OBD-коду",
        "• <code>не заводится утром</code>",
        "• <code>стук при торможении</code>",
        "• <code>перегрев двигателя</code>",
    ]
    if ai_enabled:
        lines += [
            "",
            "💬 GigaChat подключён — можете задать любой вопрос по автомобилю.",
        ]
    else:
        lines += [
            "",
            "ℹ️ Для свободных вопросов добавьте <code>GIGACHAT_CREDENTIALS</code> в .env",
        ]
    return "\n".join(lines)


def format_part(part: PartItem, title: str = "Рекомендация") -> str:
    code_line = f"<b>Код:</b> {part.id}\n" if part.type == "obd" else ""
    return (
        f"<b>{title}</b>\n\n"
        f"{code_line}"
        f"<b>Деталь:</b> {part.name}\n"
        f"<b>Описание:</b> {part.description}\n"
        f"<b>Цена:</b> {part.price}\n"
        f'<a href="{part.link}">Купить / подробнее</a>'
    )


def format_services(services: list[ServiceItem]) -> str:
    lines = ["<b>🏪 Ближайшие автосервисы</b>\n"]
    for i, s in enumerate(services, 1):
        lines.append(
            f"{i}. <b>{s.name}</b> ★ {s.rating}\n"
            f"📍 {s.address}\n"
            f"🕒 {s.work_time}\n"
            f"📞 {s.phone}\n"
        )
    return "\n".join(lines)


def format_ai_fallback(user_text: str) -> str:
    return (
        f"По запросу «{user_text}» в каталоге точного совпадения нет.\n\n"
        "Попробуйте указать код OBD (например, <code>P0301</code>) "
        "или опишите симптом иначе. "
        "Воспользуйтесь кнопками меню ниже."
    )
