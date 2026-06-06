import logging
import urllib.request

import requests
from requests.exceptions import RequestException

from config import BOT_TOKEN, TELEGRAM_PROXY

logger = logging.getLogger(__name__)

CONNECT_HELP = """
Не удалось подключиться к Telegram (api.telegram.org).

Что сделать:
1. Включите VPN на компьютере и запустите бота снова.
2. Или укажите в .env HTTP/SOCKS-прокси (не ссылку tg://proxy):
   TELEGRAM_PROXY=http://127.0.0.1:7890
   (порт 7890 — типичный для Clash; у V2Ray часто 10809)

Ссылка tg://proxy?server=... — только для приложения Telegram,
Python-бот через неё не подключается.
"""


def resolve_proxy() -> dict[str, str] | None:
    if TELEGRAM_PROXY:
        return {"https": TELEGRAM_PROXY, "http": TELEGRAM_PROXY}

    system = urllib.request.getproxies()
    if system.get("https") or system.get("http"):
        https = system.get("https") or system.get("http")
        http = system.get("http") or https
        logger.info("Using system proxy: %s", https)
        return {"https": https, "http": http}

    return None


def check_telegram(token: str, proxies: dict[str, str] | None) -> bool:
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = requests.get(url, timeout=20, proxies=proxies)
        data = response.json()
    except RequestException as exc:
        logger.error("Telegram API unreachable: %s", exc)
        print(CONNECT_HELP)
        return False

    if not data.get("ok"):
        logger.error("Telegram API error: %s", data)
        print("Токен бота неверный или отозван. Создайте новый в @BotFather.")
        return False

    user = data["result"]
    logger.info("Telegram OK: @%s (%s)", user.get("username"), user.get("first_name"))
    return True
