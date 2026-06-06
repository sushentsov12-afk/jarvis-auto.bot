import logging
import sys
from telebot import TeleBot, apihelper
from telebot.types import CallbackQuery, Message

import ai_assistant
from diagnostic import smart_search, search_by_phrase, format_diagnostic
from user_history import add_entry, format_history, has_history
from dialog_engine import find_tree, get_node, format_diagnosis, URGENCY_EMOJI
from dialog_state import set_state, get_state, clear_state, has_state, DialogState
from catalog import find_best_match, find_by_obd, load_parts, load_services
from config import BOT_TOKEN
from network import check_telegram, resolve_proxy
from user_vehicle import user_vehicle
from formatters import (
    format_ai_fallback, format_part, format_services, help_text, 
    welcome_text, format_my_car, format_diagnostic_start, format_typical_issues
)
from keyboards import (
    main_reply_keyboard, back_to_menu_keyboard, diagnostic_menu_keyboard,
    brand_keyboard, model_keyboard, year_keyboard, my_car_menu_keyboard,
    confirm_vehicle_keyboard, main_inline_keyboard, sos_location_keyboard,
    sos_inline_keyboard, after_diagnostic_keyboard, dialog_options_keyboard
)
from sos_geo import format_sos

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis")

PARTS = load_parts()
SERVICES = load_services()
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# ─────────────────────────────────────────────────────────────────────────────
# ГЛАВНОЕ МЕНЮ
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    user = message.from_user
    bot.send_message(
        message.chat.id,
        welcome_text(first_name=user.first_name if user else None),
        reply_markup=main_reply_keyboard(),
    )

@bot.message_handler(func=lambda m: m.text == "🏠 Главное меню")
def go_main_menu(message: Message) -> None:
    user = message.from_user
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

# ─────────────────────────────────────────────────────────────────────────────
# ДИАГНОСТИКА
# ─────────────────────────────────────────────────────────────────────────────

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
    if message.text == "🏠 Главное меню":
        return go_main_menu(message)
    
    user_id = message.from_user.id if message.from_user else 0
    text = (message.text or "").strip()
    bot.send_chat_action(message.chat.id, "typing")
    
    # Поиск по дереву диалога
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
    
    # Поиск по OBD или симптому
    part = find_best_match(text, PARTS)
    if part:
        title = f"Диагностика {part.id}" if part.type == "obd" else "Подбор по симптому"
        bot.send_message(
            message.chat.id,
            format_part(part, title=title),
            reply_markup=after_diagnostic_keyboard(),
        )
        add_entry(user_id, text, part.name, "medium")
        return
    
    # Нечёткий поиск
    result, confidence = search_by_phrase(text)
    if result:
        add_entry(user_id, text, result["technical_name"], result.get("urgency", "medium"))
        answer = format_diagnostic(result, confidence)
        bot.send_message(
            message.chat.id,
            f"<b>🔎 Джек нашёл похожую проблему:</b>\n\n{answer}",
            reply_markup=after_diagnostic_keyboard(),
        )
        return
    
    # GigaChat
    if ai_assistant.is_enabled():
        try:
            answer = ai_assistant.ask(text)
            bot.send_message(message.chat.id, f"<b>Джек (AI):</b>\n\n{answer}", reply_markup=main_inline_keyboard())
            return
        except Exception:
            logger.exception("GigaChat failed")
    
    bot.send_message(message.chat.id, format_ai_fallback(text), reply_markup=main_inline_keyboard())

