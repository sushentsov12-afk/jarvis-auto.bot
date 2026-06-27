import logging
import sys
from telebot import TeleBot, apihelper
from telebot.types import CallbackQuery, Message

import ai_assistant
from diagnostic import search_by_phrase, format_diagnostic
from user_history import add_entry, format_history, has_history
from dialog_engine import find_tree, get_node, format_diagnosis, URGENCY_EMOJI, DialogState
from dialog_state import set_state, get_state, clear_state, set_last_diagnostic, get_last_diagnostic
from catalog import find_best_match, load_parts, load_services
from config import BOT_TOKEN
from network import check_telegram, resolve_proxy
from user_vehicle import user_vehicle
from formatters import (
    format_ai_fallback, format_part, format_services, help_text,
    welcome_text, format_my_car, format_diagnostic_start, format_typical_issues
)
from keyboards import (
    admin_keyboard, admin_panel_keyboard,
    level_keyboard, expert_question_keyboard, rate_answer_keyboard,
    main_reply_keyboard, back_to_menu_keyboard, diagnostic_menu_keyboard,
    my_car_menu_keyboard, main_inline_keyboard, sos_location_keyboard,
    sos_inline_keyboard, after_diagnostic_keyboard, dialog_options_keyboard,
    brand_inline_keyboard, model_inline_keyboard, year_inline_keyboard,
    confirm_vehicle_keyboard
)
from sos_geo import format_sos

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis")

PARTS = load_parts()
SERVICES = load_services()
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")


# ─── ГЛАВНОЕ МЕНЮ ────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    user = message.from_user
    if user:
        from broadcaster import register_user
        register_user(user.id, username=user.username or "", first_name=user.first_name or "")

    import os
    is_admin = user and str(user.id) == str(os.getenv("ADMIN_ID", ""))

    # Онбординг — если новый пользователь
    if user:
        from user_profile import is_onboarded
        if not is_onboarded(user.id) and not is_admin:
            from keyboards import level_keyboard
            name = user.first_name or "Друг"
            bot.send_message(
                message.chat.id,
                f"🚗 <b>Привет, {name}! Я Джек — автомобильный ассистент.</b>\n\n"
                "Помогу диагностировать проблемы, подберу сервис и отвечу на вопросы об авто.\n\n"
                "📋 <b>Сначала — один вопрос:</b>\n"
                "Как хорошо вы разбираетесь в автомобилях?",
                reply_markup=level_keyboard()
            )
            return

    bot.send_message(
        message.chat.id,
        welcome_text(first_name=user.first_name if user else None),
        reply_markup=admin_keyboard() if is_admin else main_reply_keyboard(),
    )

@bot.message_handler(commands=["profile"])
def cmd_profile(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    from user_profile import get_profile, LEVELS, format_level_badge
    p = get_profile(user.id)
    car = user_vehicle.get_vehicle(user.id)
    car_str = f"{car['brand']} {car['model']} ({car['year']})" if car else "не указано"

    if not p:
        from keyboards import level_keyboard
        bot.send_message(message.chat.id, "Выберите ваш уровень:", reply_markup=level_keyboard())
        return

    level = p.get("level", "novice")
    badge = format_level_badge(level)
    level_desc = LEVELS.get(level, {}).get("desc", "")
    rating = p.get("rating", 0.0)
    answers = p.get("answers_count", 0)

    expert_block = ""
    if level in ("mechanic", "expert"):
        stars = "⭐" * round(rating) if rating else "нет оценок"
        expert_block = (
            f"\n\n🏆 <b>Статистика эксперта:</b>\n"
            f"Ответов: {answers} | Рейтинг: {stars} ({rating:.1f})"
        )

    bot.send_message(
        message.chat.id,
        f"👤 <b>Ваш профиль</b>\n\n"
        f"{badge}\n<i>{level_desc}</i>\n\n"
        f"🚗 Авто: {car_str}"
        f"{expert_block}\n\n"
        f"Изменить уровень: /setlevel",
        reply_markup=main_reply_keyboard()
    )


@bot.message_handler(commands=["setlevel"])
def cmd_setlevel(message: Message) -> None:
    bot.send_message(
        message.chat.id,
        "Выберите новый уровень знания авто:",
        reply_markup=level_keyboard()
    )


@bot.message_handler(commands=["admin"])
def cmd_admin(message: Message) -> None:
    import os
    user = message.from_user
    if not user or str(user.id) != str(os.getenv("ADMIN_ID", "")):
        return
    bot.send_message(message.chat.id, "🛠 <b>Панель администратора</b>", reply_markup=admin_keyboard())

@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message: Message) -> None:
    import os
    admin_id = str(os.getenv("ADMIN_ID", ""))
    user_id = str(message.from_user.id) if message.from_user else ""
    if not admin_id or user_id != admin_id:
        return
    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        bot.send_message(message.chat.id, "Укажи текст: /broadcast Текст")
        return
    bot.send_message(message.chat.id, "Начинаю рассылку...")
    from broadcaster import broadcast, get_user_count
    result = broadcast(bot, text)
    bot.send_message(message.chat.id,
        f"Рассылка завершена!\n"
        f"Пользователей: {get_user_count()}\n"
        f"Отправлено: {result['sent']}\n"
        f"Ошибок: {result['failed']}")

@bot.message_handler(commands=["unknown"])
def cmd_unknown(message: Message) -> None:
    """Топ нераспознанных запросов с кнопками привязки к теме."""
    import os
    admin_id = str(os.getenv("ADMIN_ID", ""))
    user_id = str(message.from_user.id) if message.from_user else ""
    if not admin_id or user_id != admin_id:
        return
    _send_unknown_item(message.chat.id, offset=0)


