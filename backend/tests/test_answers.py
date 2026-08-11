"""Ответ пользователя не должен зависеть от того, как он набрал запятую."""

import pytest

from app.core.answers import check_answer
from app.models.content import AnswerType


@pytest.mark.parametrize(
    "raw",
    ["7", " 7 ", "7.0", "7,0", "+7", "07"],
)
def test_number_accepts_equivalent_forms(raw):
    assert check_answer(AnswerType.NUMBER, {"value": "7"}, raw)


@pytest.mark.parametrize("raw", ["8", "", "семь", "7x", "0.7", "--7"])
def test_number_rejects_wrong(raw):
    assert not check_answer(AnswerType.NUMBER, {"value": "7"}, raw)


@pytest.mark.parametrize("raw", ["-0.5", "-0,5", "−0,5", "–0.5"])
def test_number_accepts_unicode_minus(raw):
    """Умные клавиатуры и копипаста подсовывают не тот минус."""
    assert check_answer(AnswerType.NUMBER, {"value": "-0.5"}, raw)


def test_number_tolerance():
    payload = {"value": "3.14", "tolerance": "0.01"}
    assert check_answer(AnswerType.NUMBER_TOLERANCE, payload, "3.15")
    assert check_answer(AnswerType.NUMBER_TOLERANCE, payload, "3,13")
    assert not check_answer(AnswerType.NUMBER_TOLERANCE, payload, "3.2")


def test_number_tolerance_zero_is_exact():
    assert check_answer(AnswerType.NUMBER_TOLERANCE, {"value": "2"}, "2")
    assert not check_answer(AnswerType.NUMBER_TOLERANCE, {"value": "2"}, "2.1")


@pytest.mark.parametrize("raw", ["нейтральный", "Нейтральный", " НЕЙТРАЛЬНЫЙ ", "нейтральныи"])
def test_string_is_forgiving(raw):
    payload = {"value": "нейтральный"}
    expected = raw != "нейтральныи"  # «и» вместо «й» — всё-таки другое слово
    assert check_answer(AnswerType.STRING, payload, raw) is expected


def test_string_yo_and_synonyms():
    payload = {"value": "объём", "synonyms": ["обьем"]}
    assert check_answer(AnswerType.STRING, payload, "объем")
    assert check_answer(AnswerType.STRING, payload, "ОБЪЁМ")
    assert check_answer(AnswerType.STRING, payload, "обьем")
    assert not check_answer(AnswerType.STRING, payload, "масса")


def test_digits_order_matters():
    payload = {"value": "1324"}
    assert check_answer(AnswerType.DIGITS, payload, "1324")
    assert check_answer(AnswerType.DIGITS, payload, "1 3 2 4")
    assert check_answer(AnswerType.DIGITS, payload, "1,3,2,4")
    assert not check_answer(AnswerType.DIGITS, payload, "1234")


def test_multi_order_does_not_matter():
    payload = {"value": "2;5;7"}
    assert check_answer(AnswerType.MULTI, payload, "7 5 2")
    assert check_answer(AnswerType.MULTI, payload, "2,5,7")
    assert not check_answer(AnswerType.MULTI, payload, "2;5")


@pytest.mark.parametrize("answer_type", list(AnswerType))
def test_empty_answer_is_never_correct(answer_type):
    assert not check_answer(answer_type, {"value": "1"}, "")
    assert not check_answer(answer_type, {"value": "1"}, "   ")
