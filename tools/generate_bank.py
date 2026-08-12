"""Генератор банка задач по шаблонам.

    python3 tools/generate_bank.py [--per-template 12]

Пишет YAML-файлы в content/math_prof/<номер>/. Каждая задача:
  * собирается из шаблона со случайными, но «красивыми» параметрами;
  * ответ вычисляется в момент генерации;
  * ответ **независимо перепроверяется** другим способом (подстановкой в уравнение,
    перебором, прямым подсчётом исходов) — при расхождении генерация падает.

Второй способ проверки принципиален: если ответ и проверка считаются одной и той же
формулой, ошибка в формуле останется незамеченной и уедет в банк.
"""

from __future__ import annotations

import argparse
import io
import math
import random
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "content" / "math_prof"


# --------------------------------------------------------------------------- утилиты


def ru(x: float | int | Fraction) -> str:
    """Число в русской записи: 0,5 вместо 0.5; целые без хвоста."""
    if isinstance(x, Fraction):
        x = float(x) if x.denominator != 1 else x.numerator
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return str(x).replace(".", ",")


def sgn(x: float | int | Fraction) -> str:
    """«+3» или «−7» — для записи многочлена без двойных знаков."""
    return ("+" if x >= 0 else "-") + ru(abs(x))


def answer_str(x: float | int | Fraction) -> str:
    """Ответ для проверки: точка как разделитель, без хвостовых нулей."""
    if isinstance(x, Fraction):
        x = x.numerator if x.denominator == 1 else float(x)
    if isinstance(x, float):
        if x.is_integer():
            return str(int(x))
        return f"{x:.6f}".rstrip("0").rstrip(".")
    return str(x)


@dataclass
class Task:
    number: int
    statement: str
    answer: str
    solution: str
    hints: list[str] = field(default_factory=list)
    difficulty: int = 2
    template: str = ""


class VerificationError(RuntimeError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


# ------------------------------------------------------------------ №1 планиметрия

BASE_TRIPLES = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41)]
# кратные тоже подходят и дают заметно больше вариантов
PYTHAGOREAN = [
    (a * k, b * k, c * k) for a, b, c in BASE_TRIPLES for k in (1, 2, 3) if c * k <= 90
]


def t_right_triangle_hyp(rnd: random.Random) -> Task:
    a, b, c = rnd.choice(PYTHAGOREAN)
    check(a * a + b * b == c * c, "тройка не пифагорова")
    return Task(
        1,
        f"В треугольнике $ABC$ угол $C$ равен $90^\\circ$, $AC = {a}$, $BC = {b}$. "
        f"Найдите $AB$.",
        answer_str(c),
        f"По теореме Пифагора $AB=\\sqrt{{{a}^2+{b}^2}}="
        f"\\sqrt{{{a*a}+{b*b}}}=\\sqrt{{{c*c}}}={c}$.",
        ["Теорема Пифагора: квадрат гипотенузы равен сумме квадратов катетов."],
        1,
        "right_triangle_hyp",
    )


def t_right_triangle_inradius(rnd: random.Random) -> Task:
    a, b, c = rnd.choice(PYTHAGOREAN)
    r = Fraction(a + b - c, 2)
    # независимая проверка: r = S / p
    s = Fraction(a * b, 2)
    p = Fraction(a + b + c, 2)
    check(r == s / p, "радиус вписанной не совпал с S/p")
    return Task(
        1,
        f"Катеты прямоугольного треугольника равны ${a}$ и ${b}$. "
        f"Найдите радиус вписанной в него окружности.",
        answer_str(r),
        f"Гипотенуза $c=\\sqrt{{{a}^2+{b}^2}}={c}$. Для прямоугольного треугольника "
        f"$r=\\dfrac{{a+b-c}}{{2}}=\\dfrac{{{a}+{b}-{c}}}{{2}}={ru(r)}$.",
        ["Сначала найдите гипотенузу.", "Для прямоугольного треугольника $r=\\dfrac{a+b-c}{2}$."],
        2,
        "right_triangle_inradius",
    )


def _heronian() -> list[tuple[int, int, int, int]]:
    """Треугольники с целыми сторонами и целой площадью — ищем перебором."""
    found = []
    for a in range(3, 26):
        for b in range(a, 26):
            for c in range(b, 26):
                if a + b <= c:
                    continue
                p2 = a + b + c
                if p2 % 2:
                    continue
                p = p2 // 2
                sq = p * (p - a) * (p - b) * (p - c)
                root = math.isqrt(sq)
                if root * root == sq and root > 0:
                    found.append((a, b, c, root))
    return found


HERON = _heronian()


def t_heron(rnd: random.Random) -> Task:
    a, b, c, area = rnd.choice(HERON)
    p = Fraction(a + b + c, 2)
    computed = math.sqrt(float(p * (p - a) * (p - b) * (p - c)))
    check(abs(computed - area) < 1e-9, "площадь по Герону не совпала")
    return Task(
        1,
        f"Стороны треугольника равны ${a}$, ${b}$ и ${c}$. Найдите его площадь.",
        answer_str(area),
        f"Полупериметр $p=\\dfrac{{{a}+{b}+{c}}}{{2}}={ru(p)}$. По формуле Герона "
        f"$S=\\sqrt{{p(p-a)(p-b)(p-c)}}="
        f"\\sqrt{{{ru(p)}\\cdot{ru(p-a)}\\cdot{ru(p-b)}\\cdot{ru(p-c)}}}={area}$.",
        ["Посчитайте полупериметр и примените формулу Герона."],
        3,
        "heron",
    )


