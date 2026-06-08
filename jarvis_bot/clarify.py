"""
clarify.py — уточняющие вопросы когда бот не распознал симптом.
Задаёт 3 вопроса и пытается найти ответ заново.
"""
from __future__ import annotations
import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "jarvis.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS unknown_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            query TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    return conn


def save_unknown_query(user_id: int, query: str) -> None:
    """Сохраняем нераспознанный запрос для пополнения базы."""
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO unknown_queries (user_id, query, timestamp) VALUES (?, ?, ?)",
            (str(user_id), query, datetime.now().isoformat())
        )


def get_unknown_queries(limit: int = 50) -> list[dict]:
    """Возвращает последние нераспознанные запросы (для админа)."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT query, COUNT(*) as cnt FROM unknown_queries "
            "GROUP BY query ORDER BY cnt DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [{"query": r[0], "count": r[1]} for r in rows]


# Уточняющие вопросы по категориям
CLARIFY_QUESTIONS = [
    {
        "question": "🔧 <b>Когда именно возникает проблема?</b>",
        "options": [
            "При запуске / на холодную",
            "На холостых оборотах",
            "При разгоне",
            "На высокой скорости",
            "При торможении",
            "Постоянно"
        ]
    },
    {
        "question": "📍 <b>Откуда исходит симптом?</b>",
        "options": [
            "Из-под капота",
            "Из подвески / колёс",
            "Из салона",
            "Из выхлопной трубы",
            "Из тормозов",
            "Непонятно"
        ]
    },
    {
        "question": "⚠️ <b>Есть ли дополнительные признаки?</b>",
        "options": [
            "Горит Check Engine",
            "Посторонний запах",
            "Странный звук",
            "Потеря мощности",
            "Вибрация",
            "Ничего дополнительного"
        ]
    }
]


def build_clarify_text(original_query: str) -> str:
    return (
        f"🤔 <b>По запросу «{original_query}» не удалось точно определить причину.</b>\n\n"
        f"Давайте уточним — отвечайте на вопросы ниже, "
        f"и Джек постарается найти причину точнее."
    )
