"""
broadcaster.py — рассылка уведомлений всем пользователям бота.
Использует SQLite для хранения user_id.
"""
from __future__ import annotations
import sqlite3
import logging
import time
import os

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "jarvis.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS known_users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registered_at TEXT
        )
    """)
    conn.commit()
    return conn


def register_user(user_id: int, username: str = "", first_name: str = "") -> None:
    """Регистрирует пользователя при первом /start."""
    from datetime import datetime
    with _get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO known_users (user_id, username, first_name, registered_at)
            VALUES (?, ?, ?, ?)
        """, (str(user_id), username or "", first_name or "", datetime.now().isoformat()))


def get_all_users() -> list[str]:
    """Возвращает список всех user_id."""
    with _get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM known_users").fetchall()
    return [r[0] for r in rows]


def get_user_count() -> int:
    with _get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM known_users").fetchone()[0]


def broadcast(bot, text: str, parse_mode: str = "HTML") -> dict:
    """
    Отправляет сообщение всем пользователям.
    Возвращает статистику: {'sent': N, 'failed': N}
    """
    users = get_all_users()
    sent = 0
    failed = 0

    for user_id in users:
        try:
            bot.send_message(int(user_id), text, parse_mode=parse_mode)
            sent += 1
            time.sleep(0.05)  # Не превышать лимит Telegram (20 msg/s)
        except Exception as e:
            logger.warning("Broadcast failed for %s: %s", user_id, e)
            failed += 1

    logger.info("Broadcast done: sent=%d failed=%d", sent, failed)
    return {"sent": sent, "failed": failed}
