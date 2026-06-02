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
from formatters import (
    format_ai_fallback,
    format_part,
    format_services,
    help_text,
    welcome_text,
)
from keyboards import (
    main_inline_keyboard,
    main_reply_keyboard,
    sos_location_keyboard,
    sos_inline_keyboard,
    after_diagnostic_keyboard,
    dialog_options_keyboard,
    vehicle_brands_keyboard,
    vehicle_models_keyboard,
    vehicle_years_keyboard,
)
from sos_geo import format_sos
from vehicle_db import (
    get_all_brands,
    get_models_by_brand,
    get_common_issues,
    format_vehicle_issues,
)
from user_vehicle import (
    set_user_vehicle,
    get_user_vehicle,
    clear_user_vehicle,
    has_vehicle,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jarvis")

PARTS = load_parts()
SERVICES = load_services()

bot: TeleBot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# Временные переменные для процесса выбора авто
_vehicle_selection_state: dict[int, dict] = {}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def send_main_menu(
    chat_id: int,
    first_name: str | None = None,
    username: str | None = None,
    text: str | None = None,
) -> None:
    bot.send_message(
        chat_id,
        text or welcome_text(first_name, username),
        reply_markup=main_reply_keyboard(),
    )
    bot.send_message(
        chat_id,
        "Выберите из меню или введите код OBD / симптом:",
        reply_markup=main_inline_keyboard(),
    )


def reply_with_part(message: Message, part, title: str = "Рекомендация") -> None:
    bot.send_message(
        message.chat.id,
        format_part(part, title=title),
        reply_markup=main_inline_keyboard(),
        disable_web_page_preview=True,
    )


def ask_for_location(chat_id: int) -> None:
    """Просим геолокацию перед показом SOS."""
    bot.send_message(
        chat_id,
        "📍 <b>SOS</b>\n\n"
        "Отправьте геолокацию — покажу <b>местный номер ГИБДД</b> "
        "и ближайших аварийных комиссаров.\n\n"
        "Или нажмите «Без геолокации» — получите федеральные номера.",
        reply_markup=sos_location_keyboard(),
    )


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    user = message.from_user
    send_main_menu(
        message.chat.id,
        first_name=user.first_name if user else None,
        username=user.username if user else None,
    )


@bot.message_handler(commands=["help"])
def cmd_help(message: Message) -> None:
    bot.send_message(
        message.chat.id,
        help_text(ai_assistant.is_enabled()),
        reply_markup=main_reply_keyboard(),
    )


@bot.message_handler(commands=["services"])
def cmd_services(message: Message) -> None:
    bot.send_message(
        message.chat.id,
        format_services(SERVICES, city_key="yoshkar_ola"),
        reply_markup=main_inline_keyboard(city_key="yoshkar_ola"),
    )


@bot.message_handler(commands=["sos"])
def cmd_sos(message: Message) -> None:
    ask_for_location(message.chat.id)


# ──────────────────────────────────────────────
# Vehicle Selection Flow
# ──────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text == "🚗 Моё авто")
def btn_select_vehicle(message: Message) -> None:
    """Начинаем процесс выбора авто."""
    user_id = message.from_user.id if message.from_user else 0
    
    # Проверяем, уже ли выбрано авто
    vehicle = get_user_vehicle(user_id)
    if vehicle:
        bot.send_message(
            message.chat.id,
            f"<b>Ваше авто:</b> {vehicle}\n\n"
            f"Хотите изменить? Нажмите 🚗 Моё авто или введите новую марку.",
            reply_markup=main_inline_keyboard(),
        )
        return
    
    # Начинаем выбор марки
    brands = get_all_brands()
    _vehicle_selection_state[user_id] = {"stage": "brand"}
    
    bot.send_message(
        message.chat.id,
        "<b>🚗 Выбор автомобиля</b>\n\nВыберите марку вашего автомобиля:",
        reply_markup=vehicle_brands_keyboard(brands),
    )


@bot.message_handler(func=lambda m: m.text == "🔙 Отмена")
def btn_vehicle_cancel(message: Message) -> None:
    """Отмена выбора авто."""
    user_id = message.from_user.id if message.from_user else 0
    if user_id in _vehicle_selection_state:
        del _vehicle_selection_state[user_id]
    
    bot.send_message(
        message.chat.id,
        "Выбор авто отменён.",
        reply_markup=main_reply_keyboard(),
    )


# ──────────────────────────────────────────────
# Reply keyboard buttons
# ──────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text in ("❓ Справка", "Справка", "/help"))
def btn_help(message: Message) -> None:
    cmd_help(message)


@bot.message_handler(func=lambda m: m.text in ("📋 Моя история", "/history"))
def btn_history(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    bot.send_message(
        message.chat.id,
        format_history(user_id),
        reply_markup=main_inline_keyboard(),
    )


@bot.message_handler(func=lambda m: m.text in ("🏪 Автосервисы", "Автосервисы", "/services"))
def btn_services(message: Message) -> None:
    cmd_services(message)


@bot.message_handler(func=lambda m: m.text in ("🆘 SOS", "/sos"))
def btn_sos(message: Message) -> None:
    ask_for_location(message.chat.id)


@bot.message_handler(func=lambda m: m.text == "🔙 Без геолокации (федеральные номера)")
def btn_sos_no_geo(message: Message) -> None:
    """Пользователь отказался от геолокации — даём федеральные номера."""
    bot.send_message(
        message.chat.id,
        format_sos(),                    # без координат
        reply_markup=main_inline_keyboard(),
        disable_web_page_preview=True,
    )


@bot.message_handler(func=lambda m: m.text in ("🔍 Диагностика", "Коды OBD"))
def btn_diagnostics(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    vehicle = get_user_vehicle(user_id)
    
    if vehicle:
        msg = (
            f"<b>Диагностика</b>\n"
            f"Авто: {vehicle}\n\n"
            f"Введите код OBD (например, <code>P0301</code>) "
            f"или опишите симптом (например, <i>стук при торможении</i>):"
        )
    else:
        msg = (
            "⚠️ Сначала выберите ваше авто (кнопка 🚗 Моё авто), "
            "чтобы я показал типичные проблемы.\n\n"
            "Или введите код OBD или симптом:"
        )
    
    bot.send_message(
        message.chat.id,
        msg,
        reply_markup=main_inline_keyboard(),
    )


# ──────────────────────────────────────────────
# Vehicle Selection Text Handler
# ──────────────────────────────────────────────

@bot.message_handler(content_types=["text"], func=lambda m: m.from_user.id in _vehicle_selection_state)
def on_vehicle_selection_text(message: Message) -> None:
    """Обработка ввода при выборе авто."""
    user_id = message.from_user.id if message.from_user else 0
    text = (message.text or "").strip()
    
    if not user_id in _vehicle_selection_state:
        return
    
    state = _vehicle_selection_state[user_id]
    stage = state.get("stage", "brand")
    
    # STAGE 1: Выбор марки
    if stage == "brand":
        selected_brand = text
        models = get_models_by_brand(selected_brand)
        
        if not models:
            bot.send_message(
                message.chat.id,
                f"❌ Марка '{selected_brand}' не найдена. Попробуйте ещё раз.",
                reply_markup=vehicle_brands_keyboard(get_all_brands()),
            )
            return
        
        state["brand"] = selected_brand
        state["stage"] = "model"
        bot.send_message(
            message.chat.id,
            f"<b>Марка:</b> {selected_brand}\n\nВыберите модель:",
            reply_markup=vehicle_models_keyboard(models),
        )
        return
    
    # STAGE 2: Выбор модели
    elif stage == "model":
        # Извлекаем название модели из ответа (формат: "Model (2000-2030)")
        model_name = text.split(" (")[0].strip()
        selected_brand = state.get("brand", "")
        
        models = get_models_by_brand(selected_brand)
        matched_model = next((m for m in models if m.get("model", "").lower() == model_name.lower()), None)
        
        if not matched_model:
            bot.send_message(
                message.chat.id,
                f"❌ Модель '{model_name}' не найдена. Попробуйте ещё раз.",
                reply_markup=vehicle_models_keyboard(models),
            )
            return
        
        state["model"] = matched_model.get("model", "")
        state["years"] = matched_model.get("years", [2000, 2030])
        state["stage"] = "year"
        
        bot.send_message(
            message.chat.id,
            f"<b>Модель:</b> {state['model']}\n\nВыберите год выпуска:",
            reply_markup=vehicle_years_keyboard(state["years"][0], state["years"][1]),
        )
        return
    
    # STAGE 3: Выбор года
    elif stage == "year":
        try:
            year = int(text)
            years_range = state.get("years", [2000, 2030])
            
            if not (years_range[0] <= year <= years_range[1]):
                bot.send_message(
                    message.chat.id,
                    f"❌ Год должен быть от {years_range[0]} до {years_range[1]}.",
                    reply_markup=vehicle_years_keyboard(years_range[0], years_range[1]),
                )
                return
            
            # Сохраняем авто
            brand = state.get("brand", "")
            model = state.get("model", "")
            vehicle = set_user_vehicle(user_id, brand, model, year)
            
            # Показываем типичные ошибки
            issues_text = format_vehicle_issues(brand, model, year)
            
            del _vehicle_selection_state[user_id]
            
            bot.send_message(
                message.chat.id,
                f"<b>✅ Ваше авто сохранено:</b>\n{vehicle}\n\n{issues_text}",
                reply_markup=main_reply_keyboard(),
                disable_web_page_preview=True,
            )
            
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Пожалуйста, введите год числом (например, 2020).",
                reply_markup=vehicle_years_keyboard(state.get("years", [2000, 2030])[0], state.get("years", [2000, 2030])[1]),
            )


# ──────────────────────────────────────────────
# Геолокация — ГЛАВНЫЙ обработчик SOS
# ──────────────────────────────────────────────

@bot.message_handler(content_types=["location"])
def on_location(message: Message) -> None:
    loc = message.location
    if not loc:
        return

    lat, lon = loc.latitude, loc.longitude
    logger.info("Location received: lat=%.4f lon=%.4f from user=%s",
                lat, lon, message.from_user.id)

    # Определяем city_key для спонсорских кнопок
    from sos_geo import find_city, _city_key
    city, dist = find_city(lat, lon)
    city_key = _city_key(city.name) if city and dist <= city.radius else ""

    text = format_sos(lat, lon)
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=sos_inline_keyboard(city_key),
        disable_web_page_preview=True,
    )
    bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=main_reply_keyboard(),
    )


