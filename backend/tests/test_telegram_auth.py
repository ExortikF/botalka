"""Проверка подписи Telegram — единственное, что стоит между нами и подделкой личности.

Если эти тесты падают, вход открыт для кого угодно.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.telegram import (
    TelegramAuthError,
    verify_init_data,
    verify_login_widget,
)

TOKEN = "123456:AAtest-token"


def sign_widget(data: dict[str, str], token: str = TOKEN) -> dict[str, str]:
    dcs = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hashlib.sha256(token.encode()).digest()
    return {**data, "hash": hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()}


def sign_init_data(params: dict[str, str], token: str = TOKEN) -> str:
    dcs = "\n".join(f"{k}={params[k]}" for k in sorted(params))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    signed = {**params, "hash": hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()}
    return urlencode(signed)


def widget_payload(**overrides) -> dict[str, str]:
    return {
        "id": "777001",
        "first_name": "Тест",
        "last_name": "Боталкин",
        "username": "tester",
        "auth_date": str(int(time.time())),
        **overrides,
    }


def test_valid_widget_signature():
    profile = verify_login_widget(sign_widget(widget_payload()), TOKEN)
    assert profile["tg_id"] == 777001
    assert profile["username"] == "tester"


def test_tampered_field_rejected():
    data = sign_widget(widget_payload())
    data["id"] = "999999"  # подменяем личность, подпись оставляем прежнюю
    with pytest.raises(TelegramAuthError):
        verify_login_widget(data, TOKEN)


def test_wrong_token_rejected():
    with pytest.raises(TelegramAuthError):
        verify_login_widget(sign_widget(widget_payload()), "999:другой-токен")


def test_missing_hash_rejected():
    with pytest.raises(TelegramAuthError):
        verify_login_widget(widget_payload(), TOKEN)


def test_stale_auth_date_rejected():
    old = str(int(time.time()) - 48 * 3600)
    with pytest.raises(TelegramAuthError):
        verify_login_widget(sign_widget(widget_payload(auth_date=old)), TOKEN)


def test_valid_init_data():
    params = {
        "user": json.dumps({"id": 777002, "first_name": "Мини", "username": "mini"}),
        "auth_date": str(int(time.time())),
        "query_id": "AAA",
    }
    profile = verify_init_data(sign_init_data(params), TOKEN)
    assert profile["tg_id"] == 777002
    assert profile["username"] == "mini"


def test_init_data_signed_with_widget_scheme_rejected():
    """Схемы подписи у виджета и Mini App разные — путать их нельзя."""
    params = {
        "user": json.dumps({"id": 777003, "first_name": "Х"}),
        "auth_date": str(int(time.time())),
    }
    dcs = "\n".join(f"{k}={params[k]}" for k in sorted(params))
    wrong = hmac.new(
        hashlib.sha256(TOKEN.encode()).digest(), dcs.encode(), hashlib.sha256
    ).hexdigest()
    with pytest.raises(TelegramAuthError):
        verify_init_data(urlencode({**params, "hash": wrong}), TOKEN)