# ─────────────────────────────────────────────────────────────────────────────
# МОЕ АВТО
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🚗 Моё авто")
def btn_my_car(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    car = user_vehicle.get_vehicle(user_id)
    
    if car:
        text = format_my_car(car['brand'], car['model'], car['year'])
        bot.send_message(message.chat.id, text, reply_markup=my_car_menu_keyboard(True))
    else:
        bot.send_message(
            message.chat.id, 
            "🚗 <b>Выберите ваш автомобиль</b>\n\nЭто поможет Джеку дать более точные советы.",
            reply_markup=my_car_menu_keyboard(False),
        )

@bot.message_handler(func=lambda m: m.text == "➕ Выбрать авто")
def select_brand(message: Message) -> None:
    bot.send_message(message.chat.id, "Выберите марку автомобиля:", reply_markup=brand_keyboard([
        "Toyota", "BMW", "Mercedes-Benz", "Audi", "Volkswagen", "Hyundai", 
        "Kia", "Nissan", "Honda", "Ford", "Lada", "Geely", "Chery", "BYD", "Tesla"
    ]))
    bot.register_next_step_handler(message, process_brand_selection)

def process_brand_selection(message: Message) -> None:
    if message.text == "🏠 Главное меню":
        return go_main_menu(message)
    brand = message.text.strip()
    bot.send_message(message.chat.id, f"Выберите модель {brand}:", reply_markup=model_keyboard([
        "Camry", "Corolla", "RAV4", "3 Series", "A4", "Golf", "Accent", "Civic", "Focus", "Granta"
    ]))
    bot.register_next_step_handler(message, lambda m: process_model_selection(m, brand))

def process_model_selection(message: Message, brand: str) -> None:
    if message.text == "🏠 Главное меню":
        return go_main_menu(message)
    if message.text == "⬅️ Вернуться к маркам":
        return select_brand(message)
    model = message.text.strip()
    bot.send_message(message.chat.id, f"Выберите год выпуска {brand} {model}:", reply_markup=year_keyboard())
    bot.register_next_step_handler(message, lambda m: process_year_selection(m, brand, model))

def process_year_selection(message: Message, brand: str, model: str) -> None:
    if message.text == "🏠 Главное меню":
        return go_main_menu(message)
    if message.text == "⬅️ Вернуться к моделям":
        return process_brand_selection(message)
    year = message.text.strip()
    
    user_id = message.from_user.id if message.from_user else 0
    user_vehicle.set_vehicle(user_id, brand, model, year)
    
    text = format_my_car(brand, model, year)
    bot.send_message(message.chat.id, text, reply_markup=my_car_menu_keyboard(True))

@bot.message_handler(func=lambda m: m.text == "📌 Типичные ошибки")
def show_typical_issues(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    car = user_vehicle.get_vehicle(user_id)
    
    if not car:
        bot.send_message(message.chat.id, "Сначала выберите авто в меню 🚗 Моё авто", reply_markup=my_car_menu_keyboard(False))
        return
    
    issues = [
        type('Issue', (), {'name': 'Пропуски зажигания', 'urgency': 'high', 'description': 'Свечи или катушка', 'price_range': '500–3000 руб'}),
        type('Issue', (), {'name': 'Check Engine', 'urgency': 'medium', 'description': 'Датчик кислорода', 'price_range': '1500–6000 руб'}),
    ]
    
    text = format_typical_issues(car['brand'], car['model'], car['year'], issues)
    bot.send_message(message.chat.id, text, reply_markup=back_to_menu_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔄 Изменить авто")
def change_car(message: Message) -> None:
    select_brand(message)

@bot.message_handler(func=lambda m: m.text == "❌ Удалить авто")
def delete_car(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    user_vehicle.clear_vehicle(user_id)
    bot.send_message(message.chat.id, "❌ Авто удалено", reply_markup=my_car_menu_keyboard(False))

# ─────────────────────────────────────────────────────────────────────────────
# ИСТОРИЯ
# ─────────────────────────────────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "📋 История")
def btn_history(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    bot.send_message(message.chat.id, format_history(user_id), reply_markup=back_to_menu_keyboard())

# ─────────────────────────────────────────────────────────────────────────────
# СЕРВИСЫ И SOS
# ─────────────────────────────────────────────────────────────────────────────

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
    from sos_geo import find_city, _city_key
    city, dist = find_city(loc.latitude, loc.longitude)
    city_key = _city_key(city.name) if city and dist <= city.radius else ""
    text = format_sos(loc.latitude, loc.longitude)
    bot.send_message(message.chat.id, text, reply_markup=sos_inline_keyboard(city_key))

@bot.message_handler(func=lambda m: m.text == "🔙 Без геолокации (федеральные номера)")
def sos_no_geo(message: Message) -> None:
    bot.send_message(message.chat.id, format_sos(), reply_markup=sos_inline_keyboard())

# ─────────────────────────────────────────────────────────────────────────────
# ДИАЛОГОВАЯ ДИАГНОСТИКА
# ─────────────────────────────────────────────────────────────────────────────

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
    
    # Финальный диагноз
    for opt_key, diagnosis in node.diagnoses.items():
        if answer.startswith(opt_key[:50]):
            clear_state(user_id)
            add_entry(user_id, " → ".join(state.answers), diagnosis.title, diagnosis.urgency)
            text = f"<b>🔎 Диагноз Джека:</b>\n\n{format_diagnosis(diagnosis)}\n\n<i>Диагностика завершена.</i>"
            bot.send_message(chat_id, text, reply_markup=after_diagnostic_keyboard())
            return
    
    # Следующий узел
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

@bot.callback_query_handler(func=lambda c: True)
def on_callback(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)
    
    if call.data == "main_menu":
        bot.send_message(call.message.chat.id, welcome_text(), reply_markup=main_reply_keyboard())
    elif call.data == "get_services":
        bot.send_message(call.message.chat.id, format_services(SERVICES), reply_markup=back_to_menu_keyboard())
    elif call.data == "sos_ask":
        bot.send_message(call.message.chat.id, "📍 Отправьте геолокацию.", reply_markup=sos_location_keyboard())
    elif call.data == "new_diagnostic":
        btn_diagnostics(call.message)
    elif call.data.startswith("sponsor_sto_"):
        city_key = call.data.removeprefix("sponsor_sto_")
        try:
            from sponsors import format_sto_sponsors
            text = "🥇 <b>Партнёры Jarvis Auto</b>\n\n" + format_sto_sponsors(city_key)
            bot.send_message(call.message.chat.id, text, reply_markup=back_to_menu_keyboard())
        except:
            pass
    elif call.data.startswith("sponsor_kom_"):
        city_key = call.data.removeprefix("sponsor_kom_")
        try:
            from sponsors import get_gold_komissar
            gold = get_gold_komissar(city_key)
            if gold:
                text = f"🥇 <b>{gold.name}</b>  ╠══ ЗОЛОТОЙ ПАРТНЁР ══╣\n\n⏰ {gold.work_time}  |  ★ {gold.rating}\n📞 <code>{gold.phone}</code>\n🌐 {gold.url}"
                bot.send_message(call.message.chat.id, text, reply_markup=back_to_menu_keyboard())
        except:
            pass

# ─────────────────────────────────────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set.")
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
print("BOT STARTED")

if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0)
import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