# ──────────────────────────────────────────────
# Inline callbacks
# ──────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("diag_"))
def on_dialog_answer(call: CallbackQuery) -> None:
    """Обрабатывает ответ пользователя в диалоге диагностики."""
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id if call.from_user else 0
    chat_id = call.message.chat.id

    # Отмена диалога
    if call.data == "diag_cancel":
        clear_state(user_id)
        bot.send_message(chat_id, "Диагностика отменена. Чем ещё могу помочь?",
                         reply_markup=main_inline_keyboard())
        return

    # Разбираем ответ: "diag_{tree_id}::{answer}"
    try:
        _, rest = call.data.split("diag_", 1)
        tree_id, answer = rest.split("::", 1)
    except ValueError:
        return

    state = get_state(user_id)
    if not state or state.tree_id != tree_id:
        bot.send_message(chat_id, "Сессия диалога устарела. Опишите симптом заново.",
                         reply_markup=main_inline_keyboard())
        return

    # Найдём текущий узел
    from dialog_engine import DIALOG_TREES
    tree = next((t for t in DIALOG_TREES if t.tree_id == tree_id), None)
    if not tree:
        clear_state(user_id)
        return

    node = get_node(tree, state.current_node_id)
    if not node:
        clear_state(user_id)
        return

    state.answers.append(answer)

    # Сначала проверяем финальные диагнозы текущего узла
    for opt_key, diagnosis in node.diagnoses.items():
        if answer.startswith(opt_key[:50]):
            # Финальный диагноз найден
            clear_state(user_id)
            add_entry(user_id, " → ".join(state.answers),
                      diagnosis.title, diagnosis.urgency)
            text = (
                f"<b>🔎 Диагноз Джека:</b>\n\n"
                f"{format_diagnosis(diagnosis)}\n\n"
                f"<i>Диагностика завершена.</i>"
            )
            bot.send_message(chat_id, text,
                             reply_markup=after_diagnostic_keyboard(),
                             disable_web_page_preview=True)
            return

    # Переходим к следующему узлу
    next_node_id = None
    for opt_key, nid in node.next_nodes.items():
        if answer.startswith(opt_key[:50]):
            next_node_id = nid
            break

    if not next_node_id:
        clear_state(user_id)
        bot.send_message(chat_id, "Не смог обработать ответ. Попробуйте снова.",
                         reply_markup=main_inline_keyboard())
        return

    next_node = get_node(tree, next_node_id)
    if not next_node:
        clear_state(user_id)
        return

    state.current_node_id = next_node_id
    set_state(user_id, state)

    hint = f"\n<i>{next_node.hint}</i>" if next_node.hint else ""
    bot.send_message(
        chat_id,
        f"<b>{next_node.question}</b>{hint}",
        reply_markup=dialog_options_keyboard(next_node.options, tree_id),
    )


