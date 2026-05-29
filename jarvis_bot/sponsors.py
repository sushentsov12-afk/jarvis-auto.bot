"""
sponsors.py — система спонсорских мест для монетизации Jarvis Auto.

Уровни (по металлам, по убыванию):
  🥇 GOLD    — топ-спонсор, выделенная кнопка золотого цвета, первое место
  🥈 SILVER  — второй уровень, серебряная кнопка
  🥉 BRONZE  — третий уровень, бронзовая кнопка
  ⬜ BASIC   — обычный список без выделения

Структура позволяет легко добавлять спонсоров в любой город.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Sponsor:
    name: str           # Название компании
    phone: str          # Телефон
    address: str        # Адрес
    work_time: str      # Режим работы
    rating: str         # Рейтинг (строка, например "4.8")
    url: str            # Сайт или соц. сеть
    tier: str           # gold | silver | bronze | basic
    city_key: str       # Ключ города (например "yoshkar_ola")
    category: str       # sto | komissar


# ─────────────────────────────────────────────────────────────────
# ЙОШКАР-ОЛА — спонсорская база
# ─────────────────────────────────────────────────────────────────
SPONSORS: list[Sponsor] = [

    # ══════════════════════════════════
    # СТО — автосервисы
    # ══════════════════════════════════

    Sponsor(
        name="Гарант Авто",
        phone="+7 (8362) 47-07-07",
        address="Сернурский тракт, 23 (2 филиала)",
        work_time="08:00–20:00, ежедневно",
        rating="4.6",
        url="garantavto12.ru",
        tier="gold",          # 🥇 ЗОЛОТОЙ СПОНСОР
        city_key="yoshkar_ola",
        category="sto",
    ),

    Sponsor(
        name="Автоклиника",
        phone="+7 (962) 588-15-15",
        address="ул. Мира, 28а",
        work_time="08:30–18:00 пн-пт, сб 10:00–16:00",
        rating="4.8",
        url="autoclinica12.ru",
        tier="silver",        # 🥈 СЕРЕБРЯНЫЙ СПОНСОР
        city_key="yoshkar_ola",
        category="sto",
    ),

    Sponsor(
        name="Когис-Бит",
        phone="+7 (8362) 00-00-00",  # уточнить при подписании договора
        address="бульвар Победы, 19Б",
        work_time="09:00–18:00",
        rating="4.4",
        url="2gis.ru/yoshkarola",
        tier="bronze",        # 🥉 БРОНЗОВЫЙ СПОНСОР
        city_key="yoshkar_ola",
        category="sto",
    ),

    # ══════════════════════════════════
    # Аварийные комиссары
    # ══════════════════════════════════

    Sponsor(
        name="АвтоКомиссар12 — 201-201",
        phone="+7 (8362) 201-201",
        address="пгт Медведево, ул. Полевая, 5",
        work_time="Круглосуточно",
        rating="4.9",
        url="xn--12-6kcaj3copq.xn--p1ai",
        tier="gold",          # 🥇 ЗОЛОТОЙ СПОНСОР SOS
        city_key="yoshkar_ola",
        category="komissar",
    ),

    Sponsor(
        name="АВАРКОМ 709-709",
        phone="+7 (8362) 709-709",
        address="Йошкар-Ола",
        work_time="Круглосуточно",
        rating="4.7",
        url="xn--709-5cdal1dqrs.xn--p1ai",
        tier="silver",        # 🥈 СЕРЕБРЯНЫЙ
        city_key="yoshkar_ola",
        category="komissar",
    ),

    Sponsor(
        name="Центр помощи 908-908",
        phone="+7 (8362) 908-908",
        address="Йошкар-Ола",
        work_time="Круглосуточно",
        rating="4.5",
        url="dtp-prav12.ru",
        tier="bronze",        # 🥉 БРОНЗОВЫЙ
        city_key="yoshkar_ola",
        category="komissar",
    ),
]


# ─────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────

TIER_EMOJI = {
    "gold":   "🥇",
    "silver": "🥈",
    "bronze": "🥉",
    "basic":  "📍",
}

TIER_LABEL = {
    "gold":   "ЗОЛОТОЙ ПАРТНЁР",
    "silver": "СЕРЕБРЯНЫЙ ПАРТНЁР",
    "bronze": "БРОНЗОВЫЙ ПАРТНЁР",
    "basic":  "",
}

# Порядок отображения уровней
TIER_ORDER = {"gold": 0, "silver": 1, "bronze": 2, "basic": 3}


def get_sponsors(city_key: str, category: str) -> list[Sponsor]:
    """Возвращает спонсоров города по категории, отсортированных по уровню."""
    result = [
        s for s in SPONSORS
        if s.city_key == city_key and s.category == category
    ]
    return sorted(result, key=lambda s: TIER_ORDER.get(s.tier, 9))


def format_sto_sponsors(city_key: str) -> str:
    """Форматирует список СТО со спонсорскими выделениями."""
    sponsors = get_sponsors(city_key, "sto")
    if not sponsors:
        return ""

    lines = []
    for s in sponsors:
        emoji = TIER_EMOJI[s.tier]
        label = TIER_LABEL[s.tier]

        if s.tier == "gold":
            lines.append(
                f"{emoji} <b>{s.name}</b>  ╠══ {label} ══╣\n"
                f"   ★ {s.rating}  |  {s.work_time}\n"
                f"   📍 {s.address}\n"
                f"   📞 <code>{s.phone}</code>\n"
                f"   🌐 {s.url}"
            )
        elif s.tier == "silver":
            lines.append(
                f"{emoji} <b>{s.name}</b>  — {label}\n"
                f"   ★ {s.rating}  |  {s.work_time}\n"
                f"   📍 {s.address}\n"
                f"   📞 <code>{s.phone}</code>"
            )
        elif s.tier == "bronze":
            lines.append(
                f"{emoji} <b>{s.name}</b>  — {label}\n"
                f"   ★ {s.rating}  |  📍 {s.address}\n"
                f"   📞 <code>{s.phone}</code>"
            )
        else:
            lines.append(
                f"{emoji} {s.name}  ★ {s.rating}\n"
                f"   📞 <code>{s.phone}</code>"
            )

    return "\n\n".join(lines)


def format_komissar_sponsors(city_key: str) -> str:
    """Форматирует список комиссаров со спонсорскими выделениями."""
    sponsors = get_sponsors(city_key, "komissar")
    if not sponsors:
        return ""

    lines = []
    for s in sponsors:
        emoji = TIER_EMOJI[s.tier]
        label = TIER_LABEL[s.tier]

        if s.tier == "gold":
            lines.append(
                f"{emoji} <b>{s.name}</b>  ╠══ {label} ══╣\n"
                f"   ⏰ {s.work_time}  |  ★ {s.rating}\n"
                f"   📞 <code>{s.phone}</code>\n"
                f"   🌐 {s.url}"
            )
        elif s.tier == "silver":
            lines.append(
                f"{emoji} <b>{s.name}</b>  — {label}\n"
                f"   ⏰ {s.work_time}  |  ★ {s.rating}\n"
                f"   📞 <code>{s.phone}</code>"
            )
        else:
            lines.append(
                f"{emoji} <b>{s.name}</b>  — {label}\n"
                f"   📞 <code>{s.phone}</code>"
            )

    return "\n\n".join(lines)


def get_gold_komissar(city_key: str) -> Sponsor | None:
    """Возвращает золотого спонсора-комиссара для выделенной кнопки SOS."""
    for s in SPONSORS:
        if s.city_key == city_key and s.category == "komissar" and s.tier == "gold":
            return s
    return None


def get_gold_sto(city_key: str) -> Sponsor | None:
    """Возвращает золотого спонсора-СТО."""
    for s in SPONSORS:
        if s.city_key == city_key and s.category == "sto" and s.tier == "gold":
            return s
    return None
