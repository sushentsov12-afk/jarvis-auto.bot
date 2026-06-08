"""
photo_diagnosis.py — диагностика авто по фотографии через GigaChat Vision.
"""
from __future__ import annotations
import base64
import json
import logging
import re
import os
from typing import Optional

logger = logging.getLogger(__name__)

PHOTO_PROMPT = """Ты опытный автомеханик с 20-летним стажем. Смотришь на фотографию автомобиля или его детали.

Определи что изображено и какая это неисправность или состояние.
Верни ТОЛЬКО валидный JSON без пояснений, без markdown, без ```json:

{
  "found": true,
  "what_i_see": "Что именно видно на фото (1-2 предложения)",
  "symptom": "Название симптома/проблемы кратко",
  "technical_name": "Техническое название неисправности",
  "urgency": "low/medium/high/critical",
  "description": "Описание проблемы 1-2 предложения",
  "probable_cause": "Вероятные причины",
  "action_required": "Что нужно сделать",
  "price_range": "от X до Y руб",
  "warning": "Предупреждение или пустая строка"
}

Если на фото нет явной проблемы или это не автомобильная тема — верни {"found": false, "what_i_see": "описание"}
"""


def analyze_photo(image_bytes: bytes) -> Optional[dict]:
    """
    Анализирует фото через GigaChat Vision.
    Возвращает dict с результатом или None при ошибке.
    """
    from config import GIGACHAT_CREDENTIALS, GIGACHAT_VERIFY_SSL
    if not GIGACHAT_CREDENTIALS:
        logger.warning("GigaChat credentials не настроены")
        return None

    try:
        from gigachat import GigaChat
        from gigachat.models import Chat, Messages, MessagesRole, Image

        # Кодируем фото в base64
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        with GigaChat(
            credentials=GIGACHAT_CREDENTIALS,
            verify_ssl_certs=GIGACHAT_VERIFY_SSL,
            model="GigaChat-Pro",  # Pro поддерживает изображения
        ) as client:
            response = client.chat(
                Chat(
                    messages=[
                        Messages(
                            role=MessagesRole.USER,
                            content=PHOTO_PROMPT,
                            attachments=[Image(content=b64)],
                        )
                    ]
                )
            )

        raw = response.choices[0].message.content.strip()
        logger.info("GigaChat Vision ответ: %s", raw[:200])

        # Извлекаем JSON
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            logger.warning("JSON не найден в ответе Vision")
            return None

        data = json.loads(match.group())
        return data

    except Exception:
        logger.exception("Ошибка GigaChat Vision")
        return None


def save_photo_result(data: dict) -> bool:
    """Сохраняет результат анализа фото в diagnostic_base.json."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "data", "diagnostic_base.json")
        db = json.load(open(db_path, encoding="utf-8"))

        # Проверяем дубликат
        existing = [x["technical_name"].lower() for x in db]
        if data.get("technical_name", "").lower() in existing:
            return False

        new_entry = {
            "id": max(x["id"] for x in db) + 1,
            "user_queries": [data.get("symptom", ""), data.get("technical_name", "")],
            "obd_code": "нет",
            "oem_code": "",
            "technical_name": data.get("technical_name", "Неизвестная проблема"),
            "ru_description": data.get("description", ""),
            "probable_cause": data.get("probable_cause", ""),
            "action_required": data.get("action_required", ""),
            "urgency": data.get("urgency", "medium"),
            "price_range": data.get("price_range", "уточняйте на СТО"),
            "lesson": "Запись создана по фото пользователя",
            "diy": False,
            "warning": data.get("warning", ""),
        }

        db.append(new_entry)
        json.dump(db, open(db_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        logger.info("Сохранена запись из фото: %s", data.get("technical_name"))
        return True

    except Exception:
        logger.exception("Ошибка сохранения результата фото")
        return False


def format_photo_result(data: dict) -> str:
    """Форматирует результат анализа фото для отправки пользователю."""
    urgency_icon = {
        "critical": "🚨",
        "high": "⚠️",
        "medium": "🔧",
        "low": "ℹ️",
    }.get(data.get("urgency", "medium"), "🔧")

    lines = [
        f"📸 <b>Анализ фото</b>",
        f"",
        f"👁 <i>{data.get('what_i_see', '')}</i>",
        f"",
        f"{urgency_icon} <b>{data.get('technical_name', 'Проблема определена')}</b>",
        f"",
        f"📋 {data.get('description', '')}",
        f"",
        f"🔍 <b>Причина:</b> {data.get('probable_cause', '')}",
        f"🛠 <b>Что делать:</b> {data.get('action_required', '')}",
        f"💰 <b>Стоимость:</b> {data.get('price_range', 'уточняйте на СТО')}",
    ]

    if data.get("warning"):
        lines.append(f"⚡ <b>Важно:</b> {data['warning']}")

    return "\n".join(lines)
