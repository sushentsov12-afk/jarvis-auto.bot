import logging
import sys
from telebot import TeleBot, apihelper
from telebot.types import CallbackQuery, Message

import ai_assistant
from diagnostic import search_by_phrase, format_diagnostic
from user_history import add_entry, format_history, has_history
from dialog_engine import find_tree, get_node, format_diagnosis, URGENCY_EMOJI
from dialog_state import set_state, get_state, clear_state, DialogState
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
    bot.send_message(
        message.chat.id,
        welcome_text(first_name=user.first_name if user else None),
        reply_markup=admin_keyboard() if is_admin else main_reply_keyboard(),
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
    """Топ нераспознанных запросов для пополнения базы."""
    import os
    admin_id = str(os.getenv("ADMIN_ID", ""))
    user_id = str(message.from_user.id) if message.from_user else ""
    if not admin_id or user_id != admin_id:
        return
    from clarify import get_unknown_queries
    queries = get_unknown_queries(20)
    if not queries:
        bot.send_message(message.chat.id, "Нераспознанных запросов нет 🎉")
        return
    lines = ["📋 <b>Нераспознанные запросы (топ-20):</b>\n"]
    for i, q in enumerate(queries, 1):
        lines.append(f"{i}. [{q['count']}x] {q['query']}")
    bot.send_message(message.chat.id, "\n".join(lines))

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
    user = message.from_user
    # Сбрасываем состояние диагностики если было
    if message.from_user:
        clear_state(message.from_user.id)
    bot.send_message(
        message.chat.id,
        welcome_text(first_name=user.first_name if user else None),
        reply_markup=main_reply_keyboard(),
    )

@bot.message_handler(func=lambda m: m.text == "ℹ️ Справка")
def btn_help(message: Message) -> None:
    bot.send_message(
        message.chat.id,
        help_text(ai_assistant.is_enabled()),
        reply_markup=back_to_menu_keyboard(),
    )


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

    # 2. Поиск по диагностической базе (65 проблем)
    from diagnostic import smart_search
    result_smart = smart_search(text)
    if result_smart:
        from diagnostic import format_diagnostic as fmt_diag
        # Проверяем учитывает ли авто пользователя
        car = user_vehicle.get_vehicle(user_id)
        car_note = ""
        if car:
            car_note = f"\n\n🚗 <i>Для {car['brand']} {car['model']}: уточните у механика применимость.</i>"
        add_entry(user_id, text, result_smart["technical_name"], result_smart.get("urgency", "medium"))
        answer = fmt_diag(result_smart)
        bot.send_message(
            message.chat.id,
            f"<b>🔎 Джек определил проблему:</b>\n\n{answer}{car_note}",
            reply_markup=after_diagnostic_keyboard()
        )
        return

    # 3. Нечёткий поиск по каталогу запчастей
    part = find_best_match(text, PARTS)
    if part:
        title = f"Диагностика {part.id}" if part.type == "obd" else "Подбор по симптому"
        bot.send_message(message.chat.id, format_part(part, title=title), reply_markup=after_diagnostic_keyboard())
        add_entry(user_id, text, part.name, "medium")
        return

    # 4. GigaChat AI
    if ai_assistant.is_enabled():
        try:
            answer = ai_assistant.ask(text)
            bot.send_message(message.chat.id, f"<b>Джек (AI):</b>\n\n{answer}", reply_markup=main_inline_keyboard())
            return
        except Exception:
            logger.exception("GigaChat failed")

    # 5. Не нашли — сохраняем запрос и запускаем уточняющие вопросы
    from clarify import save_unknown_query, build_clarify_text, CLARIFY_QUESTIONS
    save_unknown_query(user_id, text)

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
    db = json.load(open("data/diagnostic_base.json", encoding="utf-8"))
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

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("year_"))
def on_year_selected(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("_", 3)
    if len(parts) < 4:
        return
    brand, model, year = parts[1], parts[2], parts[3]
    user_id = call.from_user.id if call.from_user else 0
    user_vehicle.set_vehicle(user_id, brand, model, year)
    text = format_my_car(brand, model, year)
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "✅ Авто сохранено!", reply_markup=my_car_menu_keyboard(True))

@bot.callback_query_handler(func=lambda c: c.data == "select_brand")
def on_select_brand_cb(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    bot.edit_message_text("🚗 <b>Выберите марку автомобиля:</b>", call.message.chat.id, call.message.message_id, reply_markup=brand_inline_keyboard())

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("year_page_"))
def on_year_page(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    parts = call.data.split("_")
    # year_page_brand_model_page
    page = int(parts[-1])
    model = parts[-2]
    brand = "_".join(parts[2:-2])
    from keyboards import year_inline_keyboard
    bot.edit_message_reply_markup(
        call.message.chat.id, call.message.message_id,
        reply_markup=year_inline_keyboard(brand, model, page)
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
            bot.send_message(chat_id, f"<b>🔎 Диагноз Джека:</b>\n\n{format_diagnosis(diagnosis)}\n\n<i>Диагностика завершена.</i>", reply_markup=after_diagnostic_keyboard())
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
        from clarify import get_unknown_queries
        queries = get_unknown_queries(20)
        if not queries:
            bot.send_message(chat_id, "🎉 Нераспознанных запросов нет!")
            return
        lines = ["❓ <b>Нераспознанные запросы (топ-20):</b>\n"]
        for i, q in enumerate(queries, 1):
            lines.append(f"{i}. [{q['count']}x] {q['query']}")
        bot.send_message(chat_id, "\n".join(lines))

    elif call.data == "admin_broadcast":
        bot.send_message(
            chat_id,
            "📢 <b>Рассылка</b>\n\nОтправьте текст сообщения для рассылки всем пользователям:",
            reply_markup=back_to_menu_keyboard()
        )
        bot.register_next_step_handler(call.message, process_broadcast_input)

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
        from diagnostic import format_diagnostic as fmt_diag
        result, score = search_by_phrase(f"{original} {answer}", threshold=35)

        if result:
            bot.edit_message_text(
                f"<b>🔎 Джек нашёл похожую проблему:</b>\n\n{fmt_diag(result)}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=after_diagnostic_keyboard()
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
