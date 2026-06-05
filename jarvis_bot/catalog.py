import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import DATA_DIR

OBD_PATTERN = re.compile(r"\bP\d{4}\b", re.IGNORECASE)


@dataclass
class PartItem:
    id: str
    type: str
    name: str
    description: str
    price: str
    link: str
    keywords: list[str]


@dataclass
class ServiceItem:
    name: str
    address: str
    work_time: str
    phone: str
    rating: str


def _load_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_parts() -> list[PartItem]:
    raw = _load_json(DATA_DIR / "parts.json")
    return [
        PartItem(
            id=item["id"],
            type=item["type"],
            name=item["name"],
            description=item["description"],
            price=item["price"],
            link=item["link"],
            keywords=[k.lower() for k in item.get("keywords", [])],
        )
        for item in raw
    ]


def load_services() -> list[ServiceItem]:
    raw = _load_json(DATA_DIR / "services.json")
    return [ServiceItem(**item) for item in raw]


def find_by_obd(code: str, parts: list[PartItem]) -> Optional[PartItem]:
    code = code.upper()
    for part in parts:
        if part.id.upper() == code:
            return part
    return None


def find_best_match(query: str, parts: list[PartItem]) -> Optional[PartItem]:
    text = query.lower().strip()
    if not text:
        return None

    for code in OBD_PATTERN.findall(text):
        hit = find_by_obd(code, parts)
        if hit:
            return hit

    for part in parts:
        if text == part.id.lower() or text in part.keywords:
            return part

    best: Optional[PartItem] = None
    best_score = 0
    for part in parts:
        score = 0
        for keyword in part.keywords:
            if keyword in text or text in keyword:
                score += len(keyword)
        if score > best_score:
            best_score = score
            best = part

    return best if best_score >= 4 else None


def obd_items(parts: list[PartItem]) -> list[PartItem]:
    return [p for p in parts if p.type == "obd"]