@bot.callback_query_handler(func=lambda c: True)
def on_callback(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)

    if call.data == "main_menu":
        user = call.from_user
        bot.edit_message_text(
            welcome_text(
                first_name=user.first_name if user else None,
                username=user.username if user else None,
            ),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_inline_keyboard(),
        )
        return

    if call.data == "get_services":
        bot.edit_message_text(
            format_services(SERVICES),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_inline_keyboard(),
        )
        return

    if call.data == "sos_ask":
        bot.send_message(
            call.message.chat.id,
            "📍 <b>SOS</b>\n\n"
            "Отправьте геолокацию — покажу местный ГИБДД и комиссаров.\n"
            "Или нажмите «Без геолокации».",
            reply_markup=sos_location_keyboard(),
        )
        return

    if call.data.startswith("sponsor_sto_"):
        city_key = call.data.removeprefix("sponsor_sto_")
        from sponsors import format_sto_sponsors
        text = (
            "🥇 <b>Рекомендованные СТО — партнёры Jarvis Auto</b>\n\n"
            + format_sto_sponsors(city_key)
        )
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=main_inline_keyboard(city_key=city_key),
            disable_web_page_preview=True,
        )
        return

    if call.data.startswith("sponsor_kom_"):
        city_key = call.data.removeprefix("sponsor_kom_")
        from sponsors import get_gold_komissar
        gold = get_gold_komissar(city_key)
        if gold:
            text = (
                f"🥇 <b>{gold.name}</b>  ╠══ ЗОЛОТОЙ ПАРТНЁР ══╣\n\n"
                f"⏰ {gold.work_time}  |  ★ {gold.rating}\n"
                f"📞 <code>{gold.phone}</code>\n"
                f"🌐 {gold.url}\n\n"
                f"📍 {gold.address}\n\n"
                f"<i>Расходы на оформление ДТП возместит страховая компания!</i>"
            )
            bot.send_message(
                call.message.chat.id,
                text,
                reply_markup=sos_inline_keyboard(city_key),
                disable_web_page_preview=True,
            )
        return

    if call.data.startswith("sym_"):
        code = call.data.removeprefix("sym_")
        part = find_by_obd(code, PARTS) or next(
            (p for p in PARTS if p.id == code), None
        )
        if not part:
            bot.edit_message_text(
                f"Информация по коду {code} не найдена.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_inline_keyboard(),
            )
            return

        bot.edit_message_text(
            format_part(part, title=f"Диагностика {part.id}"),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_inline_keyboard(),
            disable_web_page_preview=True,
        )


