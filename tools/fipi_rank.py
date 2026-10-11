"""Оценка сложности задач банка.

    tools/.venv/bin/python tools/fipi_rank.py --dry
    tools/.venv/bin/python tools/fipi_rank.py

Проставляет `difficulty` (1–5) в готовых задачах `content/<предмет>/<номер>/*.yaml`.
Бэкенд раскладывает это по полосам: 1–2 «лёгкие», 3 «средние», 4–5 «сложные»
(DIFFICULTY_BANDS в app/api/quiz.py). Пока у всех стояла тройка, конструктор
квиза с выбором сложности был бесполезен: все задачи попадали в одну полосу.

Оценка складывается из двух частей:

  * **база по номеру задания** — насколько номер тяжело даётся в среднем.
    Это грубая, но честная опора: №7 «вычисления» и №6 «уравнения» решаются
    почти всеми, а №9, №10 и №12 стабильно проседают;
  * **поправки по самой задаче** — длинное условие, техника (логарифмы,
    тригонометрия, корни), нецелый ответ.

Это оценка, а не измерение. В `docs/CONTENT.md` записано, что сложность
уточняется по реальной статистике решений, — как накопятся попытки, число
надо пересчитать по доле верных ответов, а не по этим правилам.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Опорная сложность номера задания части 1.
BASE = {
    1: 2,   # планиметрия по готовому чертежу
    2: 2,   # векторы: механический счёт по координатам
    3: 3,   # стереометрия: нужно увидеть тело
    4: 2,   # классическое определение вероятности
    5: 3,   # составные события
    6: 2,   # простейшие уравнения
    7: 2,   # вычисления и преобразования
    8: 3,   # смысл производной по графику
    9: 4,   # прикладная: разобраться в чужой формуле
    10: 4,  # текстовая: составить модель самому
    11: 3,  # восстановление функции по графику
    12: 3,  # исследование функции
}

TECHNIQUE = (
    (r"\\log|\\ln|\\lg", "логарифм"),
    (r"\\sin|\\cos|\\tg|\\ctg", "тригонометрия"),
    (r"\\sqrt\s*\[", "корень степени выше второй"),
    (r"\\frac[^$]*\\frac", "дробь в дроби"),
)

LONG_STATEMENT = 220

# Номера, которые вообще осмысленно опускать ниже базы: это темы на технику,
# и короткая задача там действительно тривиальна. Исследование функции (№12)
# или стереометрия (№3) простыми не становятся от короткого условия.
LOWERABLE = {1, 2, 4, 6, 7}


def statement_of(text: str) -> str:
    match = re.search(r"^statement: \|\n((?:  .*\n)+)", text, re.M)
    return match.group(1) if match else ""


def answer_of(text: str) -> str:
    match = re.search(r'^  value: "(.*)"$', text, re.M)
    return match.group(1) if match else ""


def rank(text: str, number: int) -> tuple[int, list[str]]:
    """Сложность и список причин — причины нужны, чтобы оценку можно было оспорить."""
    score = BASE.get(number, 3)
    why = [f"№{number} — база {score}"]

    statement = statement_of(text)
    answer = answer_of(text)

    if len(statement) > LONG_STATEMENT:
        score += 1
        why.append("длинное условие")

    techniques = [name for pattern, name in TECHNIQUE if re.search(pattern, statement)]
    if len(techniques) >= 2:
        score += 1
        why.append("несколько техник: " + ", ".join(techniques))

    # Дробный ответ означает лишний шаг в счёте. Минус — не означает ничего:
    # «-4» ничуть не сложнее «4».
    if "," in answer:
        score += 1
        why.append("дробный ответ")

    if number in LOWERABLE and len(statement) < 90 and answer.lstrip("-").isdigit():
        score -= 1
        why.append("короткое условие, целый ответ")

    score = max(1, min(5, score))
    return score, why


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="math_prof")
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()

    spread: Counter[int] = Counter()
    bands: Counter[str] = Counter()
    changed = 0

    for folder in sorted((ROOT / "content" / args.subject).glob("[0-9][0-9]")):
        number = int(folder.name)
        for path in sorted(folder.glob("*.yaml")):
            text = path.read_text(encoding="utf-8")
            score, why = rank(text, number)
            spread[score] += 1
            bands["лёгкие" if score <= 2 else "средние" if score == 3 else "сложные"] += 1

            updated = re.sub(r"^difficulty: .*$", f"difficulty: {score}", text, count=1, flags=re.M)
            if updated != text and not args.dry:
                path.write_text(updated, encoding="utf-8")
                changed += 1

    print("сложность по шкале 1–5:")
    for score in sorted(spread):
        print(f"  {score}: {spread[score]:4} задач")
    print("\nполосы, как их видит конструктор квиза:")
    for band in ("лёгкие", "средние", "сложные"):
        print(f"  {band}: {bands[band]}")
    if not args.dry:
        print(f"\nобновлено файлов: {changed}")


if __name__ == "__main__":
    main()