def _send_unknown_item(chat_id: int, offset: int = 0) -> None:
    """Отправляет одну нераспознанную фразу с кнопками выбора темы."""
    from clarify import get_unknown_queries
    from dialog_engine import DIALOG_TREES

    TREE_LABELS = {
        "heavy_wheel":      "🛞 Тяжёлый руль",
        "wont_start":       "🔑 Не заводится",
        "brake_noise":      "🛑 Тормоза",
        "overheat":         "🌡 Перегрев",
        "suspension_knock": "🔩 Стук подвески",
        "gearbox":          "⚙️ Коробка передач",
        "smell":            "💨 Запах",
        "vibration_speed":  "📳 Вибрация",
        "electrics":        "⚡ Электрика",
        "aircon":           "❄️ Кондиционер",
        "oil_leak":         "🛢 Масло",
    }

    queries = get_unknown_queries(50)
    # убираем уже привязанные (offset = текущий индекс)
    if offset >= len(queries):
        bot.send_message(chat_id, "✅ Нераспознанных запросов больше нет!")
        return

    q = queries[offset]
    phrase = q["query"]
    count = q["count"]

    kb = InlineKeyboardMarkup(row_width=2)
    for tree_id, label in TREE_LABELS.items():
        kb.add(InlineKeyboardButton(
            label,
            callback_data=f"unk_assign::{offset}::{tree_id}"
        ))
    kb.add(
        InlineKeyboardButton("⏭ Пропустить", callback_data=f"unk_skip::{offset}"),
        InlineKeyboardButton("🗑 Удалить", callback_data=f"unk_delete::{offset}"),
    )

    bot.send_message(
        chat_id,
        f"❓ <b>Нераспознанная фраза</b> [{offset+1}/{len(queries)}]\n\n"
        f"<code>{phrase}</code>\n\n"
        f"Встречалась: <b>{count}x</b>\n\n"
        f"К какой теме относится?",
        reply_markup=kb
    )

@bot.message_handler(commands=["stats"])
def cmd_stats(message: Message) -> None:
    import os
    admin_id = str(os.getenv("ADMIN_ID", ""))
    user_id = str(message.from_user.id) if message.from_user else ""
    if not admin_id or user_id != admin_id:
        return
    from broadcaster import get_user_count
    bot.send_message(message.chat.id, f"Пользователей: {get_user_count()}")

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def go_main_menu(message: Message) -> None:
    import os
    user = message.from_user
    if user:
        clear_state(user.id)
    from user_profile import get_profile, format_level_badge
    badge = ""
    is_admin_user = user and str(user.id) == str(os.getenv("ADMIN_ID", ""))
    if user:
        p = get_profile(user.id)
        if p:
            badge = format_level_badge(p.get("level", "novice"))
    bot.send_message(
        message.chat.id,
        welcome_text(first_name=user.first_name if user else None, level_badge=badge),
        reply_markup=admin_keyboard() if is_admin_user else main_reply_keyboard(),
    )

@bot.message_handler(func=lambda m: m.text == "ℹ️ Справка")
def btn_help(message: Message) -> None:
    bot.send_message(
        message.chat.id,
        help_text(ai_assistant.is_enabled()),
        reply_markup=back_to_menu_keyboard(),
    )

@bot.message_handler(func=lambda m: m.text == "📚 FAQ — частые вопросы")
def btn_faq(message: Message) -> None:
    from faq import FAQ
    from keyboards import faq_keyboard
    text = (
        "📚 <b>FAQ — Частые вопросы новичков</b>\n\n"
        "Выберите вопрос — я отвечу простым языком:"
    )
    bot.send_message(message.chat.id, text, reply_markup=faq_keyboard())


# ─── ДИАГНОСТИКА ─────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🔍 ДИАГНОСТИКА")
def btn_diagnostics(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    car = user_vehicle.get_vehicle(user_id)
    car_str = f"{car['brand']} {car['model']} ({car['year']})" if car else ""
    bot.send_message(
        message.chat.id,
        format_diagnostic_start(car_str),
        reply_markup=diagnostic_menu_keyboard(),
    )

@bot.message_handler(func=lambda m: m.text in ("✍️ Описать симптом", "💻 Ввести код OBD"))
def start_diagnostic_input(message: Message) -> None:
    if message.text == "✍️ Описать симптом":
        bot.send_message(message.chat.id, "Опишите что происходит с машиной:", reply_markup=back_to_menu_keyboard())
    else:
        bot.send_message(message.chat.id, "Введите код OBD (например, P0301):", reply_markup=back_to_menu_keyboard())
    bot.register_next_step_handler(message, process_diagnostic_input)

def process_diagnostic_input(message: Message) -> None:
    if message.text in ("🏠 Главное меню", "/start"):
        return go_main_menu(message)

    user_id = message.from_user.id if message.from_user else 0
    text = (message.text or "").strip()
    if not text:
        return
    bot.send_chat_action(message.chat.id, "typing")

    # 1. Сначала диалоговое дерево (уточняющие вопросы)
    tree = find_tree(text)
    if tree:
        state = DialogState(tree_id=tree.tree_id, current_node_id=tree.root_node_id)
        set_state(user_id, state)
        root_node = get_node(tree, tree.root_node_id)
        hint = f"\n<i>{root_node.hint}</i>" if root_node and root_node.hint else ""
        bot.send_message(
            message.chat.id,
            f"{tree.intro}\n\n<b>{root_node.question}</b>{hint}",
            reply_markup=dialog_options_keyboard(root_node.options, tree.tree_id),
        )
        return

    # 2. Поиск по диагностической базе (212+ проблем)
    from diagnostic import smart_search
    result_smart = smart_search(text)
    if result_smart:
        from formatters import format_diagnostic_for_level
        from user_profile import get_profile
        # Уровень пользователя для адаптации ответа
        profile = get_profile(user_id)
        level = profile.get("level", "novice") if profile else "novice"
        # Проверяем авто пользователя
        car = user_vehicle.get_vehicle(user_id)
        car_note = ""
        if car:
            car_note = f"\n\n🚗 <i>Для {car['brand']} {car['model']}: уточните у механика применимость.</i>"
        add_entry(user_id, text, result_smart["technical_name"], result_smart.get("urgency", "medium"))
        answer = format_diagnostic_for_level(result_smart, level)
        show_simplify = level not in ("novice", "driver")
        set_last_diagnostic(user_id, {"kind": "smart", "result": result_smart})
        bot.send_message(
            message.chat.id,
            f"<b>🔎 Джек определил проблему:</b>\n\n{answer}{car_note}",
            reply_markup=after_diagnostic_keyboard(show_simplify=show_simplify)
        )
        return

    # 3. Нечёткий поиск по каталогу запчастей
    part = find_best_match(text, PARTS)
    if part:
        title = f"Диагностика {part.id}" if part.type == "obd" else "Подбор по симптому"
        bot.send_message(message.chat.id, format_part(part, title=title), reply_markup=after_diagnostic_keyboard())
        add_entry(user_id, text, part.name, "medium")
        return

    # 4. Не нашли — сохраняем, анализируем через GigaChat, уточняющие вопросы
    from clarify import save_unknown_query, build_clarify_text, CLARIFY_QUESTIONS
    save_unknown_query(user_id, text)

    # Пробуем проанализировать через GigaChat и сохранить в базу
    if ai_assistant.is_enabled():
        try:
            saved = ai_assistant.analyze_and_save(text)
            if saved:
                # Нашли и сохранили — отвечаем сразу
                from diagnostic import search_by_phrase
                from diagnostic import format_diagnostic as fmt_diag
                result, score = search_by_phrase(text, threshold=30)
                if result:
                    add_entry(user_id, text, result["technical_name"], result.get("urgency", "medium"))
                    bot.send_message(
                        message.chat.id,
                        f"<b>🔎 Джек определил проблему:</b>\n\n{fmt_diag(result)}",
                        reply_markup=after_diagnostic_keyboard()
                    )
                    return
        except Exception:
            logger.exception("GigaChat analyze failed")

    # Если GigaChat не помог — уточняющие вопросы
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    q = CLARIFY_QUESTIONS[0]
    kb = InlineKeyboardMarkup(row_width=2)
    for opt in q["options"]:
        kb.add(InlineKeyboardButton(opt, callback_data=f"clarify_0_{opt[:40]}_{text[:30]}"))
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))

    bot.send_message(
        message.chat.id,
        build_clarify_text(text) + f"\n\n{q['question']}",
        reply_markup=kb
    )


