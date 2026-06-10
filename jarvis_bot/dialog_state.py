"""
dialog_state.py — хранилище состояний диалогов пользователей.
"""
from __future__ import annotations

_STATES: dict = {}


def set_state(user_id: int, state) -> None:
    _STATES[user_id] = state


def get_state(user_id: int):
    return _STATES.get(user_id)


def clear_state(user_id: int) -> None:
    _STATES.pop(user_id, None)


def has_state(user_id: int) -> bool:
    return user_id in _STATES
