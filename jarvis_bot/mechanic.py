"""
mechanic.py — модуль вопросов к механику.
Пользователь задаёт вопрос → механик отвечает в Telegram → ответ сохраняется в базу.
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
        CREATE TABLE IF NOT EXISTS mechanic_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            username TEXT,
            first_name TEXT,
            car_info TEXT,
            question TEXT,
            answer TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            answered_at TEXT,
            chat_id TEXT
        )
    """)
    conn.commit()
    return conn


def save_question(user_id: int, username: str, first_name: str,
                  car_info: str, question: str, chat_id: int) -> int:
    """Сохраняет вопрос и возвращает его ID."""
    with _get_conn() as conn:
        cursor = conn.execute("""
            INSERT INTO mechanic_questions
            (user_id, username, first_name, car_info, question, status, created_at, chat_id)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (str(user_id), username or "", first_name or "",
              car_info or "", question, datetime.now().isoformat(), str(chat_id)))
        return cursor.lastrowid


def get_question(question_id: int) -> dict | None:
    """Получает вопрос по ID."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM mechanic_questions WHERE id = ?",
            (question_id,)
        ).fetchone()
    if not row:
        return None
    cols = ["id", "user_id", "username", "first_name", "car_info",
            "question", "answer", "status", "created_at", "answered_at", "chat_id"]
    return dict(zip(cols, row))


def save_answer(question_id: int, answer: str) -> bool:
    """Сохраняет ответ механика."""
    with _get_conn() as conn:
        conn.execute("""
            UPDATE mechanic_questions
            SET answer = ?, status = 'answered', answered_at = ?
            WHERE id = ?
        """, (answer, datetime.now().isoformat(), question_id))
    return True


def get_pending_questions(limit: int = 10) -> list[dict]:
    """Возвращает неотвеченные вопросы."""
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT id, user_id, username, first_name, car_info, question, created_at
            FROM mechanic_questions WHERE status = 'pending'
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
    cols = ["id", "user_id", "username", "first_name", "car_info", "question", "created_at"]
    return [dict(zip(cols, r)) for r in rows]


def get_stats() -> dict:
    """Статистика вопросов."""
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM mechanic_questions").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM mechanic_questions WHERE status='pending'").fetchone()[0]
        answered = conn.execute("SELECT COUNT(*) FROM mechanic_questions WHERE status='answered'").fetchone()[0]
    return {"total": total, "pending": pending, "answered": answered}


def save_to_diagnostic_base(question_id: int) -> bool:
    """
    Сохраняет вопрос+ответ механика в diagnostic_base.json через GigaChat.
    """
    q = get_question(question_id)
    if not q or not q.get("answer"):
        return False

    try:
        from ai_assistant import analyze_and_save
        combined = f"Вопрос: {q['question']}\nОтвет механика: {q['answer']}"
        return analyze_and_save(combined)
    except Exception:
        logger.exception("Ошибка сохранения в базу")
        return False


def format_question_for_admin(q: dict) -> str:
    """Форматирует вопрос для отправки механику."""
    car = q.get("car_info") or "не указано"
    username = q.get("username")
    name = q.get("first_name") or "Пользователь"
    user_str = f"@{username}" if username else f"id:{q['user_id']}"
    ts = q.get("created_at", "")[:16].replace("T", " ")

    return (
        f"\U0001f527 <b>Вопрос механику #{q['id']}</b>\n\n"
        f"\U0001f464 {name} ({user_str})\n"
        f"\U0001f697 Авто: {car}\n"
        f"\U0001f4c5 {ts}\n\n"
        f"\U0001f4ac <b>Вопрос:</b>\n{q['question']}\n\n"
        f"<i>Ответить:</i> /answer_{q['id']} [текст ответа]\n"
        f"<i>Добавить в базу:</i> /add_{q['id']}"
    )


def save_expert_assigned(question_id: int, expert_id: int) -> None:
    """Назначает эксперта на вопрос."""
    with _get_conn() as conn:
        conn.execute(
            "ALTER TABLE mechanic_questions ADD COLUMN expert_id TEXT",
        ) if "expert_id" not in [
            r[1] for r in conn.execute("PRAGMA table_info(mechanic_questions)")
        ] else None
        conn.execute(
            "UPDATE mechanic_questions SET expert_id=?, status='taken' WHERE id=?",
            (str(expert_id), question_id)
        )


def notify_experts(bot, question_id: int) -> int:
    """
    Рассылает вопрос всем экспертам и механикам.
    Возвращает количество уведомлённых.
    """
    from user_profile import get_experts
    from keyboards import expert_question_keyboard

    experts = get_experts(20)
    q = get_question(question_id)
    if not q:
        return 0

    car = q.get("car_info") or "не указано"
    text = (
        f"\U0001f6a8 <b>Новый вопрос от пользователя</b>\n\n"
        f"\U0001f697 Авто: {car}\n\n"
        f"\U0001f4ac <b>Вопрос:</b>\n{q['question']}"
    )

    sent = 0
    for expert in experts:
        try:
            bot.send_message(
                int(expert["user_id"]),
                text,
                reply_markup=expert_question_keyboard(question_id),
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            pass
    return sent
