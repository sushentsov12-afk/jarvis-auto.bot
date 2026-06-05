"""
version_manager.py — управление версией бота и уведомлениями об обновлениях.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from .config import DATA_DIR, BASE_DIR

CURRENT_VERSION_FILE = BASE_DIR / "VERSION"
USER_VERSIONS_FILE = DATA_DIR / "user_versions.json"


def get_current_version() -> str:
    """Возвращает текущую версию бота из файла VERSION."""
    try:
        with open(CURRENT_VERSION_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "1.0.0"


def _load_user_versions() -> dict[int, str]:
    """Загружает версии пользователей."""
    if not USER_VERSIONS_FILE.exists():
        return {}
    
    try:
        with open(USER_VERSIONS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_user_versions(versions: dict[int, str]) -> None:
    """Сохраняет версии пользователей."""
    with open(USER_VERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)


def get_user_version(user_id: int) -> str:
    """Возвращает версию бота, которую видел пользователь."""
    versions = _load_user_versions()
    return versions.get(str(user_id), "0.0.0")


def set_user_version(user_id: int, version: str) -> None:
    """Обновляет версию для пользователя."""
    versions = _load_user_versions()
    versions[str(user_id)] = version
    _save_user_versions(versions)


def needs_update_notification(user_id: int) -> bool:
    """Проверяет, нужно ли отправить уведомление об обновлении."""
    user_version = get_user_version(user_id)
    current_version = get_current_version()
    return user_version != current_version


def get_update_message() -> str:
    """Возвращает сообщение об обновлении."""
    return (
        "✨ <b>Бот обновлён!</b>\n\n"
        "🎉 Новые возможности:\n"
        "• 🚗 <b>Выбор вашего авто</b> — теперь бот знает вашу машину\n"
        "• 📌 <b>Типичные ошибки по модели</b> — видите популярные проблемы\n"
        "• 🎯 <b>Умная диагностика</b> — учитывает вашу марку\n\n"
        "Начните с кнопки <b>🚗 Моё авто</b> чтобы выбрать свой автомобиль!"
    )


def get_version_string() -> str:
    """Возвращает строку версии для логирования."""
    return f"v{get_current_version()}"
