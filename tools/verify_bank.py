"""Независимая проверка банка задач.

    python3 tools/verify_bank.py

Читает готовые YAML-файлы и **перерешивает задачи заново, разбирая текст условия** —
как это сделал бы ученик. Генератор для этой проверки не используется: если он
ошибётся в формуле, внутренняя проверка внутри генератора этого не заметит, а эта —
заметит, потому что считает по числам из условия.

Что проверяется у всех задач:
  * YAML разбирается, поля на месте, статус корректный;
  * у live-задачи есть разбор;
  * ответ имеет вид числа и не содержит мусора;
  * нет дублей условий.

Плюс перерешивание для распознанных семейств задач (список REDOERS ниже).
Задача, которую не удалось распознать, попадает в раздел «не перепроверено» —
это не ошибка, но и не гарантия.
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "content" / "math_prof"

NUM = r"-?\d+(?:[.,]\d+)?"


def parse(text: str) -> Fraction:
    return Fraction(text.replace(",", ".").replace("−", "-"))


def close(a, b, eps=1e-9) -> bool:
    return abs(float(a) - float(b)) < eps


# --------------------------------------------------------------- перерешиватели
# Каждый принимает текст условия и возвращает верный ответ либо None,
# если условие не подходит под шаблон.


def redo_pythagoras(s: str):
    m = re.search(rf"\$AC = ({NUM})\$, \$BC = ({NUM})\$", s)
    if not m:
        return None
    a, b = parse(m[1]), parse(m[2])
    return math.hypot(float(a), float(b))


def redo_inradius(s: str):
    m = re.search(rf"Катеты.*равны \$({NUM})\$ и \$({NUM})\$.*вписанной", s, re.S)
    if not m:
        return None
    a, b = float(parse(m[1])), float(parse(m[2]))
    c = math.hypot(a, b)
    return (a + b - c) / 2


def redo_heron(s: str):
    m = re.search(rf"Стороны треугольника равны \$({NUM})\$, \$({NUM})\$ и \$({NUM})\$", s)
    if not m:
        return None
    a, b, c = (float(parse(g)) for g in m.groups())
    p = (a + b + c) / 2
    return math.sqrt(p * (p - a) * (p - b) * (p - c))


def redo_rectangle(s: str):
    m = re.search(rf"Периметр прямоугольника равен \$({NUM})\$.*равна \$({NUM})\$", s, re.S)
    if not m:
        return None
    perimeter, a = float(parse(m[1])), float(parse(m[2]))
    return a * (perimeter / 2 - a)


def redo_trapezoid(s: str):
    m = re.search(rf"Основания трапеции равны \$({NUM})\$ и \$({NUM})\$.*высота равна \$({NUM})\$", s, re.S)
    if not m:
        return None
    a, b, h = (float(parse(g)) for g in m.groups())
    return (a + b) / 2 * h


def redo_vector_length(s: str):
    m = re.search(rf"длину вектора .*?\(({NUM});\\,\s*({NUM})\)", s)
    if not m:
        return None
    return math.hypot(float(parse(m[1])), float(parse(m[2])))


def redo_vector_dot(s: str):
    m = re.search(
        rf"скалярное произведение.*?\(({NUM});\\,\s*({NUM})\).*?\(({NUM});\\,\s*({NUM})\)", s, re.S
    )
    if not m:
        return None
    x1, y1, x2, y2 = (float(parse(g)) for g in m.groups())
    return x1 * x2 + y1 * y2


def redo_vector_collinear(s: str):
    m = re.search(
        rf"Векторы.*?\(({NUM});\\,({NUM})\).*?\(({NUM});\\,m\)\$ коллинеарны", s, re.S
    )
    if not m:
        return None
    x1, y1, x2 = (float(parse(g)) for g in m.groups())
    return y1 * x2 / x1


def redo_box(s: str):
    m = re.search(rf"параллелепипеда с измерениями \$({NUM})\$, \$({NUM})\$ и \$({NUM})\$", s)
    if not m:
        return None
    a, b, c = (float(parse(g)) for g in m.groups())
    return a * b * c


def redo_cube_surface(s: str):
    m = re.search(rf"Ребро куба равно \$({NUM})\$.*полной поверхности", s, re.S)
    if not m:
        return None
    return 6 * float(parse(m[1])) ** 2


def redo_cylinder(s: str):
    m = re.search(rf"Радиус основания цилиндра равен \$({NUM})\$, высота равна \$({NUM})\$", s)
    if not m:
        return None
    r, h = float(parse(m[1])), float(parse(m[2]))
    return r * r * h


def redo_prism(s: str):
    m = re.search(rf"катетами \$({NUM})\$ и \$({NUM})\$, боковое ребро равно \$({NUM})\$", s)
    if not m:
        return None
    a, b, h = (float(parse(g)) for g in m.groups())
    return a * b / 2 * h


def redo_prob_balls(s: str):
    m = re.search(rf"В коробке \$({NUM})\$ шаров, из них \$({NUM})\$", s)
    if not m:
        return None
    total, good = float(parse(m[1])), float(parse(m[2]))
    return good / total


def redo_prob_class(s: str):
    m = re.search(rf"В классе \$({NUM})\$ учеников, из них \$({NUM})\$ девочек", s)
    if not m:
        return None
    total, girls = float(parse(m[1])), float(parse(m[2]))
    return (total - girls) / total


DICE_PREDICATES = {
    "больше $3$": lambda k: k > 3,
    "меньше $4$": lambda k: k < 4,
    "чётное число очков": lambda k: k % 2 == 0,
    "нечётное число очков": lambda k: k % 2 == 1,
    "не меньше $4$": lambda k: k >= 4,
    "не больше $3$": lambda k: k <= 3,
    "делящееся на $3$": lambda k: k % 3 == 0,
    "больше $1$": lambda k: k > 1,
    "меньше $6$": lambda k: k < 6,
}


def redo_prob_dice(s: str):
    if "Игральную кость" not in s:
        return None
    for wording, predicate in DICE_PREDICATES.items():
        if wording in s:
            return sum(1 for k in range(1, 7) if predicate(k)) / 6
    return None


def redo_prob_both(s: str):
    m = re.search(rf"первого равна \$({NUM})\$, для второго — \$({NUM})\$.*оба попадут", s, re.S)
    if not m:
        return None
    return float(parse(m[1])) * float(parse(m[2]))


def redo_prob_at_least_one(s: str):
    m = re.search(rf"выстреле равна \$({NUM})\$.*хотя бы", s, re.S)
    if not m:
        return None
    p = float(parse(m[1]))
    return 1 - (1 - p) ** 2


def redo_prob_difference(s: str):
    m = re.search(rf"больше года, равна \$({NUM})\$, а больше двух лет — \$({NUM})\$", s)
    if not m:
        return None
    return float(parse(m[1])) - float(parse(m[2]))


def redo_eq_log(s: str):
    m = re.search(rf"\\log_\{{({NUM})\}}\(({NUM})x ([+-]) ({NUM})\)=({NUM})", s)
    if not m:
        return None
    base, k, sign, b, power = (parse(m[i]) if i != 3 else m[3] for i in (1, 2, 3, 4, 5))
    value = float(base) ** float(power)
    b = float(b) * (1 if sign == "+" else -1)
    return (value - b) / float(k)


def redo_eq_exp(s: str):
    m = re.search(rf"\$({NUM})\^\{{\\,x\+({NUM})\}}=({NUM})\$", s)
    if not m:
        return None
    base, shift, value = (float(parse(g)) for g in m.groups())
    return math.log(value, base) - shift


def redo_eq_sqrt(s: str):
    m = re.search(rf"\\sqrt\{{({NUM})x ([+-]) ({NUM})\}}=({NUM})", s)
    if not m:
        return None
    k = float(parse(m[1]))
    b = float(parse(m[3])) * (1 if m[2] == "+" else -1)
    root = float(parse(m[4]))
    return (root * root - b) / k


def redo_eq_fraction(s: str):
    m = re.search(rf"\\dfrac\{{x-({NUM})\}}\{{x\+({NUM})\}}=0", s)
    if not m:
        return None
    return float(parse(m[1]))


def redo_eq_linear(s: str):
    m = re.search(rf"\$({NUM})x \+ \(({NUM})\) = ({NUM})x \+ \(({NUM})\)\$", s)
    if not m:
        return None
    a, b, c, d = (float(parse(g)) for g in m.groups())
    return (d - b) / (a - c)


def redo_calc_log_diff(s: str):
    m = re.search(rf"\\log_\{{({NUM})\}}({NUM})-\\log_\{{({NUM})\}}({NUM})", s)
    if not m:
        return None
    base, big, base2, small = (float(parse(g)) for g in m.groups())
    if base != base2:
        return None
    return math.log(big / small, base)


def redo_calc_powers(s: str):
    m = re.search(
        rf"\\dfrac\{{({NUM})\^\{{({NUM})\}}\\cdot ({NUM})\^\{{({NUM})\}}\}}\{{({NUM})\^\{{({NUM})\}}\}}",
        s,
    )
    if not m:
        return None
    b1, p1, b2, p2, b3, p3 = (float(parse(g)) for g in m.groups())
    if not (b1 == b2 == b3):
        return None
    return b1 ** (p1 + p2 - p3)


def redo_calc_frac_power(s: str):
    m = re.search(rf"\\dfrac\{{({NUM})\^\{{\\,({NUM}),5\}}\}}\{{({NUM})\^\{{\\,0,5\}}\}}", s)
    if not m:
        return None
    base, whole, base2 = (float(parse(g)) for g in m.groups())
    if base != base2:
        return None
    return base ** ((whole + 0.5) - 0.5)


def redo_derivative(s: str):
    m = re.search(
        rf"f\(x\)=({NUM})x\^\{{3\}}([+-]{NUM})x\^\{{2\}}([+-]{NUM})x\$.*?f'\(({NUM})\)", s, re.S
    )
    if not m:
        return None
    a, b, c, x0 = (float(parse(g)) for g in m.groups())
    f = lambda t: a * t**3 + b * t**2 + c * t
    return (f(x0 + 1e-5) - f(x0 - 1e-5)) / 2e-5  # численная производная


def redo_tangent(s: str):
    m = re.search(rf"Прямая \$y=({NUM})x([+-]{NUM})\$.*?y=({NUM})x\^\{{2\}}([+-]{NUM})x", s, re.S)
    if not m:
        return None
    k, _shift, a, b = (float(parse(g)) for g in m.groups())
    return (k - b) / (2 * a)


def redo_applied_power(s: str):
    m = re.search(rf"\$I=({NUM})\$ А, а сопротивление \$R=({NUM})\$", s)
    if not m:
        return None
    return float(parse(m[1])) ** 2 * float(parse(m[2]))


def redo_applied_height(s: str):
    m = re.search(rf"h\(t\)=({NUM})\+({NUM})t-5t\^\{{2\}}.*?высоте \$({NUM})\$", s, re.S)
    if not m:
        return None
    h0, v0, target = (float(parse(g)) for g in m.groups())
    # 5t^2 - v0 t + (target - h0) = 0
    disc = v0 * v0 - 4 * 5 * (target - h0)
    if disc < 0:
        return None
    return (v0 - math.sqrt(disc)) / 10  # первый по времени, то есть меньший корень


def redo_applied_ohm(s: str):
    m = re.search(rf"равны \$({NUM})\$ Ом и \$({NUM})\$ Ом", s)
    if not m:
        return None
    r1, r2 = float(parse(m[1])), float(parse(m[2]))
    return 1 / (1 / r1 + 1 / r2)


def redo_mixture(s: str):
    m = re.search(
        rf"Смешали \$({NUM})\$ кг.*?соли \$({NUM})\\%\$ и \$({NUM})\$ кг.*?\$({NUM})\\%\$", s, re.S
    )
    if not m:
        return None
    m1, c1, m2, c2 = (float(parse(g)) for g in m.groups())
    return (m1 * c1 + m2 * c2) / (m1 + m2)


def redo_speed(s: str):
    m = re.search(
        rf"проехал \$({NUM})\$ км.*?на \$({NUM})\$ км/ч.*?на \$({NUM})\$ час", s, re.S
    )
    if not m:
        return None
    distance, delta, hours = (float(parse(g)) for g in m.groups())
    # distance/v - distance/(v+delta) = hours  =>  hours*v^2 + hours*delta*v - distance*delta = 0
    a, b, c = hours, hours * delta, -distance * delta
    disc = b * b - 4 * a * c
    return (-b + math.sqrt(disc)) / (2 * a)


def redo_percent(s: str):
    m = re.search(
        rf"стоил \$({NUM})\$ рублей.*?на \$({NUM})\\%\$, а затем ещё на \$({NUM})\\%\$", s, re.S
    )
    if not m:
        return None
    price, d1, d2 = (float(parse(g)) for g in m.groups())
    return price * (1 - d1 / 100) * (1 - d2 / 100)


def redo_hyperbola(s: str):
    m = re.search(rf"\\dfrac\{{k\}}\{{x\}}\$ проходит через точку \$\(({NUM});\\,({NUM})\)", s)
    if not m:
        return None
    return float(parse(m[1])) * float(parse(m[2]))


def redo_parabola(s: str):
    m = re.search(
        rf"y=x\^\{{2\}}\+bx\+c\$ проходит через точки \$\(0;\\,({NUM})\)\$ и \$\(({NUM});\\,({NUM})\)",
        s,
    )
    if not m:
        return None
    c, x1, y1 = (float(parse(g)) for g in m.groups())
    return (y1 - x1 * x1 - c) / x1


def redo_linear(s: str):
    m = re.search(
        rf"y=kx\+b\$ проходит через точки \$\(({NUM});\\,({NUM})\)\$ и \$\(({NUM});\\,({NUM})\)",
        s,
    )
    if not m:
        return None
    x1, y1, x2, y2 = (float(parse(g)) for g in m.groups())
    return (y2 - y1) / (x2 - x1)


def redo_min_cubic(s: str):
    m = re.search(
        rf"y=x\^\{{3\}}-({NUM})x\+({NUM})\$ на отрезке \$\[({NUM});\\,({NUM})\]", s
    )
    if not m:
        return None
    k, c, left, right = (float(parse(g)) for g in m.groups())
    f = lambda x: x**3 - k * x + c
    steps = 200000
    return min(f(left + i * (right - left) / steps) for i in range(steps + 1))


def redo_min_hyperbola(s: str):
    m = re.search(rf"y=x\+\\dfrac\{{({NUM})\}}\{{x\}}\$ при \$x>0", s)
    if not m:
        return None
    a = float(parse(m[1]))
    f = lambda x: x + a / x
    return min(f(0.001 + i * 0.001) for i in range(1, 200000))


def redo_max_quadratic(s: str):
    m = re.search(rf"y=-({NUM})x\^\{{2\}}([+-]{NUM})x([+-]{NUM})\$", s)
    if not m:
        return None
    a, b, c = (float(parse(g)) for g in m.groups())
    f = lambda x: -a * x * x + b * x + c
    x0 = b / (2 * a)
    return f(x0)


REDOERS = [
    redo_pythagoras, redo_inradius, redo_heron, redo_rectangle, redo_trapezoid,
    redo_vector_length, redo_vector_dot, redo_vector_collinear, redo_box, redo_cube_surface, redo_cylinder,
    redo_prism, redo_prob_balls, redo_prob_class, redo_prob_dice, redo_prob_both,
    redo_prob_at_least_one, redo_prob_difference, redo_eq_log, redo_eq_exp,
    redo_eq_sqrt, redo_eq_fraction, redo_eq_linear, redo_calc_log_diff,
    redo_calc_powers, redo_calc_frac_power, redo_derivative, redo_tangent,
    redo_applied_power, redo_applied_height, redo_applied_ohm, redo_mixture,
    redo_speed, redo_percent, redo_hyperbola, redo_parabola, redo_linear,
    redo_min_cubic, redo_min_hyperbola, redo_max_quadratic,
]

# у численных методов точность ограничена — где нужен допуск помягче
TOLERANT = {"redo_min_cubic", "redo_min_hyperbola", "redo_derivative", "redo_speed"}


def load(path: Path) -> dict:
    """Минимальный разбор нашего же YAML — без зависимости от pyyaml."""
    data: dict = {}
    key = None
    block: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("  ") and key in ("statement", "solution"):
            block.append(raw.strip())
            continue
        if key in ("statement", "solution") and block:
            data[key] = " ".join(block)
            block = []
        if raw.startswith("  ") or not raw.strip():
            if raw.strip().startswith("value:"):
                data["answer"] = raw.split(":", 1)[1].strip().strip("'")
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if value and value != "|":
            data[key] = value
    if key in ("statement", "solution") and block:
        data[key] = " ".join(block)
    return data


def main() -> int:
    files = sorted(ROOT.rglob("*.yaml"))
    if not files:
        print("Банк пуст")
        return 1

    problems: list[str] = []
    rechecked = 0
    unchecked: Counter[int] = Counter()
    statements: dict[str, str] = {}
    by_redoer: Counter[str] = Counter()

    for path in files:
        data = load(path)
        name = path.name

        for field in ("id", "subject", "task_type", "statement", "answer", "status"):
            if not data.get(field):
                problems.append(f"{name}: нет поля «{field}»")

        statement = data.get("statement", "")
        answer = data.get("answer", "")

        if data.get("status") == "live" and not data.get("solution"):
            problems.append(f"{name}: опубликована без разбора")

        if not re.fullmatch(r"-?\d+(?:\.\d+)?", answer or ""):
            problems.append(f"{name}: ответ «{answer}» не похож на число")
            continue

        if statement in statements:
            problems.append(f"{name}: дубль условия с {statements[statement]}")
        else:
            statements[statement] = name

        expected = float(answer)
        for redoer in REDOERS:
            got = redoer(statement)
            if got is None:
                continue
            eps = 2e-3 if redoer.__name__ in TOLERANT else 1e-6
            if not close(got, expected, eps):
                problems.append(
                    f"{name}: перерешивание даёт {got:.6g}, а в банке {expected:.6g} "
                    f"({redoer.__name__})"
                )
            rechecked += 1
            by_redoer[redoer.__name__] += 1
            break
        else:
            unchecked[int(data.get("task_type", 0))] += 1

    print(f"Файлов в банке: {len(files)}")
    print(f"Перерешано независимо: {rechecked}")
    if unchecked:
        total_unchecked = sum(unchecked.values())
        print(f"Не перепроверено: {total_unchecked} " f"(по номерам: {dict(sorted(unchecked.items()))})")

    if problems:
        print(f"\nПроблемы ({len(problems)}):")
        for problem in problems[:40]:
            print("  •", problem)
        if len(problems) > 40:
            print(f"  … и ещё {len(problems) - 40}")
        return 1

    print("\nРасхождений нет: каждый перепроверенный ответ сошёлся с условием.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