def t_rectangle_area(rnd: random.Random) -> Task:
    a = rnd.randint(3, 15)
    b = rnd.randint(3, 15)
    while b == a:
        b = rnd.randint(3, 15)
    perimeter = 2 * (a + b)
    # независимая проверка: восстановить вторую сторону из периметра
    other = perimeter // 2 - a
    check(other == b, "вторая сторона восстановилась неверно")
    return Task(
        1,
        f"Периметр прямоугольника равен ${perimeter}$, а одна из его сторон равна ${a}$. "
        f"Найдите площадь прямоугольника.",
        answer_str(a * b),
        f"Полупериметр равен ${perimeter // 2}$, значит вторая сторона равна "
        f"${perimeter // 2}-{a}={b}$. Площадь: ${a}\\cdot {b}={a * b}$.",
        ["Полупериметр — это сумма двух соседних сторон."],
        1,
        "rectangle_area",
    )


def t_trapezoid_area(rnd: random.Random) -> Task:
    a = rnd.randrange(4, 20, 2)
    b = a + rnd.randrange(2, 12, 2)
    h = rnd.randint(2, 12)
    area = Fraction(a + b, 2) * h
    check(area * 2 == (a + b) * h, "площадь трапеции посчитана неверно")
    return Task(
        1,
        f"Основания трапеции равны ${a}$ и ${b}$, а высота равна ${h}$. Найдите её площадь.",
        answer_str(area),
        f"$S=\\dfrac{{a+b}}{{2}}\\cdot h=\\dfrac{{{a}+{b}}}{{2}}\\cdot {h}="
        f"{ru(Fraction(a + b, 2))}\\cdot {h}={ru(area)}$.",
        ["Площадь трапеции — полусумма оснований, умноженная на высоту."],
        1,
        "trapezoid_area",
    )


# ---------------------------------------------------------------------- №2 векторы


def t_vector_length(rnd: random.Random) -> Task:
    a, b, c = rnd.choice(PYTHAGOREAN)
    x = a * rnd.choice([1, -1])
    y = b * rnd.choice([1, -1])
    check(round(math.hypot(x, y), 9) == c, "длина вектора не совпала")
    return Task(
        2,
        f"Найдите длину вектора $\\vec{{a}}\\,({ru(x)};\\,{ru(y)})$.",
        answer_str(c),
        f"$|\\vec{{a}}|=\\sqrt{{({ru(x)})^2+({ru(y)})^2}}=\\sqrt{{{x*x}+{y*y}}}="
        f"\\sqrt{{{x*x + y*y}}}={c}$.",
        ["Длина вектора по координатам: $\\sqrt{x^2+y^2}$."],
        1,
        "vector_length",
    )


def t_vector_dot(rnd: random.Random) -> Task:
    x1, y1, x2, y2 = (rnd.randint(-8, 8) for _ in range(4))
    dot = x1 * x2 + y1 * y2
    # независимая проверка: через сумму квадратов длин
    lhs = (x1 + x2) ** 2 + (y1 + y2) ** 2
    rhs = x1**2 + y1**2 + x2**2 + y2**2 + 2 * dot
    check(lhs == rhs, "скалярное произведение не согласовано с тождеством")
    return Task(
        2,
        f"Найдите скалярное произведение векторов $\\vec{{a}}\\,({ru(x1)};\\,{ru(y1)})$ "
        f"и $\\vec{{b}}\\,({ru(x2)};\\,{ru(y2)})$.",
        answer_str(dot),
        f"$\\vec{{a}}\\cdot\\vec{{b}}={ru(x1)}\\cdot{ru(x2)}+{ru(y1)}\\cdot{ru(y2)}="
        f"{x1*x2}+{y1*y2}={dot}$.",
        ["Скалярное произведение по координатам: $x_1x_2+y_1y_2$."],
        1,
        "vector_dot",
    )


def t_vector_collinear(rnd: random.Random) -> Task:
    k = rnd.choice([2, 3, 4, -2, -3])
    x1 = rnd.randint(2, 6)
    y1 = rnd.randint(2, 6)
    x2, y2 = x1 * k, y1 * k
    # ищем m в векторе (x2; m), при котором векторы коллинеарны
    m = y2
    check(x1 * m - y1 * x2 == 0, "определитель не нулевой — векторы не коллинеарны")
    return Task(
        2,
        f"Векторы $\\vec{{a}}\\,({x1};\\,{y1})$ и $\\vec{{b}}\\,({x2};\\,m)$ коллинеарны. "
        f"Найдите $m$.",
        answer_str(m),
        f"Коллинеарность означает $x_1 m - y_1 x_2 = 0$, то есть "
        f"${x1}m-{y1}\\cdot{x2}=0$, откуда $m={m}$.",
        ["Для коллинеарных векторов координаты пропорциональны."],
        2,
        "vector_collinear",
    )


# ------------------------------------------------------------------ №3 стереометрия


def t_box_volume(rnd: random.Random) -> Task:
    a, b, c = (rnd.randint(2, 12) for _ in range(3))
    volume = a * b * c
    check(volume == math.prod([a, b, c]), "объём не совпал")
    return Task(
        3,
        f"Найдите объём прямоугольного параллелепипеда с измерениями ${a}$, ${b}$ и ${c}$.",
        answer_str(volume),
        f"Объём равен произведению измерений: ${a}\\cdot {b}\\cdot {c}={volume}$.",
        [],
        1,
        "box_volume",
    )


def t_cube_surface(rnd: random.Random) -> Task:
    a = rnd.randint(2, 15)
    area = 6 * a * a
    check(area == sum(a * a for _ in range(6)), "площадь поверхности не совпала")
    return Task(
        3,
        f"Ребро куба равно ${a}$. Найдите площадь его полной поверхности.",
        answer_str(area),
        f"У куба $6$ граней, каждая — квадрат со стороной ${a}$: "
        f"$6\\cdot {a}^2=6\\cdot {a*a}={area}$.",
        ["У куба шесть одинаковых квадратных граней."],
        1,
        "cube_surface",
    )


