import logging

from gigachat import GigaChat

from config import GIGACHAT_CREDENTIALS, GIGACHAT_VERIFY_SSL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты Jarvis Auto — опытный автомеханик-консультант. "
    "Отвечай кратко по-русски (до 1200 символов). "
    "Дай вероятную причину, что проверить самому и когда ехать на СТО. "
    "Не выдумывай точные цены и артикулы. "
    "В конце предложи уточнить код OBD или симптом для подбора запчасти."
)


def is_enabled() -> bool:
    return bool(GIGACHAT_CREDENTIALS)


def ask(user_message: str) -> str:
    if not is_enabled():
        raise RuntimeError("GigaChat credentials are not configured")

    with GigaChat(
        credentials=GIGACHAT_CREDENTIALS,
        verify_ssl_certs=GIGACHAT_VERIFY_SSL,
    ) as client:
        response = client.chat(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ]
            }
        )

    return response.choices[0].message.content.strip()


ANALYZE_PROMPT = """Ты автомеханик-диагност. Пользователь описал проблему с машиной.
Твоя задача — вернуть ТОЛЬКО валидный JSON без пояснений, markdown и кода.

Формат ответа:
{
  "technical_name": "Краткое техническое название проблемы",
  "ru_description": "Описание проблемы 1-2 предложения",
  "probable_cause": "Вероятные причины через запятую",
  "action_required": "Что нужно сделать конкретно",
  "urgency": "low/medium/high/critical",
  "price_range": "от X до Y руб",
  "lesson": "Полезный совет для водителя",
  "warning": "Предупреждение если важно или пустая строка",
  "user_queries": ["запрос пользователя", "синоним1", "синоним2", "синоним3"]
}

Запрос пользователя: """


def analyze_and_save(user_query: str) -> bool:
    """
    Анализирует нераспознанный запрос через GigaChat
    и сохраняет результат в diagnostic_base.json.
    Возвращает True если успешно.
    """
    if not is_enabled():
        return False

    import json, os, re

    try:
        with GigaChat(
            credentials=GIGACHAT_CREDENTIALS,
            verify_ssl_certs=GIGACHAT_VERIFY_SSL,
        ) as client:
            response = client.chat({
                "messages": [
                    {"role": "user", "content": ANALYZE_PROMPT + user_query}
                ]
            })

        raw = response.choices[0].message.content.strip()

        # Вырезаем JSON если обёрнут в ```
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            logger.warning("GigaChat: JSON не найден в ответе")
            return False

        data = json.loads(match.group())

        # Валидация обязательных полей
        required = ["technical_name", "ru_description", "probable_cause",
                    "action_required", "urgency", "user_queries"]
        if not all(k in data for k in required):
            logger.warning("GigaChat: неполный JSON")
            return False

        # Загружаем базу
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "data", "diagnostic_base.json")
        db = json.load(open(db_path, encoding="utf-8"))

        # Проверяем дубликат
        existing = [x["technical_name"].lower() for x in db]
        if data["technical_name"].lower() in existing:
            logger.info("GigaChat: запись уже есть — %s", data["technical_name"])
            return False

        # Добавляем новую запись
        new_entry = {
            "id": max(x["id"] for x in db) + 1,
            "user_queries": data.get("user_queries", [user_query]),
            "obd_code": data.get("obd_code", "нет"),
            "oem_code": "",
            "technical_name": data["technical_name"],
            "ru_description": data["ru_description"],
            "probable_cause": data["probable_cause"],
            "action_required": data["action_required"],
            "urgency": data.get("urgency", "medium"),
            "price_range": data.get("price_range", "уточняйте на СТО"),
            "lesson": data.get("lesson", ""),
            "diy": data.get("diy", False),
            "warning": data.get("warning", ""),
        }

        db.append(new_entry)
        json.dump(db, open(db_path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

        logger.info("GigaChat: добавлена запись '%s'", data["technical_name"])
        return True

    except Exception:
        logger.exception("GigaChat analyze_and_save failed")
        return False
