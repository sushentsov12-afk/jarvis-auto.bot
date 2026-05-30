"""
user_history.py — история диагностических запросов пользователя.

Хранится в памяти (dict) — простое решение без БД.
При перезапуске бота история сбрасывается (достаточно для MVP).
При росте нагрузки — легко заменить на SQLite или Redis.
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque

MAX_HISTORY = 10  # максимум записей на пользователя


@dataclass
class HistoryEntry:
    query: str              # что написал пользователь
    result_name: str        # что нашли
    urgency: str            # critical / high / medium / low
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%d.%m %H:%M"))


# Хранилище: user_id → deque записей
_HISTORY: dict[int, Deque[HistoryEntry]] = {}


def add_entry(user_id: int, query: str, result_name: str, urgency: str) -> None:
    if user_id not in _HISTORY:
        _HISTORY[user_id] = deque(maxlen=MAX_HISTORY)
    _HISTORY[user_id].appendleft(
        HistoryEntry(query=query, result_name=result_name, urgency=urgency)
    )


def get_history(user_id: int) -> list[HistoryEntry]:
    return list(_HISTORY.get(user_id, []))


def has_history(user_id: int) -> bool:
    return bool(_HISTORY.get(user_id))


URGENCY_ICON = {
    "critical": "🚨",
    "high":     "⚠️",
    "medium":   "🔧",
    "low":      "ℹ️",
}


def format_history(user_id: int) -> str:
    entries = get_history(user_id)
    if not entries:
        return "📋 <b>История диагностики пуста.</b>\n\nОпишите симптом — Джек найдёт причину."

    lines = ["📋 <b>Ваша история диагностики</b>\n"]
    for i, e in enumerate(entries, 1):
        icon = URGENCY_ICON.get(e.urgency, "🔧")
        lines.append(
            f"{i}. {icon} <b>{e.result_name}</b>\n"
            f"   <i>«{e.query[:60]}»</i>\n"
            f"   🕐 {e.timestamp}"
        )
    return "\n\n".join(lines)
