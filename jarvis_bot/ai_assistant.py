import logging

from gigachat import GigaChat

from .config import GIGACHAT_CREDENTIALS, GIGACHAT_VERIFY_SSL

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
