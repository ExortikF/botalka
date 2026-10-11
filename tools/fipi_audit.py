"""Независимая проверка ответов в готовом банке.

    tools/.venv/bin/python tools/fipi_audit.py

Читает `content/<предмет>/<номер>/*.yaml` — то есть ровно то, что уезжает в базу,
— и пытается **опровергнуть** записанный ответ. Это не повтор работы решателя:
там, где решатель считал символьно, аудит считает численно и наоборот, а
формулировки разбирает заново из текста условия.

Проверки трёх сортов:

1. **Здравый смысл по типу задания.** Вероятность не бывает больше единицы,
   синус и косинус не выходят за $[-1;1]$, длина и объём не отрицательны, угол
   в градусах лежит в разумных пределах. Такие ошибки говорят не об арифметике,
   а о том, что условие поняли неправильно.
2. **Численное перерешивание** уравнений, выражений и экстремумов: корни ищутся
   сканированием по сетке со сменой знака, значения считаются с повышенной
   точностью. Символьный `solve` здесь не используется вовсе.
3. **Дубли.** Одинаковое условие с разными ответами — верный признак ошибки;
   одинаковое условие с одинаковым ответом — просто повтор в банке.

Аудит намеренно молчалив: он сообщает только то, что смог опровергнуть или в
чём не уверен. «Проверено и сходится» печатается сводкой в конце.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

import sympy

import fipi_solve as solver

ROOT = Path(__file__).resolve().parent.parent
X = solver.X


def field(text: str, name: str) -> str:
    match = re.search(rf"^{name}: (.*)$", text, re.M)
    return match.group(1).strip().strip('"') if match else ""


def statement_of(text: str) -> str:
    match = re.search(r"^statement: \|\n((?:  .*\n)+)", text, re.M)
    if not match:
        return ""
    return " ".join(line.strip() for line in match.group(1).split("\n")).strip()


def as_number(answer: str) -> float | None:
    try:
        return float(answer.replace(",", "."))
    except ValueError:
        return None


# ------------------------------------------------------------------ здравый смысл


def sanity(number: int, statement: str, answer: str) -> str | None:
    value = as_number(answer)
    if value is None:
        return f"ответ «{answer}» не число"

    low = statement.lower()

    if number in (4, 5) and not 0 <= value <= 1:
        return f"вероятность {value} вне [0;1]"

    if re.search(r"найдите\s+\$?\\?(cos|sin|\\cos|\\sin)", low) and abs(value) > 1:
        return f"синус или косинус равен {value}"

    if "ответ дайте в градусах" in low and not 0 < value < 360:
        return f"угол {value}° вне разумных границ"

    if re.search(r"найдите (объём|площадь|радиус|длину|периметр|высоту)", low) and value <= 0:
        return f"{value} — не бывает отрицательной длины, площади или объёма"

    if number == 2 and "длину вектора" in low and value < 0:
        return f"длина вектора {value} отрицательна"

    return None


# ------------------------------------------------- пересчёт по числам из условия

RIGHT_TRIANGLE = re.compile(
    r"угол\s*\$?([A-Z])\$?\s*равен\s*\$?90", re.I
)
SIDE = re.compile(r"\$?([A-Z]{2})\s*=\s*(\\sqrt\{)?(\d+)\}?", re.I)


def recheck_triangle(statement: str, answer: str) -> tuple[str | None, bool]:
    """Прямоугольный треугольник: считаем катет по Пифагору и сверяем синус или
    косинус. Это ровно то, что делает ученик, — и полностью независимо от того,
    как ответ получился у нас."""
    if not RIGHT_TRIANGLE.search(statement):
        return None, False

    asked = re.search(r"Найдите\s*\$?\\?(cos|sin)\s*([A-Z])", statement, re.I)
    if not asked:
        return None, False
    what, vertex = asked.group(1).lower(), asked.group(2).upper()

    sides: dict[str, float] = {}
    for name, root, digits in SIDE.findall(statement):
        value = float(digits) ** 0.5 if root else float(digits)
        sides["".join(sorted(name.upper()))] = value

    # гипотенуза — сторона, не содержащая вершины прямого угла
    right_vertex = RIGHT_TRIANGLE.search(statement).group(1).upper()
    hypotenuse = next((k for k in sides if right_vertex not in k), None)
    if hypotenuse is None or len(sides) < 2:
        return None, False

    legs = [k for k in sides if k != hypotenuse]
    if len(legs) != 1:
        return None, False

    known_leg, hyp = sides[legs[0]], sides[hypotenuse]
    if hyp <= known_leg:
        return None, False
    other_leg = (hyp**2 - known_leg**2) ** 0.5

    # прилежащий к вершине катет содержит её букву
    adjacent = known_leg if vertex in legs[0] else other_leg
    opposite = other_leg if vertex in legs[0] else known_leg

    expected = adjacent / hyp if what == "cos" else opposite / hyp
    value = as_number(answer)
    if value is None:
        return None, False
    if abs(expected - value) > 1e-6:
        return f"по числам условия {what} = {expected:.4g}, а записано {value}", True
    return None, True


def recheck_vectors(statement: str, answer: str) -> tuple[str | None, bool]:
    """Векторы: складываем координаты и считаем длину или произведение вручную,
    обычной арифметикой, без sympy."""
    if "\\overrightarrow" not in statement:
        return None, False

    vectors = solver.vector_parts(statement)
    if len(vectors) < 2:
        return None, False

    chunks = re.findall(r"\$([^$]+)\$", statement)
    targets = [c for c in chunks if "\\overrightarrow" in c and "(" not in c]
    if not targets:
        return None, False

    value = as_number(answer)
    if value is None:
        return None, False

    try:
        if "длину вектора" in statement.lower():
            x, y = solver.combination(targets[-1], vectors)
            expected = (float(x) ** 2 + float(y) ** 2) ** 0.5
        elif "скалярное произведение" in statement.lower():
            # Произведение записывают и двумя кусками («$u$ и $v$»), и одним
            # («$u\cdot v$») — разбираем оба вида, иначе половина задач
            # остаётся без проверки.
            if len(targets) >= 2:
                first, second = targets[-2], targets[-1]
            elif "\\cdot" in targets[-1]:
                first, second = targets[-1].split("\\cdot", 1)
            else:
                return None, False
            x1, y1 = solver.combination(first, vectors)
            x2, y2 = solver.combination(second, vectors)
            expected = float(x1) * float(x2) + float(y1) * float(y2)
        else:
            return None, False
    except Exception:
        return None, False

    if abs(expected - value) > 1e-6:
        return f"по координатам получается {expected:.6g}, а записано {value}", True
    return None, True


def recheck_average(statement: str, answer: str) -> tuple[str | None, bool]:
    """«В среднем из N — M»: доля считается двумя делениями и сверяется с суммой."""
    match = solver.AVERAGE.search(statement)
    if not match:
        return None, False
    total, part = int(match.group(1)), int(match.group(2))
    value = as_number(answer)
    if value is None or total == 0:
        return None, False

    options = {part / total, (total - part) / total}
    if not any(abs(option - value) < 1e-9 for option in options):
        return f"из чисел {total} и {part} получается {sorted(options)}, а записано {value}", True
    return None, True


# ------------------------------------------------------------------ перерешивание


def numeric_roots(left: sympy.Expr, right: sympy.Expr) -> list[float]:
    """Корни уравнения сканированием: ищем смену знака и уточняем делением отрезка.

    Символьное решение здесь не используется намеренно — иначе это была бы та же
    дорога, что у решателя, и ошибку в ней проверка бы не заметила."""
    difference = sympy.lambdify(X, left - right, "math")
    found: list[float] = []
    step = 0.05
    previous_x = -60.0
    try:
        previous = difference(previous_x)
    except Exception:
        previous = None

    x = previous_x + step
    while x <= 60.0:
        try:
            current = difference(x)
        except Exception:
            current, previous = None, None
            x += step
            continue

        if previous is not None and current is not None and previous * current < 0:
            low, high = x - step, x
            for _ in range(60):
                middle = (low + high) / 2
                try:
                    value = difference(middle)
                except Exception:
                    break
                if difference(low) * value <= 0:
                    high = middle
                else:
                    low = middle
            found.append((low + high) / 2)

        previous = current
        x += step
    return found


def recheck(number: int, statement: str, answer: str) -> tuple[str | None, bool]:
    """Перерешать задачу численно.

    Возвращает жалобу (или None) и признак того, что задачу вообще удалось
    перерешать. Признак нужен, чтобы сводка не врала: «проверено 200» звучит
    внушительно ровно до того момента, когда выясняется, что половину из них
    проверка просто не умеет разбирать."""
    value = as_number(answer)
    if value is None:
        return None, False

    low = statement.lower()

    for extra in (recheck_triangle, recheck_vectors, recheck_average):
        complaint, applicable = extra(statement, answer)
        if applicable:
            return complaint, True

    chunks = re.findall(r"\$([^$]+)\$", statement)
    if not chunks:
        return None, False

    try:
        if solver.EQUATION.search(low):
            tex = " ".join(chunks)
            if "=" not in tex:
                return None, False
            left_tex, right_tex = tex.split("=", 1)
            left = solver.tex_to_sympy(left_tex)
            right = solver.tex_to_sympy(right_tex)
            roots = numeric_roots(left, right)
            if not roots:
                return None, False  # численно не нашли — не повод обвинять
            if not any(abs(root - value) < 1e-4 for root in roots):
                return f"численно корни {[round(r, 4) for r in roots]}, а записано {value}", True
            return None, True

        elif solver.EXPRESSION.search(low):
            expr = solver.tex_to_sympy(" ".join(chunks))
            if expr.free_symbols:
                return None, False
            exact = float(sympy.N(expr, 40))
            if abs(exact - value) > 1e-6:
                return f"выражение равно {exact:.6g}, а записано {value}", True
            return None, True

        elif solver.MIN_VALUE.search(low) or solver.MAX_VALUE.search(low):
            # Сканируем отрезок мелкой сеткой через lambdify. Решатель считал
            # иначе — через нули производной, — поэтому проверка независима.
            formula = re.sub(r"^y\s*=", "", chunks[0]).strip()
            expr = solver.tex_to_sympy(formula)
            segment = solver.parse_segment(chunks[1:])
            if segment is None:
                return None, False
            f = sympy.lambdify(X, expr, "math")
            low_x, high_x = segment[0], segment[1]
            values = []
            steps = 20000
            for i in range(steps + 1):
                point = low_x + (high_x - low_x) * i / steps
                try:
                    values.append(f(point))
                except Exception:
                    continue
            if not values:
                return None, False
            kind = "min" if solver.MIN_VALUE.search(low) else "max"
            best = min(values) if kind == "min" else max(values)
            if abs(best - value) > 1e-3:
                return f"сканированием отрезка получается {best:.6g}, а записано {value}", True
            return None, True

        elif solver.MIN_POINT.search(low) or solver.MAX_POINT.search(low):
            formula = re.sub(r"^y\s*=", "", chunks[0]).strip()
            expr = solver.tex_to_sympy(formula)
            f = sympy.lambdify(X, expr, "math")
            kind = "min" if solver.MIN_POINT.search(low) else "max"
            step = 1e-3
            here, left_v, right_v = f(value), f(value - step), f(value + step)
            if kind == "min" and not (left_v > here < right_v):
                return f"в точке {value} функция не имеет минимума", True
            if kind == "max" and not (left_v < here > right_v):
                return f"в точке {value} функция не имеет максимума", True
            return None, True

    except Exception:
        return None, False  # разобрать не смогли — молчим, это не обвинение

    return None, False


# ------------------------------------------------------------------ прогон


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="math_prof")
    args = parser.parse_args()

    problems: list[str] = []
    shallow: list[str] = []
    rechecked = 0
    by_statement: dict[str, list[tuple[str, str]]] = defaultdict(list)
    total = 0

    for folder in sorted((ROOT / "content" / args.subject).glob("[0-9][0-9]")):
        number = int(folder.name)
        for path in sorted(folder.glob("*.yaml")):
            text = path.read_text(encoding="utf-8")
            statement = statement_of(text)
            answer = field(text, "  value") or field(text, "value")
            total += 1
            by_statement[statement].append((answer, path.name))

            complaint = sanity(number, statement, answer)
            if complaint:
                problems.append(f"№{number} {path.name}: {complaint}\n    {statement[:110]}")
                continue

            with_timeout, checked = None, False
            try:
                with solver.time_limit(10):
                    with_timeout, checked = recheck(number, statement, answer)
            except solver.Timeout:
                pass
            except Exception:
                pass

            if checked:
                rechecked += 1
            else:
                shallow.append(f"№{number} {path.name}")

            if with_timeout:
                problems.append(f"№{number} {path.name}: {with_timeout}\n    {statement[:110]}")

    duplicates = 0
    for statement, entries in by_statement.items():
        answers = {answer for answer, _ in entries}
        if len(entries) > 1 and len(answers) > 1:
            problems.append(
                f"одно условие — разные ответы {sorted(answers)}: "
                + ", ".join(name for _, name in entries)
                + f"\n    {statement[:110]}"
            )
        elif len(entries) > 1:
            duplicates += 1

    print(f"проверено задач: {total}")
    print(f"перерешано независимо: {rechecked}")
    print(f"только на здравый смысл: {len(shallow)}")
    print(f"повторов условия (одинаковый ответ): {duplicates}")
    print(f"\nнайдено проблем: {len(problems)}")
    for item in problems:
        print(f"  · {item}")

    if shallow:
        by_number: dict[str, int] = defaultdict(int)
        for item in shallow:
            by_number[item.split()[0]] += 1
        print("\nне перерешано (проверен только здравый смысл), по номерам:")
        for key in sorted(by_number, key=lambda k: int(k.strip("№"))):
            print(f"  {key}: {by_number[key]}")


if __name__ == "__main__":
    main()
