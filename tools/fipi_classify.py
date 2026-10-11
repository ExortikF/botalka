"""Раскладка задач ФИПИ по номерам заданий КИМ.

    python3 tools/fipi_classify.py            # разметить и записать в черновики
    python3 tools/fipi_classify.py --dry      # только показать раскладку

Открытый банк не говорит, какому заданию КИМ соответствует задача: он размечен
кодами КЭС (кодификатор элементов содержания). Один код может отвечать разным
номерам: «6.2 Вероятность» — это и №4, и №5, а «4.2 Применение производной» —
и №8, и №12. Поэтому сначала по КЭС берём кандидатов, а выбираем между ними
по тексту условия.

Чего здесь намеренно нет — угадывания. Если правила не сошлись на одном номере,
задача остаётся с `task_type: null` и уходит в ручную разметку. Неверный номер
хуже отсутствующего: ученик получит в наборе «производная» задачу про вероятность
и решит, что тренажёр сломан.

Номера сверены с `content/task_types.yaml`.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Код КЭС → номера заданий, которым он может отвечать (часть 1, №1–12).
KES = {
    "7.1": [1],           # фигуры на плоскости
    "7.2": [1],
    "7.3": [3],           # многогранники
    "7.4": [3],           # тела вращения
    "7.5": [2],           # координаты и векторы
    "6.1": [4, 5],        # статистика и вероятность
    "6.2": [4, 5],
    "6.3": [5],
    "2.1": [6],           # уравнения
    "2.2": [6],
    "2.3": [6],
    "2.4": [6],
    "1.1": [7],           # вычисления и преобразования
    "1.2": [7],
    "1.3": [7],
    "1.4": [7],
    "1.5": [7],
    "1.6": [7],
    "1.7": [7],
    "1.8": [7],
    "3.1": [11],          # функции и графики
    "3.2": [11],
    "3.3": [11],
    "4.1": [8, 12],       # производная
    "4.2": [8, 12],
    "4.3": [12],
    "5.1": [9, 10],       # прикладные и текстовые
}

# Текстовые признаки: (регулярка, номер). Применяются только к кандидатам от КЭС,
# кроме случая, когда кандидатов нет вовсе.
RULES: list[tuple[str, int]] = [
    # производная: смысл и касательная — №8, исследование функции — №12
    (r"касательн|производн", 8),
    (r"наибольшее значение|наименьшее значение|точку максимума|точку минимума", 12),
    # вероятность: классическое определение — №4, составные события — №5
    # «каждый из» сюда не годится: так начинаются и задачи про жеребьёвку,
    # а это классическое определение вероятности, то есть №4.
    (r"хотя бы|независим|оба |обе |первый и второй|подряд|"
     r"два раза|дважды|вероятност\w+ .*вероятност", 5),
    # прикладная задача всегда идёт с готовой формулой
    (r"по формуле|определяется формулой|задаётся формулой|выражается формулой", 9),
    # текстовая задача — сюжет про движение, работу, проценты, сплавы
    (r"из пункта|навстречу|вниз по течению|против течения|лодка|катер|"
     r"велосипедист|мотоциклист|автомобил|поезд|пешеход|рабоч|бригад|"
     r"труб[аы] |бассейн|сплав|раствор|кислот|вклад|кредит|подешевел|"
     r"подорожал|производительн|успевает|догон", 10),
    # №11 — это восстановление параметров функции по графику: в условии всегда
    # есть общий вид формулы. Просто «на рисунке график» под это не подходит:
    # так же начинаются задачи про производную (№8).
    (r"график функции вида|функции вида \$|найдите \$?[abck]\$?[\.,]|"
     r"где [abck] ?, ?[abck]", 11),
]


def guess(task: dict) -> tuple[int | None, str]:
    """Возвращает номер задания и причину — почему именно он."""
    if task.get("answer_kind") and "краткий" not in task["answer_kind"].lower():
        return None, f"не краткий ответ ({task['answer_kind']})"

    codes = [k.split()[0] for k in task.get("kes", [])]
    candidates: list[int] = []
    for code in codes:
        candidates.extend(KES.get(code, []))
    candidates = sorted(set(candidates))

    text = task["statement"].lower()
    hits = [number for pattern, number in RULES if re.search(pattern, text)]

    # №9 и №10 определяются формой задачи, а не темой: прикладная — это готовая
    # формула, текстовая — сюжет про движение, работу или проценты. По КЭС они
    # неотличимы от обычных уравнений, поэтому здесь текст главнее кодификатора.
    for number in (9, 10):
        if number in hits:
            return number, f"сюжет задания №{number}"

    if len(candidates) == 1 and not hits:
        return candidates[0], f"КЭС {', '.join(codes)}"

    if candidates:
        agreed = [n for n in hits if n in candidates]
        if len(set(agreed)) == 1:
            return agreed[0], f"КЭС {', '.join(codes)} + текст"
        if len(candidates) == 1:
            return candidates[0], f"КЭС {', '.join(codes)} (текст промолчал)"

        # Вероятность: №5 отличается от №4 наличием составного события, и в
        # условии это всегда сказано словами. Раз маркеров нет — это №4.
        if candidates == [4, 5] and not agreed:
            return 4, "КЭС 6.x, признаков составного события нет"

        return None, f"КЭС даёт {candidates}, текст {sorted(set(hits)) or 'молчит'}"

    if len(set(hits)) == 1:
        return hits[0], "только по тексту"

    return None, f"КЭС {codes or 'нет'}, текст {sorted(set(hits)) or 'молчит'}"


def apply_to_drafts(subject: str, decisions: dict[str, int]) -> int:
    inbox = ROOT / "content" / subject / "_inbox"
    changed = 0
    for guid, number in decisions.items():
        path = inbox / f"{guid[:12].lower()}.yaml"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        updated = re.sub(
            r"^task_type: .*$",
            f"task_type: {number}",
            text,
            count=1,
            flags=re.M,
        )
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="math_prof")
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()

    parsed = ROOT / "content" / args.subject / "_inbox" / "_parsed.json"
    tasks = json.loads(parsed.read_text(encoding="utf-8"))

    decisions: dict[str, int] = {}
    unresolved: list[tuple[str, str]] = []
    for task in tasks:
        number, why = guess(task)
        if number is None:
            unresolved.append((task["statement"][:70], why))
        else:
            decisions[task["guid"]] = number

    spread = Counter(decisions.values())
    print(f"разобрано задач: {len(tasks)}")
    print(f"разложено по номерам: {len(decisions)}")
    print(f"осталось на ручную разметку: {len(unresolved)}\n")

    for number in sorted(spread):
        print(f"  №{number:<3} {spread[number]:4} задач")

    if unresolved:
        print("\nне разложились (первые 8):")
        for statement, why in unresolved[:8]:
            print(f"  · {why}")
            print(f"    {statement}…")

    if not args.dry:
        print(f"\nобновлено черновиков: {apply_to_drafts(args.subject, decisions)}")


if __name__ == "__main__":
    main()
