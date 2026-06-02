"""
diagnostic.py — движок нечёткого поиска неисправностей по народным запросам.

Использует rapidfuzz (token_set_ratio) для поиска по фразам «своими словами».
База: data/diagnostic_base.json — 55 категорий, >300 поисковых тегов.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz

from config import DATA_DIR

# ─────────────────────────────────────────────────────────────────
# Загрузка базы
# ─────────────────────────────────────────────────────────────────

_DB: list[dict] = []


def _load_db() -> list[dict]:
    global _DB
    if not _DB:
        path = DATA_DIR / "diagnostic_base.json"
        with open(path, encoding="utf-8") as f:
            _DB = json.load(f)
    return _DB


# ─────────────────────────────────────────────────────────────────
# OBD-паттерн
# ─────────────────────────────────────────────────────────────────

OBD_RE = re.compile(r"\b[PBCU]\d{4}\b", re.IGNORECASE)

URGENCY_EMOJI = {
    "critical": "🚨",
    "high":     "⚠️",
    "medium":   "🔧",
    "low":      "ℹ️",
}

URGENCY_LABEL = {
    "critical": "КРИТИЧНО — немедленно на СТО",
    "high":     "Срочно — в ближайшие дни",
    "medium":   "Плановый ремонт",
    "low":      "Несрочно",
}


# ─────────────────────────────────────────────────────────────────
# Поиск
# ─────────────────────────────────────────────────────────────────

def search_by_code(code: str) -> Optional[dict]:
    """Точный поиск по OBD-коду."""
    code = code.upper().strip()
    for item in _load_db():
        if code == item.get("obd_code", "").upper():
            return item
        oem = item.get("oem_code", "")
        if code in [c.strip().upper() for c in oem.split(",")]:
            return item
    return None


def search_by_phrase(user_input: str, threshold: int = 42) -> tuple[Optional[dict], int]:
    """
    Нечёткий поиск по народным запросам.
    Возвращает (результат, уровень_уверенности).
    threshold=42 — оптимальный баланс точности и охвата.
    """
    text = user_input.lower().strip()
    best_item: Optional[dict] = None
    best_score = 0

    for item in _load_db():
        for query in item.get("user_queries", []):
            score = fuzz.token_set_ratio(text, query.lower())
            if score > best_score:
                best_score = score
                best_item = item

    if best_score >= threshold:
        return best_item, int(best_score)
    return None, int(best_score)


def smart_search(user_input: str) -> Optional[dict]:
    """
    Умный поиск: сначала ищет OBD-код, потом нечёткий поиск по фразе.
    """
    # 1. Есть OBD-код в тексте?
    codes = OBD_RE.findall(user_input)
    if codes:
        hit = search_by_code(codes[0])
        if hit:
            return hit

    # 2. Нечёткий поиск по фразе
    result, _ = search_by_phrase(user_input)
    return result


# ─────────────────────────────────────────────────────────────────
# Форматирование ответа
# ─────────────────────────────────────────────────────────────────

def format_diagnostic(item: dict, confidence: int | None = None) -> str:
    urgency = item.get("urgency", "medium")
    emoji = URGENCY_EMOJI.get(urgency, "🔧")
    label = URGENCY_LABEL.get(urgency, "")

    obd = item.get("obd_code", "")
    obd_line = f"<b>Код ошибки:</b> <code>{obd}</code>\n" if obd and obd != "нет" else ""

    conf_line = ""
    if confidence is not None:
        bar = "█" * (confidence // 10) + "░" * (10 - confidence // 10)
        conf_line = f"<i>Уверенность: {bar} {confidence}%</i>\n\n"

    price = item.get("price_range", "")
    price_line = f"<b>💰 Примерная стоимость:</b> {price}\n" if price else ""

    # Образовательный блок
    lesson  = item.get("lesson", "")
    diy     = item.get("diy", "")
    warning = item.get("warning", "")
    lesson_line  = f"\n\n📖 <b>Полезно знать:</b>\n<i>{lesson}</i>" if lesson else ""
    diy_line     = f"\n\n🛠 <b>Можно сделать самому:</b>\n{diy}" if diy else ""
    warning_line = f"\n\n⚡ <b>Запомните на будущее:</b>\n<i>{warning}</i>" if warning else ""

    return (
        f"{emoji} <b>{item['technical_name']}</b>\n"
        f"<i>{label}</i>\n\n"
        f"{conf_line}"
        f"{obd_line}"
        f"<b>📋 Что происходит:</b>\n{item['ru_description']}\n\n"
        f"<b>🔍 Вероятная причина:</b>\n{item['probable_cause']}\n\n"
        f"<b>🔧 Что нужно сделать:</b>\n{item['action_required']}"
        f"\n\n<b>💰 Примерная стоимость:</b> {price}" if price else ""
    ) + (
        f"{lesson_line}"
        f"{diy_line}"
        f"{warning_line}"
        f"\n\n<i>Уточните код OBD или обратитесь на СТО для точной диагностики.</i>"
    )
