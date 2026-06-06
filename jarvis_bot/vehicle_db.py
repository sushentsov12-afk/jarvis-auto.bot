"""
vehicle_db.py — база данных авто и типичных ошибок.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


@dataclass
class CommonIssue:
    name: str
    urgency: str
    description: str
    price_range: str


def _load_issues() -> dict:
    path = os.path.join(DATA_DIR, "vehicle_issues.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_ISSUES_DB = _load_issues()


def get_vehicle_key(brand: str, model: str) -> str:
    return f"{brand.lower()}_{model.lower()}".replace(" ", "_").replace("-", "_")


def get_typical_issues(brand: str, model: str) -> list[CommonIssue]:
    key = get_vehicle_key(brand, model)
    issues = _ISSUES_DB.get(key, [])
    return [CommonIssue(**i) for i in issues]
