from catalog import PartItem, ServiceItem


def welcome_text(first_name: str | None = None, username: str | None = None) -> str:
    """Приветствие с учетом имени."""
    name_line = f"Привет, <b>{first_name}</b>!\n\n" if first_name else ""

    return (
        f"{name_line}"
        f"🚗 <b>Ваша машина говорит. Я перевожу.</b>\n\n"
        f"Опишите что-нибудь — <i>стук, запах, лампочка, не заводится</i> — "
        f"и я найду причину от простого к сложному.\n\n"
        f"<b>Главное меню</b> — используйте кнопки ниже. "
        f"Везде есть кнопка «Главное меню» чтобы вернуться."
    )


def help_text(ai_enabled: bool) -> str:
    """Справка с примерами и командами."""
    lines = [
        "📖 <b>КАК ПОЛЬЗОВАТЬСЯ JARVIS AUTO</b>\n",
        
        "<b>🔍 ДИАГНОСТИКА</b>",
        "Опишите симптом своими словами:",
        "• <i>машина не заводится утром</i>",
        "• <i>стук при торможении</i>",
        "• <i>перегрев двигателя</i>",
        "• <i>странный запах из машины</i>\n",
        
        "Или введите код ошибки:",
        "• <code>P0301</code>",
        "• <code>P0420</code>",
        "• <code>C0045</code>\n",
        
        "<b>🚗 МОЕ АВТО</b>",
        "Выберите марку и модель — Джек покажет",
        "типичные ошибки именно для вашей машины.\n",
        
        "<b>📋 ИСТОРИЯ</b>",
        "Все ваши диагностики сохраняются. Быстрый доступ",
        "к прошлым запросам.\n",
        
        "<b>🏪 СЕРВИСЫ</b>",
        "Актуальные СТО с рейтингами и номерами телефонов.\n",
        
        "<b>🆘 SOS</b>",
        "При аварии — номера ГИБДД и местных комиссаров",
        "по вашей геолокации.\n",
    ]
    
    if ai_enabled:
        lines.append(
            "💬 <b>AI-ПОМОЩНИК</b>\n"
            "GigaChat подключён — можете задать любой вопрос про авто.\n"
        )
    
    lines.append("<b>⬅️ ВЕЗДЕ КНОПКА НАЗАД</b>\nВы всегда можете вернуться в главное меню.")
    
    return "\n".join(lines)


def format_my_car(brand: str, model: str, year: str) -> str:
    """Форматирование информации о выбранном авто."""
    return (
        f"🚗 <b>Ваш автомобиль:</b>\n\n"
        f"<code>{brand} {model} ({year})</code>\n\n"
        f"Теперь Джек будет учитывать вашу машину при диагностике "
        f"и показывать типичные ошибки именно для этой модели."
    )


def format_part(part: PartItem, title: str = "Рекомендация") -> str:
    """Форматирование информации о запчасти."""
    code_line = f"<b>Код:</b> <code>{part.id}</code>\n" if part.type == "obd" else ""
    return (
        f"<b>{title}</b>\n\n"
        f"{code_line}"
        f"<b>📦 Деталь:</b> {part.name}\n\n"
        f"<b>📝 Описание:</b>\n{part.description}\n\n"
        f"<b>💰 Цена:</b> {part.price}\n\n"
        f'<a href="{part.link}">🔗 Купить / подробнее</a>'
    )


def format_services(services: list[ServiceItem], city_key: str = "") -> str:
    """Список СТО с красивым форматированием."""
    lines = ["🏪 <b>АВТОСЕРВИСЫ</b>\n"]

    # Спонсорский блок (если есть для города)
    if city_key:
        try:
            from sponsors import format_sto_sponsors
            sponsor_text = format_sto_sponsors(city_key)
            if sponsor_text:
                lines.append("<b>✨ 🥇 ПАРТНЁРЫ JARVIS AUTO</b>\n")
                lines.append(sponsor_text)
                lines.append("\n" + "─" * 40 + "\n")
        except ImportError:
            pass

    # Обычный список из базы
    lines.append("<b>📋 ДОСТУПНЫЕ СЕРВИСЫ</b>\n")
    for i, s in enumerate(services, 1):
        lines.append(
            f"<b>{i}. {s.name}</b>  ⭐ {s.rating}\n"
            f"📍 {s.address}\n"
            f"🕒 {s.work_time}\n"
            f"📞 <code>{s.phone}</code>\n"
        )
    return "\n".join(lines)


def format_ai_fallback(user_text: str) -> str:
    """Сообщение когда диагностика не нашла точного результата."""
    return (
        f"🤔 По запросу <i>«{user_text}»</i> в каталоге точного совпадения нет.\n\n"
        f"<b>Попробуйте:</b>\n"
        f"• Введите код OBD (например, <code>P0301</code>)\n"
        f"• Опишите симптом иначе\n"
        f"• Используйте кнопки меню выше\n\n"
        f"<i>Или нажмите 🔍 ДИАГНОСТИКА и выберите вариант из диалога.</i>"
    )


def format_typical_issues(brand: str, model: str, year: str, issues: list) -> str:
    """Форматирование типичных ошибок для конкретного авто."""
    if not issues:
        return (
            f"📌 <b>Типичные ошибки {brand} {model} ({year})</b>\n\n"
            f"<i>К сожалению, типичных ошибок для этой модели нет в базе.</i>"
        )
    
    lines = [f"📌 <b>Типичные ошибки {brand} {model} ({year}):</b>\n"]
    
    # Группируем по urgency
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_issues = sorted(issues, key=lambda x: urgency_order.get(x.urgency, 9))
    
    urgency_emoji = {
        "critical": "🚨",
        "high": "⚠️",
        "medium": "🔧",
        "low": "ℹ️"
    }
    
    urgency_label = {
        "critical": "КРИТИЧНО",
        "high": "Срочно",
        "medium": "Плановый",
        "low": "Низкий"
    }
    
    for issue in sorted_issues[:8]:  # Показываем топ-8
        emoji = urgency_emoji.get(issue.urgency, "🔧")
        label = urgency_label.get(issue.urgency, "")
        
        lines.append(
            f"{emoji} <b>{issue.name}</b>  ({label})\n"
            f"   {issue.description}\n"
            f"   💰 {issue.price_range}\n"
        )
    
    return "\n".join(lines)


def format_diagnostic_start(car_info: str = "") -> str:
    """Приветствие перед диагностикой."""
    car_line = f"\n🚗 Диагностирую для: <b>{car_info}</b>" if car_info else ""
    
    return (
        f"🔍 <b>ДИАГНОСТИКА</b>{car_line}\n\n"
        f"Опишите симптом — я задам уточняющие вопросы "
        f"и точно определю причину.\n\n"
        f"<b>Примеры:</b>\n"
        f"• машина не заводится\n"
        f"• стук в подвеске\n"
        f"• горит лампочка на панели\n"
        f"• странный запах из машины"
    )
