import logging
import sys

from telebot import TeleBot, apihelper
from telebot.types import CallbackQuery, Message

import ai_assistant
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
)
from sos_geo import format_sos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jarvis")

PARTS = load_parts()
SERVICES = load_services()

bot: TeleBot = TeleBot(BOT_TOKEN, parse_mode="HTML")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def send_main_menu(chat_id: int, text: str | None = None) -> None:
    bot.send_message(
        chat_id,
        text or welcome_text(),
        reply_markup=main_reply_keyboard(),
    )
    bot.send_message(
        chat_id,
        "Выберите из меню или введите код OBD / симптом:",
        reply_markup=main_inline_keyboard(PARTS),
    )


def reply_with_part(message: Message, part, title: str = "Рекомендация") -> None:
    bot.send_message(
        message.chat.id,
        format_part(part, title=title),
        reply_markup=main_inline_keyboard(PARTS),
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
    send_main_menu(message.chat.id)


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
        format_services(SERVICES),
        reply_markup=main_inline_keyboard(PARTS),
    )


@bot.message_handler(commands=["sos"])
def cmd_sos(message: Message) -> None:
    ask_for_location(message.chat.id)


# ──────────────────────────────────────────────
# Reply keyboard buttons
# ──────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text in ("❓ Справка", "Справка", "/help"))
def btn_help(message: Message) -> None:
    cmd_help(message)


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
        reply_markup=main_inline_keyboard(PARTS),
        disable_web_page_preview=True,
    )


@bot.message_handler(func=lambda m: m.text in ("🔍 Диагностика", "Коды OBD"))
def btn_diagnostics(message: Message) -> None:
    bot.send_message(
        message.chat.id,
        "Введите код OBD (например, <code>P0301</code>) "
        "или опишите симптом (например, <i>стук при торможении</i>):",
        reply_markup=main_inline_keyboard(PARTS),
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

    text = format_sos(lat, lon)
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_inline_keyboard(PARTS),
        disable_web_page_preview=True,
    )
    # Возвращаем обычную клавиатуру после one-time клавиатуры геолокации
    bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=main_reply_keyboard(),
    )


# ──────────────────────────────────────────────
# Inline callbacks
# ──────────────────────────────────────────────

@bot.callback_query_handler(func=lambda c: True)
def on_callback(call: CallbackQuery) -> None:
    bot.answer_callback_query(call.id)

    if call.data == "main_menu":
        bot.edit_message_text(
            welcome_text(),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_inline_keyboard(PARTS),
        )
        return

    if call.data == "get_services":
        bot.edit_message_text(
            format_services(SERVICES),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_inline_keyboard(PARTS),
        )
        return

    if call.data == "sos_ask":
        # Инлайн-кнопка SOS → просим геолокацию
        bot.send_message(
            call.message.chat.id,
            "📍 <b>SOS</b>\n\n"
            "Отправьте геолокацию — покажу местный ГИБДД и комиссаров.\n"
            "Или нажмите «Без геолокации».",
            reply_markup=sos_location_keyboard(),
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
                reply_markup=main_inline_keyboard(PARTS),
            )
            return

        bot.edit_message_text(
            format_part(part, title=f"Диагностика {part.id}"),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_inline_keyboard(PARTS),
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

    part = find_best_match(text, PARTS)
    if part:
        title = f"Диагностика {part.id}" if part.type == "obd" else "Подбор по симптому"
        reply_with_part(message, part, title=title)
        return

    if ai_assistant.is_enabled():
        bot.send_chat_action(message.chat.id, "typing")
        try:
            answer = ai_assistant.ask(text)
            bot.send_message(
                message.chat.id,
                f"<b>Jarvis (AI):</b>\n\n{answer}",
                reply_markup=main_inline_keyboard(PARTS),
            )
            return
        except Exception:
            logger.exception("GigaChat request failed")

    bot.send_message(
        message.chat.id,
        format_ai_fallback(text),
        reply_markup=main_inline_keyboard(PARTS),
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