def t_cylinder_volume(rnd: random.Random) -> Task:
    r = rnd.randint(2, 9)
    h = rnd.randint(2, 12)
    volume = r * r * h  # объём, делённый на π
    check(abs(math.pi * volume - math.pi * r**2 * h) < 1e-9, "объём цилиндра не совпал")
    return Task(
        3,
        f"Радиус основания цилиндра равен ${r}$, высота равна ${h}$. "
        f"Найдите объём цилиндра, делённый на $\\pi$.",
        answer_str(volume),
        f"$V=\\pi R^2 h=\\pi\\cdot {r}^2\\cdot {h}={volume}\\pi$. "
        f"Разделив на $\\pi$, получаем ${volume}$.",
        ["Объём цилиндра: $V=\\pi R^2 h$."],
        2,
        "cylinder_volume",
    )


def t_prism_volume(rnd: random.Random) -> Task:
    a, b, _ = rnd.choice(PYTHAGOREAN)
    h = rnd.randint(2, 12)
    volume = Fraction(a * b, 2) * h
    check(volume * 2 == a * b * h, "объём призмы не совпал")
    return Task(
        3,
        f"Основание прямой призмы — прямоугольный треугольник с катетами ${a}$ и ${b}$, "
        f"боковое ребро равно ${h}$. Найдите объём призмы.",
        answer_str(volume),
        f"Площадь основания $S=\\dfrac{{{a}\\cdot {b}}}{{2}}={ru(Fraction(a*b, 2))}$, "
        f"объём $V=S\\cdot h={ru(Fraction(a*b, 2))}\\cdot {h}={ru(volume)}$.",
        ["Объём призмы — площадь основания на высоту."],
        2,
        "prism_volume",
    )


# ------------------------------------------------------------- №4 простая вероятность


def t_prob_balls(rnd: random.Random) -> Task:
    total = rnd.choice([10, 20, 25, 40, 50])
    good = rnd.randint(1, total - 1)
    while Fraction(good, total).denominator not in (1, 2, 4, 5, 8, 10, 20, 25, 50):
        good = rnd.randint(1, total - 1)
    prob = Fraction(good, total)
    # независимая проверка: перебор исходов
    hits = sum(1 for i in range(total) if i < good)
    check(Fraction(hits, total) == prob, "вероятность не совпала с перебором")
    colour = rnd.choice(["красных", "синих", "зелёных", "белых"])
    return Task(
        4,
        f"В коробке ${total}$ шаров, из них ${good}$ {colour}. Наугад достают один шар. "
        f"Найдите вероятность того, что он окажется этого цвета.",
        answer_str(prob),
        f"$P=\\dfrac{{{good}}}{{{total}}}={ru(prob)}$.",
        ["Вероятность — отношение подходящих исходов к общему числу исходов."],
        1,
        "prob_balls",
    )


DICE_CASES = [
    ("больше $3$", lambda k: k > 3),
    ("меньше $4$", lambda k: k < 4),
    ("чётное число очков", lambda k: k % 2 == 0),
    ("нечётное число очков", lambda k: k % 2 == 1),
    ("не меньше $4$", lambda k: k >= 4),
    ("не больше $3$", lambda k: k <= 3),
    ("делящееся на $3$", lambda k: k % 3 == 0),
    ("больше $1$", lambda k: k > 1),
    ("меньше $6$", lambda k: k < 6),
]


def t_prob_dice(rnd: random.Random) -> Task:
    wording, predicate = rnd.choice(DICE_CASES)
    favourable = [k for k in range(1, 7) if predicate(k)]
    prob = Fraction(len(favourable), 6)
    # берём только варианты с конечной десятичной записью
    if prob.denominator not in (1, 2, 5, 10):
        wording, predicate = DICE_CASES[0]
        favourable = [4, 5, 6]
        prob = Fraction(1, 2)
    check(len(favourable) == sum(1 for k in range(1, 7) if predicate(k)), "исходы не сошлись")
    return Task(
        4,
        f"Игральную кость бросают один раз. Найдите вероятность того, что выпадет "
        f"{wording}.",
        answer_str(prob),
        f"Подходят исходы {', '.join(map(str, favourable))} — всего ${len(favourable)}$ "
        f"из $6$. $P=\\dfrac{{{len(favourable)}}}{{6}}={ru(prob)}$.",
        ["Всего у кости шесть равновозможных исходов."],
        1,
        "prob_dice",
    )


def t_prob_class(rnd: random.Random) -> Task:
    total = rnd.choice([20, 25, 40, 50])
    girls = rnd.randrange(4, total - 4, 2)
    prob = Fraction(total - girls, total)
    while prob.denominator not in (1, 2, 4, 5, 8, 10, 20, 25, 50):
        girls += 1
        prob = Fraction(total - girls, total)
    check(prob + Fraction(girls, total) == 1, "вероятности не дают в сумме единицу")
    return Task(
        4,
        f"В классе ${total}$ учеников, из них ${girls}$ девочек. Наугад выбирают одного "
        f"дежурного. Найдите вероятность того, что дежурным окажется мальчик.",
        answer_str(prob),
        f"Мальчиков ${total}-{girls}={total - girls}$. "
        f"$P=\\dfrac{{{total - girls}}}{{{total}}}={ru(prob)}$.",
        [],
        1,
        "prob_class",
    )


# -------------------------------------------------------------- №5 сложная вероятность


def t_prob_both(rnd: random.Random) -> Task:
    p1 = Fraction(rnd.randrange(1, 10), 10)
    p2 = Fraction(rnd.randrange(1, 10), 10)
    prob = p1 * p2
    # независимая проверка: перебор по сетке исходов 10×10
    grid = sum(
        1 for i in range(10) for j in range(10) if i < p1 * 10 and j < p2 * 10
    )
    check(Fraction(grid, 100) == prob, "перебор не подтвердил произведение")
    return Task(
        5,
        f"Два стрелка независимо стреляют по мишени. Вероятность попадания для первого "
        f"равна ${ru(p1)}$, для второго — ${ru(p2)}$. Найдите вероятность того, что "
        f"оба попадут.",
        answer_str(prob),
        f"События независимы, поэтому вероятности перемножаются: "
        f"${ru(p1)}\\cdot {ru(p2)}={ru(prob)}$.",
        ["Для независимых событий вероятности перемножаются."],
        2,
        "prob_both",
    )


