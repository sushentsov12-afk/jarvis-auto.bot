"""
dialog_state.py — хранилище состояний диалогов пользователей.
"""
from __future__ import annotations
from dialog_engine import DialogState

# user_id → активный DialogState
_STATES: dict[int, DialogState] = {}


def set_state(user_id: int, state: DialogState) -> None:
    _STATES[user_id] = state


def get_state(user_id: int) -> DialogState | None:
    return _STATES.get(user_id)


def clear_state(user_id: int) -> None:
    _STATES.pop(user_id, None)


def has_state(user_id: int) -> bool:
    return user_id in _STATES
