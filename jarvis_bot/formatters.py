from catalog import PartItem, ServiceItem


def welcome_text(first_name: str | None = None, username: str | None = None) -> str:
    # Обращение только по имени — ник не показываем
    name_line = f"Привет, <b>{first_name}</b>!\n\n" if first_name else ""

    return (
        f"{name_line}"
        f"<b>Ваша машина говорит. Я перевожу.</b>\n\n"
        f"Опишите симптом своими словами — стук, запах, лампочка — "
        f"и я найду причину от простого к сложному.\n\n"
        f"🔍 <b>Диагностика</b> — опишите симптом или код ошибки\n"
        f"🏪 <b>Автосервисы</b> — СТО рядом с рейтингом\n"
        f"🆘 <b>SOS</b> — ГИБДД и комиссары по геолокации"
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


def format_services(services: list[ServiceItem], city_key: str = "") -> str:
    """
    Список СТО. Если city_key задан — показывает спонсоров с металлическими
    значками поверх обычного списка.
    """
    lines = ["<b>🏪 Автосервисы Йошкар-Олы</b>\n"]

    # Спонсорский блок (если есть для города)
    if city_key:
        try:
            from sponsors import format_sto_sponsors
            sponsor_text = format_sto_sponsors(city_key)
            if sponsor_text:
                lines.append("<b>✨ Партнёры Jarvis Auto</b>")
                lines.append(sponsor_text)
                lines.append("")
                lines.append("─" * 28)
                lines.append("")
        except ImportError:
            pass

    # Обычный список из базы
    lines.append("<b>📋 Другие сервисы</b>")
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
