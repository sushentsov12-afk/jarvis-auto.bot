"""
user_vehicle.py — хранение авто пользователя в SQLite.
Данные сохраняются между рестартами Railway.
"""
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "jarvis.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_vehicles (
            user_id TEXT PRIMARY KEY,
            brand TEXT,
            model TEXT,
            year TEXT
        )
    """)
    conn.commit()
    return conn


class UserVehicle:
    def set_vehicle(self, user_id: int, brand: str, model: str, year: str = None):
        with _get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_vehicles (user_id, brand, model, year)
                VALUES (?, ?, ?, ?)
            """, (str(user_id), brand, model, year))

    def get_vehicle(self, user_id: int):
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT brand, model, year FROM user_vehicles WHERE user_id = ?",
                (str(user_id),)
            ).fetchone()
        if row:
            return {"brand": row[0], "model": row[1], "year": row[2]}
        return None

    def clear_vehicle(self, user_id: int):
        with _get_conn() as conn:
            conn.execute("DELETE FROM user_vehicles WHERE user_id = ?", (str(user_id),))

    def has_vehicle(self, user_id: int) -> bool:
        return self.get_vehicle(user_id) is not None


user_vehicle = UserVehicle()
