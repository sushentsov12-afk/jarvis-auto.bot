"""
dialog_state.py — хранилище состояний диалогов пользователей.
"""
from __future__ import annotations

_STATES: dict = {}
_LAST_DIAGNOSTICS: dict = {}


def set_state(user_id: int, state) -> None:
    _STATES[user_id] = state


def get_state(user_id: int):
    return _STATES.get(user_id)


def clear_state(user_id: int) -> None:
    _STATES.pop(user_id, None)


def has_state(user_id: int) -> bool:
    return user_id in _STATES


def set_last_diagnostic(user_id: int, data: dict) -> None:
    """Запоминает последний показанный диагноз — для кнопки '🔄 Объясни проще'."""
    _LAST_DIAGNOSTICS[user_id] = data


def get_last_diagnostic(user_id: int) -> dict | None:
    return _LAST_DIAGNOSTICS.get(user_id)