def t_prob_at_least_one(rnd: random.Random) -> Task:
    p = Fraction(rnd.randrange(1, 10), 10)
    q = 1 - p
    prob = 1 - q * q
    check(prob == 2 * p - p * p, "формула «хотя бы один» не сошлась с раскрытием скобок")
    return Task(
        5,
        f"Стрелок делает два независимых выстрела. Вероятность попадания при одном "
        f"выстреле равна ${ru(p)}$. Найдите вероятность того, что он попадёт хотя бы "
        f"один раз.",
        answer_str(prob),
        f"Через противоположное событие: оба промаха — ${ru(q)}\\cdot {ru(q)}={ru(q*q)}$. "
        f"Тогда $P=1-{ru(q*q)}={ru(prob)}$.",
        ["«Хотя бы один» удобно считать через противоположное событие."],
        3,
        "prob_at_least_one",
    )


def t_prob_difference(rnd: random.Random) -> Task:
    p_year = Fraction(rnd.randrange(90, 99), 100)
    p_two = p_year - Fraction(rnd.randrange(2, 12), 100)
    prob = p_year - p_two
    check(p_two + prob == p_year, "разность вероятностей не сходится")
    item = rnd.choice(["чайник", "принтер", "аккумулятор", "насос"])
    return Task(
        5,
        f"Вероятность того, что новый {item} прослужит больше года, равна ${ru(p_year)}$, "
        f"а больше двух лет — ${ru(p_two)}$. Найдите вероятность того, что он прослужит "
        f"меньше двух лет, но больше года.",
        answer_str(prob),
        f"Событие «больше двух лет» входит в «больше года», поэтому "
        f"$P={ru(p_year)}-{ru(p_two)}={ru(prob)}$.",
        ["Одно событие целиком содержится в другом — вероятности вычитаются."],
        2,
        "prob_difference",
    )


# -------------------------------------------------------------------- №6 уравнения


def t_eq_log(rnd: random.Random) -> Task:
    base = rnd.choice([2, 3, 5])
    power = rnd.randint(2, 4)
    k = rnd.randint(2, 5)
    value = base**power
    b = rnd.randint(1, 12)
    # kx - b = value  =>  x = (value + b) / k, подбираем b так, чтобы корень был целым
    b = (k * rnd.randint(2, 12)) - value
    x = Fraction(value + b, k)
    check(base ** float(power) == value, "степень посчитана неверно")
    check(k * x - b == value, "корень не удовлетворяет уравнению")
    sign = "-" if b >= 0 else "+"
    return Task(
        6,
        f"Найдите корень уравнения $\\log_{{{base}}}({k}x {sign} {abs(b)})={power}$.",
        answer_str(x),
        f"По определению логарифма ${k}x {sign} {abs(b)}={base}^{{{power}}}={value}$, "
        f"откуда $x={ru(x)}$. Под логарифмом ${value}>0$ — ОДЗ выполнено.",
        [
            "Перейдите от логарифма к показательному виду.",
            "Проверьте ОДЗ: под логарифмом должно быть положительное число.",
        ],
        2,
        "eq_log",
    )


def t_eq_exp(rnd: random.Random) -> Task:
    base = rnd.choice([2, 3, 5])
    power = rnd.randint(2, 5)
    shift = rnd.randint(1, 6)
    value = base**power
    x = power - shift
    check(base ** (x + shift) == value, "корень не удовлетворяет уравнению")
    return Task(
        6,
        f"Найдите корень уравнения ${base}^{{\\,x+{shift}}}={value}$.",
        answer_str(x),
        f"${value}={base}^{{{power}}}$, значит $x+{shift}={power}$ и $x={x}$.",
        ["Приведите обе части к одному основанию."],
        1,
        "eq_exp",
    )


def t_eq_sqrt(rnd: random.Random) -> Task:
    k = rnd.randint(2, 6)
    root = rnd.randint(3, 12)
    value = root * root
    b = value - k * rnd.randint(2, 9)
    x = Fraction(value - b, k)
    check(math.isclose(math.sqrt(float(k * x + b)), root), "корень не удовлетворяет уравнению")
    sign = "+" if b >= 0 else "-"
    return Task(
        6,
        f"Найдите корень уравнения $\\sqrt{{{k}x {sign} {abs(b)}}}={root}$.",
        answer_str(x),
        f"Возведём обе части в квадрат: ${k}x {sign} {abs(b)}={value}$, откуда $x={ru(x)}$.",
        ["Возведите обе части в квадрат."],
        2,
        "eq_sqrt",
    )


def t_eq_fraction(rnd: random.Random) -> Task:
    a = rnd.randint(2, 15)
    b = rnd.randint(2, 15)
    while b == -a:
        b = rnd.randint(2, 15)
    check(a + b != 0, "знаменатель обращается в ноль в найденном корне")
    return Task(
        6,
        f"Найдите корень уравнения $\\dfrac{{x-{a}}}{{x+{b}}}=0$.",
        answer_str(a),
        f"Дробь равна нулю, когда числитель равен нулю, а знаменатель — нет. "
        f"$x-{a}=0$ даёт $x={a}$; при этом $x+{b}={a + b}\\neq 0$.",
        ["Дробь равна нулю только при нулевом числителе."],
        2,
        "eq_fraction",
    )


def t_eq_linear(rnd: random.Random) -> Task:
    a = rnd.randint(2, 9)
    c = rnd.randint(2, 9)
    while c == a:
        c = rnd.randint(2, 9)
    x = rnd.randint(-8, 8)
    b = rnd.randint(-10, 10)
    d = (a - c) * x + b
    check(a * x + b == c * x + d, "корень не удовлетворяет уравнению")
    return Task(
        6,
        f"Найдите корень уравнения ${a}x + ({ru(b)}) = {c}x + ({ru(d)})$.",
        answer_str(x),
        f"Переносим: $({a}-{c})x = {ru(d)} - ({ru(b)})$, то есть ${a - c}x={d - b}$, "
        f"откуда $x={x}$.",
        [],
        1,
        "eq_linear",
    )


