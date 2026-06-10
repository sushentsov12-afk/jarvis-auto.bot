"""
user_profile.py — профиль пользователя: уровень знания авто, роль.
"""
from __future__ import annotations
import sqlite3, os, logging
from datetime import datetime

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "jarvis.db")

LEVELS = {
    "novice": {
        "emoji": "🔰",
        "title": "Новичок",
        "desc": "Пользуюсь авто меньше года, механику не знаю",
    },
    "driver": {
        "emoji": "🚗",
        "title": "Автолюбитель",
        "desc": "Знаю базовые моменты, вожу больше года",
    },
    "garage": {
        "emoji": "🔧",
        "title": "Автогараж",
        "desc": "Делаю несложный ремонт, большой опыт вождения",
    },
    "mechanic": {
        "emoji": "⚙️",
        "title": "Автомеханик",
        "desc": "Починю машину, замена деталей, кузовной ремонт",
    },
    "expert": {
        "emoji": "🏆",
        "title": "Автоэксперт",
        "desc": "Знаю всё об авто, огромный опыт во всех областях",
    },
}


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            level TEXT DEFAULT 'novice',
            role TEXT DEFAULT 'user',
            onboarded INTEGER DEFAULT 0,
            rating REAL DEFAULT 0.0,
            answers_count INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    conn.commit()
    return conn


def get_profile(user_id: int) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT user_id, level, role, onboarded, rating, answers_count FROM user_profiles WHERE user_id = ?",
            (str(user_id),)
        ).fetchone()
    if not row:
        return None
    return {"user_id": row[0], "level": row[1], "role": row[2],
            "onboarded": row[3], "rating": row[4], "answers_count": row[5]}


def set_level(user_id: int, level: str) -> None:
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO user_profiles (user_id, level, onboarded, created_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET level=excluded.level, onboarded=1
        """, (str(user_id), level, datetime.now().isoformat()))


def set_role(user_id: int, role: str) -> None:
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO user_profiles (user_id, role, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role=excluded.role
        """, (str(user_id), role, datetime.now().isoformat()))


def is_onboarded(user_id: int) -> bool:
    p = get_profile(user_id)
    return bool(p and p.get("onboarded"))


def is_expert_or_mechanic(user_id: int) -> bool:
    p = get_profile(user_id)
    return bool(p and p.get("level") in ("mechanic", "expert"))


def add_answer_rating(user_id: int, rating: float) -> None:
    """Обновляет рейтинг эксперта после ответа."""
    with _get_conn() as conn:
        conn.execute("""
            UPDATE user_profiles
            SET answers_count = answers_count + 1,
                rating = (rating * answers_count + ?) / (answers_count + 1)
            WHERE user_id = ?
        """, (rating, str(user_id)))


def get_experts(limit: int = 10) -> list[dict]:
    """Возвращает список экспертов/механиков."""
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT u.user_id, u.level, u.rating, u.answers_count,
                   k.first_name, k.username
            FROM user_profiles u
            LEFT JOIN known_users k ON u.user_id = k.user_id
            WHERE u.level IN ('mechanic', 'expert')
            ORDER BY u.rating DESC, u.answers_count DESC
            LIMIT ?
        """, (limit,)).fetchall()
    cols = ["user_id", "level", "rating", "answers_count", "first_name", "username"]
    return [dict(zip(cols, r)) for r in rows]


def format_level_badge(level: str) -> str:
    l = LEVELS.get(level, LEVELS["novice"])
    return f"{l['emoji']} {l['title']}"
