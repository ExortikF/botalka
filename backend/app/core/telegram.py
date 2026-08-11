"""Проверка подписи данных от Telegram.

Без этой проверки любой может отправить нам произвольный tg_id и представиться кем
угодно — поэтому она обязательна и для виджета на сайте, и для Mini App.

Схемы подписи у них разные:
  - Login Widget: ключ = SHA256(bot_token)
  - Mini App initData: ключ = HMAC_SHA256(msg=bot_token, key="WebAppData")

Документация: https://core.telegram.org/widgets/login#checking-authorization
              https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class TelegramAuthError(Exception):
    pass


MAX_AUTH_AGE_SECONDS = 24 * 60 * 60


def _data_check_string(data: dict[str, str]) -> str:
    return "\n".join(f"{k}={data[k]}" for k in sorted(data) if k != "hash")


def _check_age(auth_date: str | None) -> None:
    if not auth_date:
        raise TelegramAuthError("нет auth_date")
    try:
        issued = int(auth_date)
    except ValueError as exc:
        raise TelegramAuthError("некорректный auth_date") from exc
    if time.time() - issued > MAX_AUTH_AGE_SECONDS:
        raise TelegramAuthError("данные авторизации устарели")


def verify_login_widget(data: dict[str, str], bot_token: str) -> dict:
    """Данные от виджета Telegram Login на сайте. Возвращает профиль пользователя."""
    received = data.get("hash")
    if not received:
        raise TelegramAuthError("нет hash")

    secret = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret, _data_check_string(data).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise TelegramAuthError("подпись не совпадает")

    _check_age(data.get("auth_date"))

    return {
        "tg_id": int(data["id"]),
        "username": data.get("username"),
        "first_name": data.get("first_name") or "",
        "last_name": data.get("last_name") or "",
        "photo_url": data.get("photo_url"),
    }


def verify_init_data(init_data: str, bot_token: str) -> dict:
    """Строка initData из Telegram Mini App. Возвращает профиль пользователя."""
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received = parsed.get("hash")
    if not received:
        raise TelegramAuthError("нет hash")

    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, _data_check_string(parsed).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise TelegramAuthError("подпись не совпадает")

    _check_age(parsed.get("auth_date"))

    try:
        user = json.loads(parsed["user"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise TelegramAuthError("нет данных пользователя") from exc

    return {
        "tg_id": int(user["id"]),
        "username": user.get("username"),
        "first_name": user.get("first_name") or "",
        "last_name": user.get("last_name") or "",
        "photo_url": user.get("photo_url"),
    }