# ──────────────────────────────────────────────
# Свободный текст
# ──────────────────────────────────────────────

@bot.message_handler(content_types=["text"])
def on_text(message: Message) -> None:
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return

    bot.send_chat_action(message.chat.id, "typing")
    user_id = message.from_user.id if message.from_user else 0

    # 0. Проверяем — есть ли подходящий диалог для этого симптома
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

    # 1. Точный поиск по OBD-коду или симптому из старого каталога
    part = find_best_match(text, PARTS)
    if part:
        title = f"Диагностика {part.id}" if part.type == "obd" else "Подбор по симптому"
        reply_with_part(message, part, title=title)
        return

    # 2. Умный нечёткий поиск по народным запросам (diagnostic_base.json)
    result, confidence = search_by_phrase(text)
    if result:
        # Сохраняем в историю пользователя
        user_id = message.from_user.id if message.from_user else 0
        add_entry(user_id, text, result["technical_name"], result.get("urgency", "medium"))

        answer = format_diagnostic(result, confidence)
        bot.send_message(
            message.chat.id,
            f"<b>🔎 Джек нашёл похожую проблему:</b>\n\n{answer}",
            reply_markup=after_diagnostic_keyboard(),
            disable_web_page_preview=True,
        )
        return

    # 3. GigaChat AI — если подключён
    if ai_assistant.is_enabled():
        try:
            answer = ai_assistant.ask(text)
            bot.send_message(
                message.chat.id,
                f"<b>Джек (AI):</b>\n\n{answer}",
                reply_markup=main_inline_keyboard(),
            )
            return
        except Exception:
            logger.exception("GigaChat request failed")

    # 4. Fallback
    bot.send_message(
        message.chat.id,
        format_ai_fallback(text),
        reply_markup=main_inline_keyboard(),
    )


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Create a .env file (see .env.example).")
        sys.exit(1)

    proxies = resolve_proxy()
    if proxies:
        apihelper.proxy = proxies

    if not check_telegram(BOT_TOKEN, proxies):
        sys.exit(1)

    logger.info(
        "Jarvis Auto started (AI: %s)",
        "on" if ai_assistant.is_enabled() else "off",
    )
    bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
