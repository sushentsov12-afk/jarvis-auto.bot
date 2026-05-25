from catalog import PartItem, ServiceItem


def welcome_text() -> str:
    return (
        "<b>Jarvis Auto</b> — ваш автопомощник.\n\n"
        "Выберите код ошибки OBD, опишите симптом текстом "
        "или задайте вопрос — я подскажу деталь, цену и сервис."
    )


def help_text(ai_enabled: bool) -> str:
    lines = [
        "<b>Команды</b>",
        "/start — главное меню",
        "/help — эта справка",
        "/services — список автосервисов",
        "",
        "<b>Примеры запросов</b>",
        "• <code>P0301</code> — диагностика по коду",
        "• <code>не заводится утром</code>",
        "• <code>стук при торможении</code>",
    ]
    if ai_enabled:
        lines.append("")
        lines.append("Если в базе нет ответа — подключён GigaChat для свободных вопросов.")
    else:
        lines.append("")
        lines.append(
            "Для ответов на свободные вопросы добавьте <code>GIGACHAT_CREDENTIALS</code> в файл .env"
        )
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
    lines = ["<b>Ближайшие автосервисы</b>\n"]
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
        "Попробуйте указать код OBD (например, P0301) или опишите симптом иначе. "
        "Можно воспользоваться кнопками меню ниже."
    )
