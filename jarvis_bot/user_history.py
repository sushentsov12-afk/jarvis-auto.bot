"""
user_history.py — история диагностики в SQLite.
Сохраняется между рестартами.
"""
from __future__ import annotations
import sqlite3
import os
from datetime import datetime
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "jarvis.db")
MAX_HISTORY = 10


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            query TEXT,
            result_name TEXT,
            urgency TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    return conn


@dataclass
class HistoryEntry:
    query: str
    result_name: str
    urgency: str
    timestamp: str


URGENCY_ICON = {
    "critical": "🚨",
    "high":     "⚠️",
    "medium":   "🔧",
    "low":      "ℹ️",
}


def add_entry(user_id: int, query: str, result_name: str, urgency: str) -> None:
    ts = datetime.now().strftime("%d.%m %H:%M")
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO user_history (user_id, query, result_name, urgency, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (str(user_id), query, result_name, urgency, ts))
        # Оставляем только последние MAX_HISTORY записей
        conn.execute("""
            DELETE FROM user_history WHERE user_id = ? AND id NOT IN (
                SELECT id FROM user_history WHERE user_id = ?
                ORDER BY id DESC LIMIT ?
            )
        """, (str(user_id), str(user_id), MAX_HISTORY))


def get_history(user_id: int) -> list[HistoryEntry]:
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT query, result_name, urgency, timestamp
            FROM user_history WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
        """, (str(user_id), MAX_HISTORY)).fetchall()
    return [HistoryEntry(query=r[0], result_name=r[1], urgency=r[2], timestamp=r[3]) for r in rows]


def has_history(user_id: int) -> bool:
    with _get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM user_history WHERE user_id = ?",
            (str(user_id),)
        ).fetchone()[0]
    return count > 0


def format_history(user_id: int) -> str:
    entries = get_history(user_id)
    if not entries:
        return "📋 <b>История пуста</b>\n\nПройдите диагностику, чтобы она появилась здесь."
    lines = ["📋 <b>Последние диагностики:</b>\n"]
    for e in entries:
        icon = URGENCY_ICON.get(e.urgency, "🔧")
        lines.append(f"{icon} <b>{e.result_name}</b>\n   <i>{e.query[:40]}...</i> • {e.timestamp}")
    return "\n".join(lines)