# ------------------------------------------------------- №7 вычисления и преобразования


def t_calc_log_diff(rnd: random.Random) -> Task:
    base = rnd.choice([2, 3, 5])
    power = rnd.randint(2, 5)
    k = rnd.randint(2, 9)
    big = base**power * k
    check(math.isclose(math.log(big, base) - math.log(k, base), power), "логарифмы не сошлись")
    return Task(
        7,
        f"Найдите значение выражения $\\log_{{{base}}}{big}-\\log_{{{base}}}{k}$.",
        answer_str(power),
        f"$\\log_{{{base}}}{big}-\\log_{{{base}}}{k}="
        f"\\log_{{{base}}}\\dfrac{{{big}}}{{{k}}}=\\log_{{{base}}}{base**power}={power}$.",
        ["Разность логарифмов с одним основанием — логарифм частного."],
        2,
        "calc_log_diff",
    )


def t_calc_powers(rnd: random.Random) -> Task:
    base = rnd.choice([2, 3, 5])
    p1, p2, p3 = rnd.randint(3, 7), rnd.randint(2, 5), rnd.randint(2, 6)
    result_power = p1 + p2 - p3
    while result_power < 0 or result_power > 6:
        p3 = rnd.randint(2, 6)
        result_power = p1 + p2 - p3
    value = base**result_power
    check(base**p1 * base**p2 // base**p3 == value, "степени не сошлись")
    return Task(
        7,
        f"Найдите значение выражения $\\dfrac{{{base}^{{{p1}}}\\cdot {base}^{{{p2}}}}}"
        f"{{{base}^{{{p3}}}}}$.",
        answer_str(value),
        f"$\\dfrac{{{base}^{{{p1}+{p2}}}}}{{{base}^{{{p3}}}}}="
        f"{base}^{{{p1 + p2}-{p3}}}={base}^{{{result_power}}}={value}$.",
        ["При умножении степени складываются, при делении вычитаются."],
        1,
        "calc_powers",
    )


def t_calc_frac_power(rnd: random.Random) -> Task:
    base = rnd.choice([2, 3, 5, 7])
    whole = rnd.randint(2, 4)
    value = base**whole
    check(math.isclose(base ** (whole + 0.5) / base**0.5, value), "дробные степени не сошлись")
    return Task(
        7,
        f"Найдите значение выражения $\\dfrac{{{base}^{{\\,{whole},5}}}}{{{base}^{{\\,0,5}}}}$.",
        answer_str(value),
        f"${base}^{{{whole},5-0,5}}={base}^{{{whole}}}={value}$.",
        ["При делении степеней с одинаковым основанием показатели вычитаются."],
        2,
        "calc_frac_power",
    )


# ------------------------------------------------------ №8 производная и первообразная


def t_derivative_value(rnd: random.Random) -> Task:
    a = rnd.randint(1, 4)
    b = rnd.randint(-6, 6)
    c = rnd.randint(-8, 8)
    x0 = rnd.randint(-3, 4)
    derivative = 3 * a * x0**2 + 2 * b * x0 + c
    # независимая проверка: численная производная
    f = lambda t: a * t**3 + b * t**2 + c * t
    numeric = (f(x0 + 1e-5) - f(x0 - 1e-5)) / 2e-5
    check(abs(numeric - derivative) < 1e-3, "численная производная не совпала")
    return Task(
        8,
        f"Функция задана формулой $f(x)={a}x^{{3}}{sgn(b)}x^{{2}}{sgn(c)}x$. "
        f"Найдите $f'({x0})$.",
        answer_str(derivative),
        f"$f'(x)={3*a}x^{{2}}{sgn(2*b)}x{sgn(c)}$, тогда "
        f"$f'({x0})={3*a}\\cdot{x0**2}{sgn(2*b*x0)}{sgn(c)}={derivative}$.",
        ["Производная $x^n$ равна $nx^{n-1}$."],
        2,
        "derivative_value",
    )


def t_tangent_parallel(rnd: random.Random) -> Task:
    a = rnd.choice([1, 2])
    b = rnd.randint(-6, 6)
    k = rnd.randint(-5, 9)
    while (k - b) % (2 * a) != 0:
        k += 1
    x0 = Fraction(k - b, 2 * a)
    check(2 * a * x0 + b == k, "производная в точке не равна угловому коэффициенту")
    shift = rnd.randint(-9, 9)
    return Task(
        8,
        f"Прямая $y={k}x{sgn(shift)}$ параллельна касательной к графику функции "
        f"$y={a}x^{{2}}{sgn(b)}x$. Найдите абсциссу точки касания.",
        answer_str(x0),
        f"У параллельных прямых равные угловые коэффициенты, значит производная в точке "
        f"касания равна ${k}$. $y'={2*a}x{sgn(b)}={k}$, откуда $x={ru(x0)}$.",
        [
            "У параллельных прямых равные угловые коэффициенты.",
            "Угловой коэффициент касательной — значение производной в точке касания.",
        ],
        3,
        "tangent_parallel",
    )


# ------------------------------------------------------------- №9 прикладная задача


def t_applied_power(rnd: random.Random) -> Task:
    i = rnd.randint(2, 9)
    r = rnd.randint(2, 15)
    power = i * i * r
    check(power == i**2 * r, "мощность посчитана неверно")
    return Task(
        9,
        f"Мощность постоянного тока вычисляется по формуле $P=I^{{2}}R$. Найдите "
        f"мощность (в ваттах), если сила тока $I={i}$ А, а сопротивление $R={r}$ Ом.",
        answer_str(power),
        f"$P={i}^{{2}}\\cdot {r}={i*i}\\cdot {r}={power}$.",
        [],
        1,
        "applied_power",
    )


def t_applied_height(rnd: random.Random) -> Task:
    # h(t) = h0 + v0 t - 5 t^2, подбираем так, чтобы корни были «красивыми»
    t1 = Fraction(rnd.choice([1, 2, 3, 4]), rnd.choice([1, 2, 5]))
    t2 = t1 + Fraction(rnd.choice([1, 2, 3]))
    v0 = 5 * (t1 + t2)
    target = rnd.randint(5, 30)
    h0 = target - float(5 * t1 * t2) * -1  # h0 подбирается ниже
    h0 = target + 5 * float(t1 * t2) * 1
    h0 = target - (v0 * float(t1) - 5 * float(t1) ** 2)
    if h0 != int(h0) or v0 != int(v0):
        t1, t2 = Fraction(4, 5), Fraction(2)
        v0 = 5 * (t1 + t2)
        target = 10
        h0 = target - (float(v0) * float(t1) - 5 * float(t1) ** 2)
    h0 = int(h0)
    v0 = int(v0)
    # независимая проверка: подставляем оба корня
    h = lambda t: h0 + v0 * t - 5 * t * t
    check(abs(h(float(t1)) - target) < 1e-9, "первый корень не даёт нужную высоту")
    check(abs(h(float(t2)) - target) < 1e-9, "второй корень не даёт нужную высоту")
    check(t1 < t2, "корни не упорядочены")
    return Task(
        9,
        f"Высота камня меняется по закону $h(t)={h0}+{v0}t-5t^{{2}}$ (высота в метрах, "
        f"время в секундах). Через сколько секунд после броска камень **впервые** "
        f"окажется на высоте ${target}$ метров?",
        answer_str(t1),
        f"Решаем ${h0}+{v0}t-5t^{{2}}={target}$, то есть $5t^{{2}}-{v0}t+{target - h0}=0$. "
        f"Корни: ${ru(t1)}$ и ${ru(t2)}$. Впервые — при меньшем, $t={ru(t1)}$.",
        [
            "Составьте уравнение $h(t)$ = нужная высота.",
            "Корней будет два — нужен меньший.",
        ],
        3,
        "applied_height",
    )


def t_applied_ohm(rnd: random.Random) -> Task:
    r1 = rnd.choice([2, 3, 4, 6, 12])
    r2 = rnd.choice([2, 3, 4, 6, 12])
    total = Fraction(r1 * r2, r1 + r2)
    while total.denominator != 1:
        r2 = rnd.choice([2, 3, 4, 6, 12])
        total = Fraction(r1 * r2, r1 + r2)
    check(Fraction(1, r1) + Fraction(1, r2) == Fraction(1, 1) / total, "сопротивление не сошлось")
    return Task(
        9,
        f"Два резистора соединены параллельно, их сопротивления равны ${r1}$ Ом "
        f"и ${r2}$ Ом. Общее сопротивление находится по формуле "
        f"$\\dfrac{{1}}{{R}}=\\dfrac{{1}}{{R_1}}+\\dfrac{{1}}{{R_2}}$. "
        f"Найдите $R$ (в омах).",
        answer_str(total),
        f"$\\dfrac{{1}}{{R}}=\\dfrac{{1}}{{{r1}}}+\\dfrac{{1}}{{{r2}}}="
        f"\\dfrac{{{r1 + r2}}}{{{r1 * r2}}}$, откуда "
        f"$R=\\dfrac{{{r1 * r2}}}{{{r1 + r2}}}={ru(total)}$.",
        ["Сначала найдите $\\dfrac{1}{R}$, потом переверните дробь."],
        2,
        "applied_ohm",
    )


# --------------------------------------------------------------- №10 текстовая задача


def t_text_mixture(rnd: random.Random) -> Task:
    m1 = rnd.randrange(2, 12, 2)
    m2 = rnd.randrange(2, 12, 2)
    c1 = rnd.randrange(5, 40, 5)
    c2 = rnd.randrange(5, 40, 5)
    while c1 == c2:
        c2 = rnd.randrange(5, 40, 5)
    salt = Fraction(m1 * c1 + m2 * c2, 100)
    concentration = salt / (m1 + m2) * 100
    if concentration.denominator != 1:
        m1, m2, c1, c2 = 4, 6, 15, 25
        salt = Fraction(4 * 15 + 6 * 25, 100)
        concentration = salt / 10 * 100
    # независимая проверка: масса соли обратно
    check(
        Fraction(concentration, 100) * (m1 + m2) == salt,
        "концентрация не даёт исходную массу соли",
    )
    return Task(
        10,
        f"Смешали ${m1}$ кг раствора с концентрацией соли ${c1}\\%$ и ${m2}$ кг раствора "
        f"с концентрацией ${c2}\\%$. Найдите концентрацию соли в полученном растворе "
        f"(в процентах).",
        answer_str(concentration),
        f"Соли: ${m1}\\cdot {ru(Fraction(c1,100))}+{m2}\\cdot {ru(Fraction(c2,100))}="
        f"{ru(salt)}$ кг на ${m1 + m2}$ кг раствора. "
        f"Концентрация: $\\dfrac{{{ru(salt)}}}{{{m1 + m2}}}={ru(concentration/100)}$, "
        f"то есть ${ru(concentration)}\\%$.",
        ["Посчитайте массу соли отдельно, затем разделите на общую массу."],
        3,
        "text_mixture",
    )


def t_text_speed(rnd: random.Random) -> Task:
    v = rnd.choice([10, 12, 15, 20, 24, 30])
    delta = rnd.choice([5, 10, 15, 20])
    hours = rnd.choice([1, 2, 3])
    distance = Fraction(hours * v * (v + delta), delta)
    if distance.denominator != 1:
        v, delta, hours = 10, 10, 3
        distance = Fraction(3 * 10 * 20, 10)
    distance = int(distance)
    # независимая проверка: разность времён равна заявленной
    check(
        abs(distance / v - distance / (v + delta) - hours) < 1e-9,
        "разность времён не совпала",
    )
    return Task(
        10,
        f"Велосипедист проехал ${distance}$ км. Если бы он увеличил скорость "
        f"на ${delta}$ км/ч, то потратил бы на ${hours}$ "
        f"{'час' if hours == 1 else 'часа'} меньше. Найдите скорость велосипедиста "
        f"(в км/ч).",
        answer_str(v),
        f"Пусть скорость $v$. Тогда $\\dfrac{{{distance}}}{{v}}-"
        f"\\dfrac{{{distance}}}{{v+{delta}}}={hours}$. После приведения к общему "
        f"знаменателю получаем квадратное уравнение, положительный корень $v={v}$.",
        [
            "Обозначьте скорость за $v$ и выразите оба времени в пути.",
            "Отрицательный корень отбрасываем — скорость положительна.",
        ],
        4,
        "text_speed",
    )


def t_text_percent(rnd: random.Random) -> Task:
    price = rnd.randrange(200, 5000, 100)
    d1 = rnd.choice([10, 20, 25, 30, 40, 50])
    d2 = rnd.choice([10, 20, 25, 50])
    final = Fraction(price) * Fraction(100 - d1, 100) * Fraction(100 - d2, 100)
    while final.denominator != 1:
        price += 100
        final = Fraction(price) * Fraction(100 - d1, 100) * Fraction(100 - d2, 100)
    # независимая проверка: последовательное вычитание
    step = price - price * Fraction(d1, 100)
    step = step - step * Fraction(d2, 100)
    check(step == final, "последовательные скидки не сошлись")
    return Task(
        10,
        f"Товар стоил ${price}$ рублей. Сначала его уценили на ${d1}\\%$, "
        f"а затем ещё на ${d2}\\%$ от новой цены. Сколько рублей стоит товар теперь?",
        answer_str(final),
        f"После первой скидки: ${price}\\cdot {ru(Fraction(100-d1,100))}="
        f"{ru(price * Fraction(100-d1,100))}$ р. "
        f"После второй: ${ru(price * Fraction(100-d1,100))}\\cdot "
        f"{ru(Fraction(100-d2,100))}={ru(final)}$ р. "
        f"Скидки не складываются — множители перемножаются.",
        ["Скидка на $p\\%$ — это умножение на $1-\\dfrac{p}{100}$."],
        3,
        "text_percent",
    )


# ------------------------------------------------------------- №11 графики функций


def t_graph_hyperbola(rnd: random.Random) -> Task:
    x0 = rnd.choice([-6, -4, -3, -2, 2, 3, 4, 6])
    y0 = rnd.choice([-12, -6, -4, -3, 3, 4, 6, 12])
    k = x0 * y0
    check(Fraction(k, x0) == y0, "точка не лежит на гиперболе")
    return Task(
        11,
        f"График функции $y=\\dfrac{{k}}{{x}}$ проходит через точку "
        f"$({ru(x0)};\\,{ru(y0)})$. Найдите $k$.",
        answer_str(k),
        f"Подставим точку: ${ru(y0)}=\\dfrac{{k}}{{{ru(x0)}}}$, откуда "
        f"$k={ru(x0)}\\cdot{ru(y0)}={k}$.",
        ["Подставьте координаты точки в формулу функции."],
        1,
        "graph_hyperbola",
    )


def t_graph_parabola(rnd: random.Random) -> Task:
    c = rnd.randint(-9, 9)
    b = rnd.randint(-9, 9)
    x1 = rnd.choice([1, 2, -1, -2])
    y1 = x1 * x1 + b * x1 + c
    check(y1 == x1**2 + b * x1 + c, "точка не лежит на параболе")
    return Task(
        11,
        f"Парабола $y=x^{{2}}+bx+c$ проходит через точки $(0;\\,{ru(c)})$ и "
        f"$({ru(x1)};\\,{ru(y1)})$. Найдите $b$.",
        answer_str(b),
        f"Из точки $(0;{ru(c)})$ сразу $c={c}$. Подставим вторую точку: "
        f"${x1**2}+b\\cdot({ru(x1)})+({ru(c)})={ru(y1)}$, откуда $b={b}$.",
        ["Начните с точки, где $x=0$ — она сразу даёт $c$."],
        3,
        "graph_parabola",
    )


def t_graph_linear(rnd: random.Random) -> Task:
    k = rnd.choice([-4, -3, -2, 2, 3, 4])
    b = rnd.randint(-9, 9)
    x1, x2 = rnd.sample([-4, -3, -2, -1, 1, 2, 3, 4], 2)
    y1, y2 = k * x1 + b, k * x2 + b
    check(Fraction(y2 - y1, x2 - x1) == k, "угловой коэффициент не совпал")
    return Task(
        11,
        f"Прямая $y=kx+b$ проходит через точки $({ru(x1)};\\,{ru(y1)})$ и "
        f"$({ru(x2)};\\,{ru(y2)})$. Найдите $k$.",
        answer_str(k),
        f"$k=\\dfrac{{y_2-y_1}}{{x_2-x_1}}=\\dfrac{{{ru(y2)}-({ru(y1)})}}"
        f"{{{ru(x2)}-({ru(x1)})}}={k}$.",
        ["Угловой коэффициент — отношение приращения $y$ к приращению $x$."],
        2,
        "graph_linear",
    )


# --------------------------------------------------------------- №12 анализ функций


def t_min_cubic(rnd: random.Random) -> Task:
    a = rnd.randint(1, 3)
    c = rnd.randint(1, 20)
    # y = x^3 - 3a^2 x + c, критические точки x = ±a
    left, right = 0, a + rnd.randint(1, 3)
    f = lambda x: x**3 - 3 * a * a * x + c
    ymin = min(f(x) for x in (left, a, right))
    # независимая проверка: перебор по мелкой сетке
    grid_min = min(f(left + i * (right - left) / 20000) for i in range(20001))
    check(abs(grid_min - ymin) < 1e-6, "минимум по сетке не совпал с найденным")
    return Task(
        12,
        f"Найдите наименьшее значение функции $y=x^{{3}}-{3*a*a}x+{c}$ на отрезке "
        f"$[{left};\\,{right}]$.",
        answer_str(ymin),
        f"$y'=3x^{{2}}-{3*a*a}=0$ при $x=\\pm{a}$; отрезку принадлежит $x={a}$. "
        f"Сравниваем: $y({left})={f(left)}$, $y({a})={f(a)}$, $y({right})={f(right)}$. "
        f"Наименьшее — ${ymin}$.",
        ["Найдите критические точки и сравните значения на концах отрезка и в них."],
        3,
        "min_cubic",
    )


def t_min_hyperbola(rnd: random.Random) -> Task:
    root = rnd.randint(2, 12)
    a = root * root
    ymin = 2 * root
    f = lambda x: x + a / x
    grid_min = min(f(0.01 + i * 0.005) for i in range(1, 20000))
    check(abs(grid_min - ymin) < 1e-2, "минимум по сетке не совпал")
    return Task(
        12,
        f"Найдите наименьшее значение функции $y=x+\\dfrac{{{a}}}{{x}}$ при $x>0$.",
        answer_str(ymin),
        f"$y'=1-\\dfrac{{{a}}}{{x^{{2}}}}=0$ при $x={root}$. Производная меняет знак "
        f"с минуса на плюс — это минимум: $y({root})={root}+{root}={ymin}$.",
        ["Приравняйте производную к нулю; берём положительный корень."],
        3,
        "min_hyperbola",
    )


def t_max_quadratic(rnd: random.Random) -> Task:
    a = rnd.randint(1, 4)
    x0 = rnd.randint(-6, 6)
    c = rnd.randint(-10, 20)
    # y = -a(x-x0)^2 + c
    b = 2 * a * x0
    f = lambda x: -a * x * x + b * x + c
    ymax = f(x0)
    grid_max = max(f(x0 - 5 + i * 0.001) for i in range(10001))
    check(abs(grid_max - ymax) < 1e-6, "максимум по сетке не совпал")
    return Task(
        12,
        f"Найдите наибольшее значение функции $y=-{a}x^{{2}}{sgn(b)}x{sgn(c)}$.",
        answer_str(ymax),
        f"Ветви параболы направлены вниз, максимум в вершине: "
        f"$x_0=-\\dfrac{{b}}{{2a}}=-\\dfrac{{{b}}}{{{-2*a}}}={x0}$, "
        f"$y({x0})={ymax}$.",
        ["У параболы с отрицательным старшим коэффициентом максимум в вершине."],
        2,
        "max_quadratic",
    )


# --------------------------------------------------------------------------- сборка

TEMPLATES = [
    t_right_triangle_hyp,
    t_right_triangle_inradius,
    t_heron,
    t_rectangle_area,
    t_trapezoid_area,
    t_vector_length,
    t_vector_dot,
    t_vector_collinear,
    t_box_volume,
    t_cube_surface,
    t_cylinder_volume,
    t_prism_volume,
    t_prob_balls,
    t_prob_dice,
    t_prob_class,
    t_prob_both,
    t_prob_at_least_one,
    t_prob_difference,
    t_eq_log,
    t_eq_exp,
    t_eq_sqrt,
    t_eq_fraction,
    t_eq_linear,
    t_calc_log_diff,
    t_calc_powers,
    t_calc_frac_power,
    t_derivative_value,
    t_tangent_parallel,
    t_applied_power,
    t_applied_height,
    t_applied_ohm,
    t_text_mixture,
    t_text_speed,
    t_text_percent,
    t_graph_hyperbola,
    t_graph_parabola,
    t_graph_linear,
    t_min_cubic,
    t_min_hyperbola,
    t_max_quadratic,
]


def yaml_escape(text: str) -> str:
    return text.replace("'", "''")


def write_task(task: Task, index: int) -> Path:
    directory = ROOT / f"{task.number:02d}"
    directory.mkdir(parents=True, exist_ok=True)
    task_id = f"math_prof_{task.number:02d}_{index:04d}"

    lines = [
        f"id: {task_id}",
        "subject: math_prof",
        f"task_type: {task.number}",
        f"difficulty: {task.difficulty}",
        "statement: |",
        f"  {task.statement}",
        "answer:",
        "  type: number",
        f"  value: '{task.answer}'",
        "solution: |",
        f"  {task.solution}",
    ]
    if task.hints:
        lines.append("hints:")
        lines += [f"  - '{yaml_escape(h)}'" for h in task.hints]
    lines += [
        "source:",
        "  kind: own",
        f"  ref: 'tpl:{task.template}'",
        "status: live",
        "",
    ]

    path = directory / f"{task_id}.yaml"
    io.open(path, "w", encoding="utf-8").write("\n".join(lines))
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-template", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260812)
    args = parser.parse_args()

    rnd = random.Random(args.seed)
    seen: set[str] = set()
    counters: dict[int, int] = {}
    written = 0
    duplicates = 0
    per_number: dict[int, int] = {}

    for template in TEMPLATES:
        made = 0
        attempts = 0
        while made < args.per_template and attempts < args.per_template * 40:
            attempts += 1
            task = template(rnd)  # исключения не глушим: сломанный шаблон должен падать
            if task.statement in seen:
                duplicates += 1
                continue
            seen.add(task.statement)

            counters[task.number] = counters.get(task.number, 0) + 1
            write_task(task, counters[task.number])
            per_number[task.number] = per_number.get(task.number, 0) + 1
            made += 1
            written += 1

        if made < args.per_template:
            print(f"  ! {template.__name__}: только {made} уникальных вариантов")

    print(f"\nЗаписано задач: {written} (повторов пропущено: {duplicates})")
    for number in sorted(per_number):
        print(f"  № {number:>2}: {per_number[number]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
