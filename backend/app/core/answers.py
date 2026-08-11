"""Проверка ответов.

Самая частая причина потери доверия — засчитать верный ответ как неверный из-за
запятой вместо точки или лишнего пробела. Поэтому нормализация здесь агрессивная,
а тесты на неё — обязательные.

Формат `answer_payload` по типам:
    number            {"value": "7"}                     точное значение
    number_tolerance  {"value": "3.14", "tolerance": "0.01"}
    string            {"value": "нейтральный", "synonyms": ["нейтрально"]}
    digits            {"value": "1324"}                  порядок важен
    multi             {"value": "2;5;7"}                 порядок не важен
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.models.content import AnswerType

# нормализуем «минусы», которые прилетают из умных клавиатур и копипасты
MINUS_VARIANTS = {"−": "-", "–": "-", "—": "-"}


def normalize_raw(raw: str) -> str:
    text = (raw or "").strip()
    for bad, good in MINUS_VARIANTS.items():
        text = text.replace(bad, good)
    text = text.replace(" ", " ")
    return text


def _to_decimal(raw: str) -> Decimal | None:
    text = normalize_raw(raw).replace(",", ".").replace(" ", "")
    if not text:
        return None
    # «+7» и «7.» — валидные вводы, Decimal их принимает; мусор отсекаем ниже
    if not re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)", text):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _normalize_string(raw: str) -> str:
    text = normalize_raw(raw).lower().replace("ё", "е")
    return re.sub(r"[\s\-]+", "", text)


def _normalize_digits(raw: str) -> str:
    return re.sub(r"\D", "", normalize_raw(raw))


def _multi_items(raw: str) -> list[str]:
    parts = re.split(r"[;,\s]+", normalize_raw(raw))
    return sorted(p.replace(",", ".") for p in parts if p)


def check_answer(answer_type: AnswerType | str, payload: dict, raw: str) -> bool:
    """Верен ли ответ `raw`. Никогда не бросает — некорректный ввод это просто «неверно»."""
    answer_type = AnswerType(answer_type)
    expected = str(payload.get("value", ""))

    if not normalize_raw(raw):
        return False

    if answer_type is AnswerType.NUMBER:
        got, want = _to_decimal(raw), _to_decimal(expected)
        return got is not None and want is not None and got == want

    if answer_type is AnswerType.NUMBER_TOLERANCE:
        got, want = _to_decimal(raw), _to_decimal(expected)
        tol = _to_decimal(str(payload.get("tolerance", "0"))) or Decimal(0)
        return got is not None and want is not None and abs(got - want) <= tol

    if answer_type is AnswerType.STRING:
        variants = [expected, *payload.get("synonyms", [])]
        return _normalize_string(raw) in {_normalize_string(v) for v in variants}

    if answer_type is AnswerType.DIGITS:
        got = _normalize_digits(raw)
        return bool(got) and got == _normalize_digits(expected)

    if answer_type is AnswerType.MULTI:
        got, want = _multi_items(raw), _multi_items(expected)
        return bool(got) and got == want

    return False