# ─── МОЁ АВТО (inline callbacks) ─────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🚗 Моё авто")
def btn_my_car(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    car = user_vehicle.get_vehicle(user_id)
    if car:
        bot.send_message(message.chat.id, format_my_car(car['brand'], car['model'], car['year']), reply_markup=my_car_menu_keyboard(True))
    else:
        bot.send_message(message.chat.id, "🚗 <b>Выберите ваш автомобиль</b>\n\nЭто поможет Джеку давать точные советы.", reply_markup=my_car_menu_keyboard(False))

@bot.message_handler(func=lambda m: m.text == "➕ Выбрать авто")
def select_brand_msg(message: Message) -> None:
    bot.send_message(message.chat.id, "🚗 <b>Выберите марку автомобиля:</b>", reply_markup=brand_inline_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔄 Изменить авто")
def change_car(message: Message) -> None:
    bot.send_message(message.chat.id, "🚗 <b>Выберите марку автомобиля:</b>", reply_markup=brand_inline_keyboard())

@bot.message_handler(func=lambda m: m.text == "❌ Удалить авто")
def delete_car(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    user_vehicle.clear_vehicle(user_id)
    bot.send_message(message.chat.id, "❌ Авто удалено.", reply_markup=my_car_menu_keyboard(False))

@bot.message_handler(func=lambda m: m.text == "📌 Типичные ошибки")
def show_typical_issues(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    car = user_vehicle.get_vehicle(user_id)
    if not car:
        bot.send_message(message.chat.id, "Сначала выберите авто в меню 🚗 Моё авто", reply_markup=my_car_menu_keyboard(False))
        return
    from vehicle_db import get_typical_issues
    issues = get_typical_issues(car['brand'], car['model'])
    bot.send_message(message.chat.id, format_typical_issues(car['brand'], car['model'], car['year'], issues), reply_markup=back_to_menu_keyboard())


# ─── ВОПРОС МЕХАНИКУ ────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🔧 Спросить механика")
def btn_ask_mechanic(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    car = user_vehicle.get_vehicle(user_id)
    car_str = f"{car['brand']} {car['model']} ({car['year']})" if car else "не указано"

    text = (
        "🔧 <b>Спросить механика</b>\n\n"
        "Опытный механик ответит на ваш вопрос лично.\n\n"
        f"🚗 Ваше авто: <b>{car_str}</b>\n\n"
        "Напишите ваш вопрос:"
    )
    bot.send_message(message.chat.id, text, reply_markup=back_to_menu_keyboard())
    bot.register_next_step_handler(message, process_mechanic_question)


def process_mechanic_question(message: Message) -> None:
    if message.text in ("🏠 Главное меню", "/start"):
        return go_main_menu(message)

    user = message.from_user
    user_id = user.id if user else 0
    question = (message.text or "").strip()
    if not question:
        return

    from mechanic import save_question, format_question_for_admin
    import os

    car = user_vehicle.get_vehicle(user_id)
    car_info = f"{car['brand']} {car['model']} ({car['year']})" if car else ""

    # Сохраняем вопрос
    q_id = save_question(
        user_id=user_id,
        username=user.username or "" if user else "",
        first_name=user.first_name or "" if user else "",
        car_info=car_info,
        question=question,
        chat_id=message.chat.id
    )

    # Отправляем подтверждение пользователю
    bot.send_message(
        message.chat.id,
        "🔧 <b>Вопрос отправлен механику!</b>\n\n"
        "Обычно отвечаем в течение нескольких часов.\n"
        "Ответ придёт прямо в этот чат.",
        reply_markup=main_reply_keyboard()
    )

    # 1. Пересылаем администратору
    admin_id = os.getenv("ADMIN_ID", "")
    if admin_id:
        from mechanic import format_question_for_admin, get_question
        q = get_question(q_id)
        try:
            bot.send_message(int(admin_id), format_question_for_admin(q))
        except Exception as e:
            logger.warning("Не удалось отправить вопрос админу: %s", e)

    # 2. Рассылаем всем экспертам и механикам
    from mechanic import notify_experts
    sent = notify_experts(bot, q_id)
    if sent > 0:
        logger.info("Вопрос #%d разослан %d экспертам", q_id, sent)


# ─── ДИАГНОСТИКА ПО ФОТО ─────────────────────────────────────────────────────

@bot.message_handler(content_types=["photo"])
def on_photo(message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    bot.send_chat_action(message.chat.id, "typing")

    # Берём фото наилучшего качества
    photo = message.photo[-1]
    file_info = bot.get_file(photo.file_id)
    image_bytes = bot.download_file(file_info.file_path)

    bot.send_message(
        message.chat.id,
        "📸 Фото получено. Джек анализирует...",
    )
    bot.send_chat_action(message.chat.id, "typing")

    from photo_diagnosis import analyze_photo, save_photo_result, format_photo_result
    result = analyze_photo(image_bytes)

    if not result:
        bot.send_message(
            message.chat.id,
            "\U0001f614 Не удалось проанализировать фото.\n\n"
            "Попробуйте:\n"
            "\u2022 Сделать фото чётче и ближе\n"
            "\u2022 Описать проблему текстом через \U0001f50d ДИАГНОСТИКА",
            reply_markup=diagnostic_menu_keyboard()
        )
        return

    if not result.get("found"):
        bot.send_message(
            message.chat.id,
            "\U0001f914 На фото не видно автомобильной проблемы.\n\n"
            f"<i>Вижу: {result.get('what_i_see', 'не определено')}</i>\n\n"
            "Попробуйте сфотографировать:\n"
            "\u2022 Место утечки или ржавчины\n"
            "\u2022 Выхлопную трубу (дым)\n"
            "\u2022 Тормозные колодки / диски\n"
            "\u2022 Ремень или шланги под капотом\n"
            "\u2022 Экран OBD сканера с кодом ошибки",
            reply_markup=diagnostic_menu_keyboard()
        )
        return

    # Сохраняем в базу
    save_photo_result(result)
    add_entry(user_id, f"фото: {result.get('symptom', '')}", result.get("technical_name", ""), result.get("urgency", "medium"))

    text = format_photo_result(result)
    bot.send_message(message.chat.id, text, reply_markup=after_diagnostic_keyboard())


# ─── ИСТОРИЯ ─────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "📋 История")
def btn_history(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    bot.send_message(message.chat.id, format_history(user_id), reply_markup=back_to_menu_keyboard())


# ─── АДМИН ПАНЕЛЬ ────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🛠 Админ панель")
def btn_admin_panel(message: Message) -> None:
    import os
    user = message.from_user
    if not user or str(user.id) != str(os.getenv("ADMIN_ID", "")):
        return
    from broadcaster import get_user_count
    from clarify import get_unknown_queries
    import json
    import os as _os; db = json.load(open(_os.path.join(_os.path.dirname(__file__), "data", "diagnostic_base.json"), encoding="utf-8"))
    unknown = get_unknown_queries(5)
    top = "\n".join(f"  • [{q['count']}x] {q['query']}" for q in unknown) or "  Нет"
    text = (
        "🛠 <b>Панель администратора Jarvis Auto</b>\n\n"
        f"👥 Пользователей: <b>{get_user_count()}</b>\n"
        f"🗄 Записей в базе диагностики: <b>{len(db)}</b>\n\n"
        f"❓ <b>Топ нераспознанных запросов:</b>\n{top}"
    )
    from keyboards import admin_panel_keyboard
    bot.send_message(message.chat.id, text, reply_markup=admin_panel_keyboard())


# ─── ОБРАТНАЯ СВЯЗЬ ─────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "💬 Обратная связь")
def btn_feedback(message: Message) -> None:
    text = (
        "💬 <b>Обратная связь</b>\n\n"
        "Напишите ваше пожелание, предложение или благодарность — "
        "оно сразу уйдёт администратору.\n\n"
        "<i>Примеры:</i>\n"
        "• Хочу добавить мою марку авто\n"
        "• Не нашёл ответ на вопрос про...\n"
        "• Спасибо, очень помогло! 🙏"
    )
    bot.send_message(message.chat.id, text, reply_markup=back_to_menu_keyboard())
    bot.register_next_step_handler(message, process_feedback)

def process_feedback(message: Message) -> None:
    if message.text in ("🏠 Главное меню", "/start"):
        return go_main_menu(message)

    import os
    user = message.from_user
    admin_id = os.getenv("ADMIN_ID", "")
    text = message.text or ""

    # Отправляем сообщение пользователю
    bot.send_message(
        message.chat.id,
        "✅ <b>Спасибо!</b> Ваше сообщение отправлено администратору.",
        reply_markup=main_reply_keyboard()
    )

    # Пересылаем админу
    if admin_id:
        user_info = f"@{user.username}" if user and user.username else f"id:{user.id if user else '?'}"
        name = (user.first_name or "") if user else ""
        try:
            msg = (
                f"\U0001f4e9 <b>Обратная связь</b>\n\n"
                f"\U0001f464 {name} ({user_info})\n\n"
                f"\U0001f4ac {text}"
            )
            bot.send_message(int(admin_id), msg)
        except Exception as e:
            logger.warning("Feedback forward failed: %s", e)


# ─── СЕРВИСЫ И SOS ───────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🏪 Сервисы")
def btn_services(message: Message) -> None:
    bot.send_message(message.chat.id, format_services(SERVICES), reply_markup=back_to_menu_keyboard())

@bot.message_handler(func=lambda m: m.text == "🆘 SOS")
def btn_sos(message: Message) -> None:
    bot.send_message(message.chat.id, "📍 Отправьте геолокацию чтобы увидеть местные номера ГИБДД.", reply_markup=sos_location_keyboard())

@bot.message_handler(content_types=["location"])
def on_location(message: Message) -> None:
    loc = message.location
    if not loc:
        return
    try:
        from sos_geo import find_city, _city_key
        city, dist = find_city(loc.latitude, loc.longitude)
        city_key = _city_key(city.name) if city and dist <= city.radius else ""
    except Exception:
        city_key = ""
    text = format_sos(loc.latitude, loc.longitude)
    bot.send_message(message.chat.id, text, reply_markup=sos_inline_keyboard(city_key))

@bot.message_handler(func=lambda m: m.text == "🔙 Без геолокации (федеральные номера)")
def sos_no_geo(message: Message) -> None:
    bot.send_message(message.chat.id, format_sos(), reply_markup=sos_inline_keyboard())


# ─── CALLBACK HANDLERS ───────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("brand_"))
def on_brand_selected(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    brand = call.data.replace("brand_", "", 1)
    bot.edit_message_text(
        f"🚗 Марка: <b>{brand}</b>\n\nВыберите модель:",
        call.message.chat.id, call.message.message_id,
        reply_markup=model_inline_keyboard(brand)
    )

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("model_"))
def on_model_selected(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("_", 2)
    if len(parts) < 3:
        return
    brand = parts[1]
    model = parts[2]
    bot.edit_message_text(
        f"🚗 {brand} <b>{model}</b>\n\nВыберите год выпуска:",
        call.message.chat.id, call.message.message_id,
        reply_markup=year_inline_keyboard(brand, model)
    )

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("year|"))
def on_year_selected(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("|")
    if len(parts) < 4:
        return
    _, brand, model, year = parts
    user_id = call.from_user.id if call.from_user else 0
    user_vehicle.set_vehicle(user_id, brand, model, year)
    text = format_my_car(brand, model, year)
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "✅ Авто сохранено!", reply_markup=my_car_menu_keyboard(True))

@bot.callback_query_handler(func=lambda c: c.data == "select_brand")
def on_select_brand_cb(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    bot.edit_message_text("🚗 <b>Выберите марку автомобиля:</b>", call.message.chat.id, call.message.message_id, reply_markup=brand_inline_keyboard())

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("ypage|"))
def on_year_page(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("|")
    if len(parts) < 4:
        return
    _, brand, model, page = parts
    from keyboards import year_inline_keyboard
    bot.edit_message_reply_markup(
        call.message.chat.id, call.message.message_id,
        reply_markup=year_inline_keyboard(brand, model, int(page))
    )

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("select_model_"))
def on_select_model_cb(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    brand = call.data.replace("select_model_", "", 1)
    bot.edit_message_text(f"🚗 Марка: <b>{brand}</b>\n\nВыберите модель:", call.message.chat.id, call.message.message_id, reply_markup=model_inline_keyboard(brand))


# ─── ДИАЛОГОВАЯ ДИАГНОСТИКА ──────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("diag_"))
def on_dialog_answer(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id if call.from_user else 0
    chat_id = call.message.chat.id

    if call.data == "diag_cancel":
        clear_state(user_id)
        bot.send_message(chat_id, "Диагностика отменена.", reply_markup=main_inline_keyboard())
        return

    try:
        _, rest = call.data.split("diag_", 1)
        tree_id, answer = rest.split("::", 1)
    except ValueError:
        return

    state = get_state(user_id)
    if not state or state.tree_id != tree_id:
        bot.send_message(chat_id, "Сессия устарела. Начните сначала.", reply_markup=main_inline_keyboard())
        return

    from dialog_engine import DIALOG_TREES
    tree = next((t for t in DIALOG_TREES if t.tree_id == tree_id), None)
    if not tree:
        return

    node = get_node(tree, state.current_node_id)
    if not node:
        return

    state.answers.append(answer)

    for opt_key, diagnosis in node.diagnoses.items():
        if answer.startswith(opt_key[:50]):
            clear_state(user_id)
            add_entry(user_id, " → ".join(state.answers), diagnosis.title, diagnosis.urgency)
            from user_profile import get_profile
            profile = get_profile(user_id)
            level = profile.get("level", "novice") if profile else "novice"
            show_simplify = level not in ("novice", "driver")
            set_last_diagnostic(user_id, {"kind": "tree", "diagnosis": diagnosis})
            bot.send_message(chat_id, f"<b>🔎 Диагноз Джека:</b>\n\n{format_diagnosis(diagnosis)}\n\n<i>Диагностика завершена.</i>", reply_markup=after_diagnostic_keyboard(show_simplify=show_simplify))
            return

    next_node_id = None
    for opt_key, nid in node.next_nodes.items():
        if answer.startswith(opt_key[:50]):
            next_node_id = nid
            break

    if not next_node_id:
        clear_state(user_id)
        bot.send_message(chat_id, "Ошибка. Попробуйте снова.", reply_markup=main_inline_keyboard())
        return

    next_node = get_node(tree, next_node_id)
    if not next_node:
        return

    state.current_node_id = next_node_id
    set_state(user_id, state)
    hint = f"\n<i>{next_node.hint}</i>" if next_node.hint else ""
    bot.send_message(chat_id, f"<b>{next_node.question}</b>{hint}", reply_markup=dialog_options_keyboard(next_node.options, tree_id))


# ─── ОТВЕТЫ МЕХАНИКА ────────────────────────────────────────────────────────

@bot.message_handler(regexp=r'^/answer_\d+')
def cmd_answer(message: Message) -> None:
    """Механик отвечает: /answer_123 Текст ответа"""
    import os, re
    admin_id = str(os.getenv("ADMIN_ID", ""))
    user_id = str(message.from_user.id) if message.from_user else ""
    if not admin_id or user_id != admin_id:
        return

    match = re.match(r'/answer_(\d+)\s*(.*)', message.text or "", re.DOTALL)
    if not match:
        return

    q_id = int(match.group(1))
    answer_text = match.group(2).strip()

    if not answer_text:
        bot.send_message(message.chat.id, "Укажи ответ: /answer_123 Текст ответа")
        return

    from mechanic import get_question, save_answer
    q = get_question(q_id)
    if not q:
        bot.send_message(message.chat.id, f"Вопрос #{q_id} не найден")
        return

    save_answer(q_id, answer_text)

    # Отправляем ответ пользователю
    try:
        user_name = q.get("first_name") or "Пользователь"
        from keyboards import rate_answer_keyboard
        bot.send_message(
            int(q["chat_id"]),
            (
                "🔧 <b>Ответ механика на ваш вопрос:</b>\n\n"
                f"<i>Вопрос: {q['question']}</i>\n\n"
                f"{answer_text}\n\n"
                "<i>Помог ли вам этот ответ?</i>"
            ),
            reply_markup=rate_answer_keyboard(q_id)
        )
        bot.send_message(
            message.chat.id,
            f"✅ Ответ отправлен {user_name}!\nДобавить в базу: /add_{q_id}"
        )
    except Exception as e:
        logger.warning("Не удалось отправить ответ пользователю: %s", e)
        bot.send_message(message.chat.id, f"Ответ сохранён, но не доставлен: {e}")


@bot.message_handler(regexp=r'^/add_\d+')
def cmd_add_to_base(message: Message) -> None:
    """Добавляет вопрос+ответ в базу диагностики: /add_123"""
    import os, re
    admin_id = str(os.getenv("ADMIN_ID", ""))
    user_id = str(message.from_user.id) if message.from_user else ""
    if not admin_id or user_id != admin_id:
        return

    match = re.match(r'/add_(\d+)', message.text or "")
    if not match:
        return

    q_id = int(match.group(1))
    from mechanic import get_question, save_to_diagnostic_base
    q = get_question(q_id)

    if not q:
        bot.send_message(message.chat.id, f"Вопрос #{q_id} не найден")
        return

    if not q.get("answer"):
        bot.send_message(message.chat.id, f"Сначала ответь на вопрос: /answer_{q_id} [ответ]")
        return

    bot.send_message(message.chat.id, "⏳ Добавляю в базу через GigaChat...")
    saved = save_to_diagnostic_base(q_id)

    if saved:
        import json
        db_path = os.path.join(os.path.dirname(__file__), "data", "diagnostic_base.json")
        db = json.load(open(db_path, encoding="utf-8"))
        bot.send_message(
            message.chat.id,
            f"✅ Добавлено в базу!\n🗄 Теперь в базе: {len(db)} записей"
        )
    else:
        bot.send_message(message.chat.id, "⚠️ Не удалось добавить (дубликат или ошибка GigaChat)")


# ─── ADMIN CALLBACKS ─────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("admin_"))
def on_admin_callback(call: CallbackQuery) -> None:
    import os
    user = call.from_user
    if not user or str(user.id) != str(os.getenv("ADMIN_ID", "")):
        bot.answer_callback_query(call.id, "⛔ Нет доступа")
        return

    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id

    if call.data == "admin_stats":
        from broadcaster import get_user_count
        bot.send_message(chat_id, f"👥 Пользователей: <b>{get_user_count()}</b>")

    elif call.data == "admin_unknown":
        _send_unknown_item(chat_id, offset=0)

    elif call.data == "admin_broadcast":
        bot.send_message(
            chat_id,
            "📢 <b>Рассылка</b>\n\nОтправьте текст сообщения для рассылки всем пользователям:",
            reply_markup=back_to_menu_keyboard()
        )
        bot.register_next_step_handler(call.message, process_broadcast_input)

    elif call.data == "admin_experts":
        from user_profile import get_experts, LEVELS
        experts = get_experts(20)
        if not experts:
            bot.send_message(chat_id, "Экспертов пока нет. Пользователи с уровнем Механик или Эксперт появятся здесь.")
            return
        lines = ["🏆 <b>Эксперты и механики:</b>\n"]
        for e in experts:
            badge = LEVELS.get(e["level"], {}).get("emoji", "⚙️")
            name = e.get("first_name") or f"id:{e['user_id']}"
            uname = f"@{e['username']}" if e.get("username") else ""
            stars = round(e.get("rating") or 0)
            lines.append(f"{badge} {name} {uname} | ⭐{stars} | {e.get('answers_count',0)} ответов")
        bot.send_message(chat_id, "\n".join(lines))

    elif call.data == "admin_mechanic":
        from mechanic import get_pending_questions, get_stats
        stats = get_stats()
        questions = get_pending_questions(5)
        lines = [
            "🔧 <b>Вопросы механику</b>\n",
            f"Всего: {stats['total']} | Ожидают: {stats['pending']} | Отвечено: {stats['answered']}\n"
        ]
        if questions:
            lines.append("<b>Неотвеченные:</b>")
            for q in questions:
                uname = q.get("username") or q["user_id"]
                car = q.get("car_info") or "авто не указано"
                lines.append(f"\n#{q['id']} @{uname} ({car})")
                lines.append(f"<i>{q['question'][:80]}</i>")
                lines.append(f"/answer_{q['id']} [ответ]  |  /add_{q['id']}")
        else:
            lines.append("\n✅ Нет неотвеченных вопросов!")
        bot.send_message(chat_id, "\n".join(lines))

    elif call.data == "admin_db_info":
        import json, os
        path = os.path.join(os.path.dirname(__file__), "data", "diagnostic_base.json")
        db = json.load(open(path, encoding="utf-8"))
        total_queries = sum(len(x.get("user_queries", [])) for x in db)
        urgency = {}
        for x in db:
            u = x.get("urgency", "medium")
            urgency[u] = urgency.get(u, 0) + 1
        text = (
            f"🗄 <b>База диагностики</b>\n\n"
            f"Записей: <b>{len(db)}</b>\n"
            f"Поисковых фраз: <b>{total_queries}</b>\n\n"
            f"🚨 Критических: {urgency.get('critical', 0)}\n"
            f"⚠️ Важных: {urgency.get('high', 0)}\n"
            f"🔧 Средних: {urgency.get('medium', 0)}\n"
            f"ℹ️ Низких: {urgency.get('low', 0)}"
        )
        bot.send_message(chat_id, text)

    elif call.data == "admin_claude":
        from config import ANTHROPIC_API_KEY
        if not ANTHROPIC_API_KEY:
            bot.send_message(chat_id, "⚠️ ANTHROPIC_API_KEY не задан в переменных окружения Railway.")
            return
        from dialog_state import set_state, DialogState
        set_state(call.from_user.id, "claude_chat")
        bot.send_message(
            chat_id,
            "🤖 <b>Режим Claude</b>\n\n"
            "Напиши любой вопрос — отвечу через Claude AI.\n\n"
            "<i>Чтобы выйти — нажми 🏠 Главное меню или /start</i>"
        )


def process_broadcast_input(message: Message) -> None:
    import os
    user = message.from_user
    if not user or str(user.id) != str(os.getenv("ADMIN_ID", "")):
        return
    if message.text in ("🏠 Главное меню", "/start"):
        return go_main_menu(message)
    from broadcaster import broadcast, get_user_count
    bot.send_message(message.chat.id, "⏳ Начинаю рассылку...")
    result = broadcast(bot, message.text)
    bot.send_message(
        message.chat.id,
        f"✅ Готово!\n👥 {get_user_count()} польз. | 📨 {result['sent']} | ❌ {result['failed']}"
    )


# ─── УТОЧНЯЮЩИЕ ВОПРОСЫ ──────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("clarify_"))
def on_clarify_answer(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    from clarify import CLARIFY_QUESTIONS
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Парсим: clarify_{step}_{answer}_{original}
    parts = call.data.split("_", 3)
    if len(parts) < 4:
        return
    step = int(parts[1])
    answer = parts[2]
    original = parts[3]

    next_step = step + 1

    if next_step < len(CLARIFY_QUESTIONS):
        # Следующий уточняющий вопрос
        q = CLARIFY_QUESTIONS[next_step]
        kb = InlineKeyboardMarkup(row_width=2)
        for opt in q["options"]:
            kb.add(InlineKeyboardButton(
                opt,
                callback_data=f"clarify_{next_step}_{opt[:40]}_{original}"
            ))
        kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
        bot.edit_message_text(
            q["question"],
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
    else:
        # Все вопросы заданы — пробуем найти ответ ещё раз
        from diagnostic import search_by_phrase
        from formatters import format_diagnostic_for_level
        from user_profile import get_profile
        result, score = search_by_phrase(f"{original} {answer}", threshold=35)

        if result:
            user_id_cb = call.from_user.id if call.from_user else 0
            profile = get_profile(user_id_cb)
            level = profile.get("level", "novice") if profile else "novice"
            show_simplify = level not in ("novice", "driver")
            set_last_diagnostic(user_id_cb, {"kind": "smart", "result": result})
            bot.edit_message_text(
                f"<b>🔎 Джек нашёл похожую проблему:</b>\n\n{format_diagnostic_for_level(result, level)}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=after_diagnostic_keyboard(show_simplify=show_simplify)
            )
        else:
            bot.edit_message_text(
                "😔 <b>Джек не смог определить причину точно.</b>\n\n"
                "Рекомендуем:\n"
                "• Обратиться в СТО для компьютерной диагностики\n"
                "• Написать нам через 💬 Обратная связь — добавим в базу\n\n"
                "<i>Ваш запрос сохранён и поможет улучшить Джека!</i>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_inline_keyboard()
            )


# ─── ОНБОРДИНГ / УРОВЕНЬ ─────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("level_"))
def on_level_selected(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    user = call.from_user
    if not user:
        return

    level = call.data.replace("level_", "")
    from user_profile import set_level, LEVELS
    set_level(user.id, level)

    level_info = LEVELS.get(level, LEVELS["novice"])
    emoji = level_info["emoji"]
    title = level_info["title"]
    desc = level_info["desc"]

    # Персонализированное приветствие по уровню
    if level in ("mechanic", "expert"):
        extra = (
            "\n\n🏆 <b>Отлично! Вы можете помогать другим пользователям.</b>\n"
            "Когда кто-то задаст вопрос — вы получите уведомление.\n"
            "За каждый полезный ответ вы будете получать рейтинг."
        )
    elif level == "garage":
        extra = "\n\n🔧 Буду давать вам более технические ответы."
    else:
        extra = "\n\nБуду объяснять всё простым языком 👍"

    bot.edit_message_text(
        f"{emoji} <b>Уровень: {title}</b>\n<i>{desc}</i>{extra}\n\n"
        "Теперь выберите ваш автомобиль или начните диагностику!",
        call.message.chat.id,
        call.message.message_id,
    )

    import os
    is_admin = str(user.id) == str(os.getenv("ADMIN_ID", ""))
    bot.send_message(
        call.message.chat.id,
        welcome_text(first_name=user.first_name),
        reply_markup=admin_keyboard() if is_admin else main_reply_keyboard(),
    )


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("rate_"))
def on_rate_answer(call: CallbackQuery) -> None:
    """Пользователь оценивает ответ эксперта."""
    bot.answer_callback_query(call.id)
    parts = call.data.split("_")
    rating_type = parts[1]   # good / partial / bad
    q_id = int(parts[2])

    rating_map = {"good": 5.0, "partial": 3.0, "bad": 1.0}
    rating = rating_map.get(rating_type, 3.0)

    from mechanic import get_question
    from user_profile import add_answer_rating
    q = get_question(q_id)

    if q and q.get("expert_id"):
        add_answer_rating(int(q["expert_id"]), rating)

    msg = {
        "good": "👍 Спасибо за оценку! Эксперт получит +рейтинг.",
        "partial": "🤔 Понятно. Попробуйте уточнить вопрос.",
        "bad": "👎 Жаль. Попробуем найти другого эксперта.",
    }.get(rating_type, "Спасибо!")

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, msg, reply_markup=main_reply_keyboard())


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("eq_"))
def on_expert_question(call: CallbackQuery) -> None:
    """Эксперт берёт или пропускает вопрос."""
    bot.answer_callback_query(call.id)
    parts = call.data.split("_")
    action = parts[1]   # take / skip
    q_id = int(parts[2])

    if action == "skip":
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Вопрос пропущен.")
        return

    # Эксперт берёт вопрос
    from mechanic import get_question, save_expert_assigned
    q = get_question(q_id)
    if not q:
        bot.send_message(call.message.chat.id, "Вопрос уже решён или не найден.")
        return

    try:
        save_expert_assigned(q_id, call.from_user.id)
    except Exception:
        pass

    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    bot.send_message(
        call.message.chat.id,
        f"✅ Вопрос #{q_id} закреплён за вами!\n\n"
        f"<b>Вопрос:</b> {q['question']}\n\n"
        f"Ответьте: /answer_{q_id} [ваш ответ]"
    )


# ─── FAQ CALLBACKS ───────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "faq_menu")
def on_faq_menu(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    from faq import FAQ
    from keyboards import faq_keyboard
    text = "📚 <b>FAQ — Частые вопросы</b>\n\nВыберите вопрос:"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=faq_keyboard())


@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("faq_") and c.data != "faq_menu")
def on_faq_answer(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    from faq import FAQ
    from keyboards import faq_back_keyboard
    try:
        idx = int(call.data.replace("faq_", ""))
        item = FAQ[idx]
        bot.edit_message_text(
            item["answer"],
            call.message.chat.id,
            call.message.message_id,
            reply_markup=faq_back_keyboard()
        )
    except (ValueError, IndexError):
        pass


# ─── ADMIN: ПРИВЯЗКА НЕРАСПОЗНАННЫХ ФРАЗ ─────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith(("unk_assign::", "unk_skip::", "unk_delete::")))
def on_unknown_action(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("::")
    action = parts[0]
    offset = int(parts[1])
    chat_id = call.message.chat.id

    from clarify import get_unknown_queries, save_custom_trigger, delete_unknown_query

    queries = get_unknown_queries(50)
    if offset >= len(queries):
        bot.send_message(chat_id, "✅ Фраза уже обработана.")
        return

    phrase = queries[offset]["query"]

    if action == "unk_assign":
        tree_id = parts[2]
        save_custom_trigger(phrase, tree_id)
        delete_unknown_query(phrase)
        TREE_LABELS = {
            "heavy_wheel": "🛞 Тяжёлый руль", "wont_start": "🔑 Не заводится",
            "brake_noise": "🛑 Тормоза", "overheat": "🌡 Перегрев",
            "suspension_knock": "🔩 Стук подвески", "gearbox": "⚙️ Коробка",
            "smell": "💨 Запах", "vibration_speed": "📳 Вибрация",
            "electrics": "⚡ Электрика", "aircon": "❄️ Кондиционер",
            "oil_leak": "🛢 Масло",
        }
        label = TREE_LABELS.get(tree_id, tree_id)
        bot.edit_message_text(
            f"✅ Сохранено: <code>{phrase}</code> → {label}",
            chat_id, call.message.message_id
        )
        # Показываем следующую фразу
        _send_unknown_item(chat_id, offset=0)

    elif action == "unk_skip":
        bot.edit_message_text(
            f"⏭ Пропущено: <code>{phrase}</code>",
            chat_id, call.message.message_id
        )
        _send_unknown_item(chat_id, offset=offset + 1)

    elif action == "unk_delete":
        delete_unknown_query(phrase)
        bot.edit_message_text(
            f"🗑 Удалено: <code>{phrase}</code>",
            chat_id, call.message.message_id
        )
        _send_unknown_item(chat_id, offset=0)


# ─── ОБЪЯСНИ ПРОЩЕ ────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data == "explain_simpler")
def on_explain_simpler(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id if call.from_user else 0
    chat_id = call.message.chat.id

    data = get_last_diagnostic(user_id)
    if not data:
        bot.send_message(
            chat_id,
            "😔 Не нашёл, что упрощать — похоже, диагностика устарела. Запустите новую.",
            reply_markup=after_diagnostic_keyboard(),
        )
        return

    if data["kind"] == "smart":
        from formatters import format_diagnostic_for_level
        simple_text = format_diagnostic_for_level(data["result"], "novice")
        header = "<b>🔎 То же самое, но проще:</b>\n\n"
    else:
        from formatters import format_diagnosis_simple
        simple_text = format_diagnosis_simple(data["diagnosis"])
        header = "<b>🔎 Диагноз Джека — проще:</b>\n\n"

    bot.send_message(chat_id, header + simple_text, reply_markup=after_diagnostic_keyboard())


# ─── ОБЩИЕ CALLBACKS ─────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: True)
def on_callback(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id

    if call.data == "main_menu":
        user = call.from_user
        bot.send_message(chat_id, welcome_text(first_name=user.first_name if user else None), reply_markup=main_reply_keyboard())
    elif call.data == "get_services":
        bot.send_message(chat_id, format_services(SERVICES), reply_markup=back_to_menu_keyboard())
    elif call.data == "sos_ask":
        bot.send_message(chat_id, "📍 Отправьте геолокацию.", reply_markup=sos_location_keyboard())
    elif call.data == "new_diagnostic":
        user_id = call.from_user.id if call.from_user else 0
        car = user_vehicle.get_vehicle(user_id)
        car_str = f"{car['brand']} {car['model']} ({car['year']})" if car else ""
        bot.send_message(chat_id, format_diagnostic_start(car_str), reply_markup=diagnostic_menu_keyboard())
    elif call.data == "show_history":
        user_id = call.from_user.id if call.from_user else 0
        bot.send_message(chat_id, format_history(user_id), reply_markup=back_to_menu_keyboard())
    elif call.data.startswith("sponsor_sto_"):
        city_key = call.data.removeprefix("sponsor_sto_")
        try:
            from sponsors import format_sto_sponsors
            bot.send_message(chat_id, "🥇 <b>Партнёры Jarvis Auto</b>\n\n" + format_sto_sponsors(city_key), reply_markup=back_to_menu_keyboard())
        except Exception:
            pass
    elif call.data.startswith("sponsor_kom_"):
        city_key = call.data.removeprefix("sponsor_kom_")
        try:
            from sponsors import get_gold_komissar
            gold = get_gold_komissar(city_key)
            if gold:
                bot.send_message(chat_id, f"🥇 <b>{gold.name}</b>\n\n⏰ {gold.work_time}  |  ★ {gold.rating}\n📞 <code>{gold.phone}</code>", reply_markup=back_to_menu_keyboard())
        except Exception:
            pass


# ─── CLAUDE CHAT (только для админа) ─────────────────────────────────────────

@bot.message_handler(func=lambda m: get_state(m.from_user.id) == "claude_chat" if m.from_user else False)
def handle_claude_chat(message: Message) -> None:
    """Обрабатывает сообщения в режиме диалога с Claude."""
    import os
    user = message.from_user
    if not user or str(user.id) != str(os.getenv("ADMIN_ID", "")):
        return

    text = message.text or ""
    if text in ("🏠 Главное меню", "/start", "/admin"):
        clear_state(user.id)
        return go_main_menu(message)

    from config import ANTHROPIC_API_KEY
    if not ANTHROPIC_API_KEY:
        bot.send_message(message.chat.id, "⚠️ ANTHROPIC_API_KEY не задан.")
        return

    # Показываем "печатает..."
    bot.send_chat_action(message.chat.id, "typing")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=(
                "Ты персональный ассистент Алекса — создателя Jarvis Auto, "
                "Telegram-бота для диагностики автомобилей. "
                "Отвечай по-русски, кратко и по делу. "
                "Можешь помогать с идеями для бота, анализом, текстами, "
                "техническими вопросами и любыми другими задачами."
            ),
            messages=[{"role": "user", "content": text}],
        )
        answer = response.content[0].text
        # Telegram ограничивает сообщения до 4096 символов
        if len(answer) > 4000:
            answer = answer[:4000] + "\n\n<i>...ответ обрезан</i>"
        bot.send_message(message.chat.id, f"🤖 <b>Claude:</b>\n\n{answer}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка Claude API: {e}")


# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set")
        sys.exit(1)

    proxies = resolve_proxy()
    if proxies:
        apihelper.proxy = proxies

    if not check_telegram(BOT_TOKEN, proxies):
        sys.exit(1)

    logger.info("Jarvis Auto started (AI: %s)", "on" if ai_assistant.is_enabled() else "off")
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
