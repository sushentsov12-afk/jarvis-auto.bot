"""
vehicle_db.py — база данных популярных моделей авто и их типичных ошибок.

Содержит:
- Каталог поддерживаемых марок и моделей
- Типичные поломки по каждому авто
- Вероятность и срочность
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from config import DATA_DIR


@dataclass
class VehicleModel:
    brand: str
    model: str
    years: tuple[int, int]  # (from_year, to_year)
    
    def __str__(self) -> str:
        return f"{self.brand} {self.model} ({self.years[0]}-{self.years[1]})"
    
    def key(self) -> str:
        """Ключ для поиска в базе"""
        return f"{self.brand.lower()}_{self.model.lower()}".replace(" ", "_")


@dataclass
class CommonIssue:
    name: str
    urgency: str  # critical, high, medium, low
    probability: str  # high, medium, low
    description: str
    price_range: str


def _load_vehicles() -> dict:
    """Загружает список моделей авто из JSON."""
    path = DATA_DIR / "vehicles.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_vehicle_issues() -> dict:
    """Загружает типичные ошибки по каждому авто."""
    path = DATA_DIR / "vehicle_issues.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


VEHICLES_DB = _load_vehicles()
VEHICLE_ISSUES_DB = _load_vehicle_issues()


def get_all_brands() -> list[str]:
    """Возвращает отсортированный список всех марок авто."""
    brands = set()
    for vehicle_list in VEHICLES_DB.values():
        for v in vehicle_list:
            brands.add(v.get("brand", "").strip())
    return sorted(list(brands))


def get_models_by_brand(brand: str) -> list[dict]:
    """Возвращает список моделей для марки."""
    brand_lower = brand.lower().strip()
    models = []
    for vehicles in VEHICLES_DB.values():
        for v in vehicles:
            if v.get("brand", "").lower() == brand_lower:
                models.append(v)
    
    # Убираем дубликаты и сортируем по названию
    seen = set()
    unique = []
    for m in models:
        key = m.get("model", "").lower()
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return sorted(unique, key=lambda x: x.get("model", ""))


def get_common_issues(brand: str, model: str, year: int) -> list[CommonIssue]:
    """
    Возвращает типичные поломки для конкретного авто.
    """
    key = f"{brand.lower()}_{model.lower()}".replace(" ", "_")
    if key not in VEHICLE_ISSUES_DB:
        return []
    
    issues_data = VEHICLE_ISSUES_DB[key]
    issues = []
    
    for issue in issues_data.get("common_issues", []):
        # Проверяем, актуальна ли ошибка для этого года
        years_range = issue.get("years", [1990, 2030])
        if years_range[0] <= year <= years_range[1]:
            issues.append(CommonIssue(
                name=issue.get("name", ""),
                urgency=issue.get("urgency", "medium"),
                probability=issue.get("probability", "medium"),
                description=issue.get("description", ""),
                price_range=issue.get("price_range", "")
            ))
    
    return sorted(issues, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.urgency, 3))


def find_vehicle(brand: str, model: str) -> Optional[dict]:
    """Ищет авто в базе."""
    brand_lower = brand.lower().strip()
    model_lower = model.lower().strip()
    
    for vehicles in VEHICLES_DB.values():
        for v in vehicles:
            if (v.get("brand", "").lower() == brand_lower and 
                v.get("model", "").lower() == model_lower):
                return v
    return None


def format_vehicle_issues(brand: str, model: str, year: int) -> str:
    """Форматирует список типичных ошибок для вывода."""
    issues = get_common_issues(brand, model, year)
    
    if not issues:
        return f"<i>У {brand} {model} ({year}) нет известных типичных ошибок в базе.</i>"
    
    lines = [f"<b>📌 Типичные проблемы {brand} {model} ({year}):</b>\n"]
    
    for issue in issues[:5]:  # Показываем топ-5
        emoji_urgency = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "🔧",
            "low": "ℹ️"
        }.get(issue.urgency, "🔧")
        
        lines.append(f"{emoji_urgency} <b>{issue.name}</b>")
        lines.append(f"   {issue.description}")
        lines.append(f"   💰 {issue.price_range}\n")
    
    return "\n".join(lines)
