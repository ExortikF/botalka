"""Решение задач ФИПИ с двойной проверкой ответа.

    tools/.venv/bin/python tools/fipi_solve.py --dry     # посчитать, ничего не писать
    tools/.venv/bin/python tools/fipi_solve.py           # записать ответы в черновики

Открытый банк не отдаёт ответы, поэтому их считаем сами. Правило здесь одно и
оно жёсткое: **ответ принимается, только если он получен двумя независимыми
способами и они совпали**. Символьное решение проверяется численно — подстановкой
в исходное условие, перебором или сканированием окрестности. Если способы
разошлись или второй способ неприменим, ответ не проставляется и задача остаётся
черновиком. Лучше пустая задача, чем задача с неверным ключом: неверный ключ
ученик воспринимает как «тренажёр врёт», и это не чинится извинениями.

Считаем не всё подряд, а три семейства, где символьная математика надёжна:
  №6  «Найдите корень уравнения …»
  №7  «Найдите значение выражения …»
  №12 «Найдите точку минимума/максимума …», «наибольшее/наименьшее значение …»

Ответ части 1 — всегда целое число или конечная десятичная дробь. Всё, что не
приводится к такому виду, отбраковывается: это верный признак, что условие
разобрано неправильно.
"""

from __future__ import annotations

import argparse
import json
import re
import signal
from contextlib import contextmanager
from pathlib import Path

import fipi_geometry
import sympy
from sympy import Symbol, nsimplify
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    rationalize,
    standard_transformations,
)

ROOT = Path(__file__).resolve().parent.parent

X = Symbol("x", real=True)

# rationalize обязателен: без него «6,4» становится float, точность теряется уже
# на первом шаге и ответ приезжает в виде 6,0000000000000001268.
TRANSFORMS = standard_transformations + (rationalize, implicit_multiplication_application)

# Погрешности: символьный и численный ответы должны совпадать с большим запасом
EPS_MATCH = 1e-9
EPS_ZERO = 1e-7


# Ограничение на задачу. Без него sympy может думать над одним трансцендентным
# уравнением дольше, чем над всем банком: solve не обязан завершаться быстро.
TASK_SECONDS = 8


class Timeout(Exception):
    pass


@contextmanager
def time_limit(seconds: int):
    def ring(signum, frame):
        raise Timeout()

    previous = signal.signal(signal.SIGALRM, ring)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


# --------------------------------------------------------------------- LaTeX → sympy


def tex_to_sympy(tex: str) -> sympy.Expr:
    """Перевод куска LaTeX из условия в выражение sympy.

    Полноценный парсер LaTeX здесь не нужен и вреден: чем шире он понимает, тем
    охотнее «понимает» неправильно. Поддерживаем ровно то, что встречается в
    части 1, а на всём остальном честно падаем — задача уйдёт в ручные.
    """
    s = tex.strip()

    # Невидимые символы из банка: узкий и неразрывный пробел, zero-width.
    for junk in ("\u200b", "\u00a0", "\u2009", "\u2062", "\u2061"):
        s = s.replace(junk, "")

    s = s.replace("\\left", "").replace("\\right", "").replace("\\,", " ")
    s = s.replace("−", "-").replace("–", "-").replace("⋅", "*").replace("·", "*")
    s = s.replace("\\cdot", "*").replace("\\times", "*")

    # хвостовая точка предложения внутрь формулы попадает часто
    s = s.rstrip(". ,;")

    # десятичная запятая: 0,5 → 0.5
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)

    while "\\frac" in s:
        s, count = re.subn(
            r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"((\1)/(\2))", s, count=1
        )
        if not count:
            break

    s = re.sub(r"\\sqrt\s*\[\s*(\d+)\s*\]\s*\{([^{}]*)\}", r"((\2)**(1/(\1)))", s)
    while "\\sqrt" in s:
        s, count = re.subn(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt(\1)", s, count=1)
        if not count:
            break

    # Логарифм с основанием. Пробел после \log в банке встречается постоянно:
    # «\log _{5}(8-x)», поэтому \s* обязателен во всех вариантах.
    s = re.sub(r"\\log\s*_\s*\{([^{}]+)\}\s*\(([^()]+)\)", r"log((\2),(\1))", s)
    s = re.sub(r"\\log\s*_\s*\{([^{}]+)\}\s*([\d\.]+|[a-z])", r"log((\2),(\1))", s)
    s = re.sub(r"\\log\s*_\s*(\d+)\s*\(([^()]+)\)", r"log((\2),(\1))", s)
    s = re.sub(r"\\log\s*_\s*(\d+)\s*([\d\.]+|[a-z])", r"log((\2),(\1))", s)

    # Функция без скобок: «\sin 51», «\ln x». Аргументом считаем первый
    # неразрывный кусок — этого хватает, а на сложном разбор честно упадёт.
    names = {"sin": "sin", "cos": "cos", "tg": "tan", "ctg": "cot",
             "ln": "log", "lg": "log10_", "arcsin": "asin", "arccos": "acos"}

    # Скобочная группа с одним уровнем вложенности — этого хватает: к этому
    # моменту \frac уже развёрнут в ((a)/(b)).
    GROUP = r"\((?:[^()]|\([^()]*\))*\)"

    for tex_name, py_name in names.items():
        # «\ln (x+9)^{5}» в ЕГЭ означает ln((x+9)^5), а не (ln(x+9))^5.
        # Без этого правила ответ получается неверным, причём двойная проверка
        # его не поймает: обе дороги считают одно и то же неправильно понятое
        # выражение.
        s = re.sub(
            r"\\" + tex_name + r"\s*(" + GROUP + r")\s*\^\s*\{?(\d+)\}?",
            lambda m, f=py_name: f"{f}(({m.group(1)})**{m.group(2)})",
            s,
        )
        # «\cos ^{2}x» — степень стоит перед аргументом и относится к значению
        # функции: (cos x)^2.
        s = re.sub(
            r"\\" + tex_name + r"\s*\^\s*\{?(\d+)\}?\s*(" + GROUP + r"|[A-Za-z0-9\.]+)",
            lambda m, f=py_name: f"{f}({m.group(2)})**{m.group(1)}",
            s,
        )

    for tex_name, py_name in names.items():
        # сначала «sin 51°» — иначе градус останется снаружи скобок
        s = re.sub(
            r"\\" + tex_name + r"\s*(\d+(?:\.\d+)?)\s*(?:°|\\circ)",
            py_name + r"((\1)*pi/180)",
            s,
        )
        s = re.sub(
            r"\\" + tex_name + r"\s*(\([^()]*\)|[A-Za-z0-9\.]+)",
            py_name + r"(\1)",
            s,
        )

    # оставшиеся градусы — это уже просто числа в условии
    s = re.sub(r"(\d+(?:\.\d+)?)\s*(?:°|\\circ)", r"((\1)*pi/180)", s)

    s = s.replace("\\pi", "pi").replace("π", "pi")
    s = s.replace("^", "**").replace("{", "(").replace("}", ")")

    remains = re.findall(r"\\[a-zA-Z]+", s)
    if remains:
        raise ValueError(f"не знаю команду {remains[0]}")

    local = {
        "x": X,
        "sqrt": sympy.sqrt,
        "log": sympy.log,
        "log10_": lambda a: sympy.log(a, 10),
        "sin": sympy.sin,
        "cos": sympy.cos,
        "tan": sympy.tan,
        "cot": sympy.cot,
        "pi": sympy.pi,
        "e": sympy.E,
    }
    # parse_expr с неявным умножением: в условиях пишут «5x», а не «5*x»
    return parse_expr(
        s,
        local_dict=local,
        transformations=TRANSFORMS,
        evaluate=True,
    )


def as_answer(value) -> str | None:
    """Ответ части 1 — целое или конечная десятичная дробь. Иначе не наш случай."""
    # Крохи от плавающей точки убираем до перевода в дробь: 6.0000000000000001
    # это ответ «6», а не «непредставимое число».
    try:
        approx = float(sympy.N(value, 30))
        if abs(approx - round(approx)) < 1e-9:
            return str(int(round(approx)))
    except Exception:
        pass

    try:
        exact = nsimplify(value, rational=True)
        number = sympy.Rational(exact)
    except Exception:
        try:
            number = sympy.Rational(str(sympy.N(value, 30)))
        except Exception:
            return None

    if number.q == 1:
        return str(number.p)

    decimal = sympy.N(number, 20)
    text = str(decimal).rstrip("0").rstrip(".")
    # Ответ части 1 — короткое число. «9050,9667991878083123» формально
    # конечная дробь, но реально это признак того, что условие разобрано не так.
    if len(text.replace("-", "").replace(".", "")) > 7:
        return None
    # конечная дробь: знаменатель раскладывается только на 2 и 5
    q = number.q
    for divisor in (2, 5):
        while q % divisor == 0:
            q //= divisor
    if q != 1:
        return None
    return text.replace(".", ",")


# --------------------------------------------------------------------- решатели


def log_step(tex: str) -> str | None:
    """Свёртка суммы или разности логарифмов с одинаковым основанием.

    Самый частый вид задания №7, и именно этот шаг человек делает первым:
    $\\log_3 162-\\log_3 2 = \\log_3 81$. Делаем его текстом по исходной записи —
    sympy на этом месте либо молчит, либо выдаёт нечитаемое.
    """
    pattern = r"^\\log\s*_\s*\{?(\w+)\}?\s*([\d\.,]+)\s*([+-])\s*\\log\s*_\s*\{?(\w+)\}?\s*([\d\.,]+)$"
    match = re.match(pattern, tex.strip())
    if not match:
        return None

    base, first, sign, base2, second = match.groups()
    if base != base2:
        return None

    try:
        left = sympy.Rational(first.replace(",", "."))
        right = sympy.Rational(second.replace(",", "."))
    except Exception:
        return None

    inner = left * right if sign == "+" else left / right
    return f"\\log_{{{base}}}{{{sympy.latex(inner)}}}"


def solve_expression(tex: str) -> tuple[str | None, str, str]:
    """№7: «Найдите значение выражения». Проверка — независимый численный счёт."""
    expr = tex_to_sympy(tex)
    if expr.free_symbols:
        return None, "в выражении осталась переменная", ""

    exact = sympy.simplify(expr)
    # вторая, независимая дорога: считаем то же выражение с 40 знаками
    numeric = sympy.N(expr, 40)

    if abs(sympy.N(exact, 40) - numeric) > EPS_MATCH:
        return None, "символьный и численный счёт разошлись", ""

    answer = as_answer(exact)
    if answer is None:
        return None, "ответ не приводится к числу части 1", ""

    # Промежуточный шаг: без него «разбор» сводится к «упростим и вот ответ»,
    # то есть к объявлению ответа. Ищем форму, в которой видно сам приём:
    # свёрнутый логарифм, приведённую тригонометрию, общий знаменатель.
    source = tex.strip().rstrip(".")
    middle = log_step(source)

    if middle is None:
        for transform in (
            lambda e: sympy.logcombine(e, force=True),
            sympy.trigsimp,
            sympy.powsimp,
        ):
            try:
                candidate = transform(expr)
            except Exception:
                continue
            shown = sympy.latex(candidate)
            # Шаг имеет смысл, только если запись стала проще. sympy охотно
            # раскрывает sin 51° в радикалы — такой «разбор» хуже, чем никакого.
            # Появление \pi там, где в условии были градусы, — тоже шаг назад:
            # ученик увидит незнакомую запись вместо привычной.
            radians = "\\pi" in shown and "°" in source
            if (
                shown not in {sympy.latex(expr), sympy.latex(exact)}
                and len(shown) <= len(source)
                and not radians
            ):
                middle = shown
                break

    if not middle:
        # «Упростим выражение: <громоздкая формула> = 7» — это не разбор, а
        # объявление ответа. Такой лучше не показывать вовсе: пустое место
        # честнее имитации объяснения.
        return answer, "символьно + численно", ""

    chain = [source, middle, sympy.latex(exact)]
    return answer, "символьно + численно", "Упростим выражение: $" + " = ".join(chain) + "$."


def equation_hint(left_tex: str, right_tex: str) -> str:
    """Первый шаг разбора — тот, который человек делает в уме.

    Смотрим на исходную запись, а не на представление sympy: sympy раскладывает
    $\\log_5 x$ в $\\log x/\\log 5$, и по такой структуре приём уже не опознать."""
    left, right = left_tex.strip(), right_tex.strip()

    if "\\log" in left and "\\log" in right:
        return "Логарифмы с одинаковым основанием равны, значит равны и их аргументы."
    if "\\log" in left or "\\log" in right:
        return "Перейдём от логарифма к его определению."
    if "\\sqrt" in left or "\\sqrt" in right:
        return "Возведём обе части в степень, которая уберёт корень."
    if "^" in left and "^" in right:
        return "Приведём обе части к одному основанию и приравняем показатели."
    if "^" in left and "x" in left:
        return "Приведём правую часть к тому же основанию и приравняем показатели."
    return "Выразим неизвестное."


def solve_equation(tex: str, pick: str) -> tuple[str | None, str, str]:
    """№6: «Найдите корень уравнения». Проверка — подстановка в исходное."""
    if "=" not in tex:
        return None, "не уравнение", ""

    left_tex, right_tex = tex.split("=", 1)
    left, right = tex_to_sympy(left_tex), tex_to_sympy(right_tex)
    equation = sympy.Eq(left, right)

    roots = [r for r in sympy.solve(equation, X, dict=False) if sympy.N(r, 30).is_real]
    if not roots:
        return None, "корней не нашлось", ""

    # Независимая проверка: подставляем корень в исходное уравнение и смотрим,
    # что левая и правая части численно совпали. Символьное solve тут не участвует.
    checked = []
    for root in roots:
        try:
            residual = abs(sympy.N(left.subs(X, root) - right.subs(X, root), 30))
        except Exception:
            continue
        if residual < EPS_ZERO:
            checked.append(root)

    if not checked:
        return None, "корень не прошёл подстановку", ""

    if len(checked) > 1:
        if pick == "smaller":
            chosen = min(checked, key=lambda r: sympy.N(r))
        elif pick == "larger":
            chosen = max(checked, key=lambda r: sympy.N(r))
        else:
            return None, f"корней {len(checked)}, а в условии не сказано, какой брать", ""
    else:
        chosen = checked[0]

    answer = as_answer(chosen)
    if answer is None:
        return None, "ответ не приводится к числу части 1", ""

    steps = [
        f"${left_tex.strip().rstrip('. ')} = {right_tex.strip().rstrip('. ')}$.",
        equation_hint(left_tex, right_tex),
        f"Получаем $x = {sympy.latex(chosen)}$.",
    ]
    if len(checked) > 1:
        steps.append(
            "Корней несколько: "
            + ", ".join(f"${sympy.latex(r)}$" for r in checked)
            + f" — в ответ идёт {'меньший' if pick == 'smaller' else 'больший'}."
        )
    steps.append(
        "Проверка: подставим найденное значение в исходное уравнение — обе части совпадают."
    )
    return answer, "решено + подстановка", " ".join(steps)


def solve_extremum(tex: str, kind: str) -> tuple[str | None, str, str]:
    """№12: точка минимума/максимума. Проверка — сканирование окрестности."""
    expr = tex_to_sympy(tex)
    if X not in expr.free_symbols:
        return None, "нет переменной x", ""

    derivative = sympy.diff(expr, X)
    points = [p for p in sympy.solve(sympy.Eq(derivative, 0), X, dict=False) if p.is_real]
    if not points:
        return None, "критических точек не нашлось", ""

    good = []
    for point in points:
        value = float(sympy.N(point))
        step = max(abs(value) * 1e-3, 1e-3)
        try:
            here = float(sympy.N(expr.subs(X, point)))
            left = float(sympy.N(expr.subs(X, value - step)))
            right = float(sympy.N(expr.subs(X, value + step)))
        except Exception:
            continue

        # Сканирование — это и есть вторая дорога: производную оно не использует
        if kind == "min" and left > here < right:
            good.append(point)
        if kind == "max" and left < here > right:
            good.append(point)

    if len(good) != 1:
        return None, f"подходящих точек {len(good)}, нужна одна", ""

    answer = as_answer(good[0])
    if answer is None:
        return None, "ответ не приводится к числу части 1", ""

    word = "минимума" if kind == "min" else "максимума"
    steps = [
        f"Найдём производную: $y' = {sympy.latex(sympy.simplify(derivative))}$.",
        "Приравняем её к нулю: "
        + ", ".join(f"$x = {sympy.latex(p)}$" for p in points)
        + ".",
    ]
    if len(points) > 1:
        steps.append(
            f"Из этих точек условию отвечает только $x = {sympy.latex(good[0])}$: "
            "слева и справа от неё функция ведёт себя так, как нужно для "
            f"точки {word}."
        )
    else:
        steps.append(
            f"Слева от точки функция {'убывает' if kind == 'min' else 'возрастает'}, "
            f"справа {'возрастает' if kind == 'min' else 'убывает'} — это точка {word}."
        )
    return answer, "производная + сканирование", " ".join(steps)


def solve_extreme_value(
    tex: str, kind: str, segment: tuple | None
) -> tuple[str | None, str, str]:
    """«Наибольшее/наименьшее значение функции» — нужен не аргумент, а значение.

    Проверка независимая: помимо критических точек производной прогоняем густую
    сетку и смотрим, что найденное значение действительно крайнее."""
    expr = tex_to_sympy(tex)
    if X not in expr.free_symbols:
        return None, "нет переменной x", ""

    derivative = sympy.diff(expr, X)
    points = [p for p in sympy.solve(sympy.Eq(derivative, 0), X, dict=False) if p.is_real]

    if segment:
        low, high = segment[0], segment[1]
        candidates = [sympy.nsimplify(low, rational=False), sympy.nsimplify(high, rational=False)]
        candidates += [p for p in points if low <= float(sympy.N(p)) <= high]
    else:
        candidates = points
        low, high = -50.0, 50.0

    values = []
    for point in candidates:
        try:
            values.append((float(sympy.N(expr.subs(X, point))), point))
        except Exception:
            continue
    if not values:
        return None, "значения не посчитались", ""

    best = min(values) if kind == "min" else max(values)
    best_value = sympy.simplify(expr.subs(X, best[1]))

    # Вторая дорога: сетка. Производную здесь не трогаем вовсе.
    grid = []
    steps_count = 2000
    for i in range(steps_count + 1):
        x = low + (high - low) * i / steps_count
        try:
            grid.append(float(sympy.N(expr.subs(X, x))))
        except Exception:
            continue
    if not grid:
        return None, "сетка не посчиталась", ""

    scanned = min(grid) if kind == "min" else max(grid)
    if (kind == "min" and scanned < best[0] - 1e-6) or (
        kind == "max" and scanned > best[0] + 1e-6
    ):
        return None, "сетка нашла значение лучше — разбор неверный", ""

    answer = as_answer(best_value)
    if answer is None:
        return None, "ответ не приводится к числу части 1", ""

    word = "наименьшее" if kind == "min" else "наибольшее"
    steps = [f"Производная: $y' = {sympy.latex(sympy.simplify(derivative))}$."]
    if points:
        steps.append(
            "Нули производной: " + ", ".join(f"$x = {sympy.latex(p)}$" for p in points) + "."
        )
    else:
        steps.append("Производная в нуль не обращается, значит функция монотонна.")
    if segment:
        steps.append(
            "Значение сравниваем в критических точках и на концах отрезка "
            f"$[{segment[2]}; {segment[3]}]$."
        )
    steps.append(
        f"{word.capitalize()} значение достигается при $x = {sympy.latex(best[1])}$ "
        f"и равно ${sympy.latex(best_value)}$."
    )
    return answer, "производная + сетка", " ".join(steps)


# ------------------------------------------------------------------ векторы (№2)

VECTOR_COORDS = re.compile(r"\\overrightarrow\s*\{(\w)\}\s*\(\s*([^)]+?)\s*\)")
VECTOR_ANGLE = re.compile(
    r"длины векторов.*?равны\s*(\d+)\s*и\s*(\d+).*?угол между ними равен\s*\$?\s*(\d+)",
    re.I | re.S,
)


def vector_parts(text: str) -> dict[str, tuple[float, float]]:
    """Координаты векторов из условия: «\\overrightarrow{a}(1;1)»."""
    found = {}
    for name, coords in VECTOR_COORDS.findall(text):
        parts = re.split(r"[;,]", coords)
        if len(parts) != 2:
            continue
        try:
            found[name] = (
                float(parts[0].replace(",", ".").replace("−", "-")),
                float(parts[1].replace(",", ".").replace("−", "-")),
            )
        except ValueError:
            continue
    return found


def combination(tex: str, vectors: dict[str, tuple[float, float]]):
    """Линейная комбинация вида «8\\overrightarrow{a}+\\overrightarrow{b}» в пару чисел."""
    symbols = {name: Symbol(f"vec_{name}") for name in vectors}
    # точка предложения приезжает внутрь формулы: «…+\overrightarrow{b}.»
    expression = tex.strip().rstrip(". ,;")
    for name in vectors:
        expression = expression.replace(f"\\overrightarrow{{{name}}}", f"vec_{name}")
    expression = expression.replace("\\cdot", "*")
    if "\\" in expression:
        raise ValueError("в комбинации осталась незнакомая команда")

    parsed = parse_expr(expression, local_dict=symbols, transformations=TRANSFORMS)
    x = y = sympy.Integer(0)
    for name, symbol in symbols.items():
        factor = parsed.coeff(symbol)
        x += factor * sympy.nsimplify(vectors[name][0])
        y += factor * sympy.nsimplify(vectors[name][1])
    return sympy.simplify(x), sympy.simplify(y)


def solve_vectors(text: str) -> tuple[str | None, str, str]:
    """№2: длина вектора, скалярное произведение по координатам или через угол."""
    lowered = text.lower()

    angle = VECTOR_ANGLE.search(text)
    if angle and "скалярное произведение" in lowered:
        first, second, degrees = (int(g) for g in angle.groups())
        exact = sympy.simplify(first * second * sympy.cos(sympy.rad(degrees)))
        # вторая дорога — обычная арифметика с плавающей точкой
        import math

        rough = first * second * math.cos(math.radians(degrees))
        if abs(float(sympy.N(exact)) - rough) > 1e-9:
            return None, "точный и численный счёт разошлись", ""
        return (
            as_answer(exact),
            "формула + численная проверка",
            f"Скалярное произведение равно произведению длин на косинус угла: "
            f"${first} \\cdot {second} \\cdot \\cos {degrees}° = {sympy.latex(exact)}$.",
        )

    vectors = vector_parts(text)
    if not vectors:
        return None, "координаты векторов не разобрались", ""

    chunks = re.findall(r"\$([^$]+)\$", text)
    targets = [c for c in chunks if "\\overrightarrow" in c and "(" not in c]
    if not targets:
        return None, "не нашли, что именно ищут", ""

    import math

    if "длину вектора" in lowered:
        x, y = combination(targets[-1], vectors)
        exact = sympy.sqrt(x**2 + y**2)
        rough = math.hypot(float(sympy.N(x)), float(sympy.N(y)))
        if abs(float(sympy.N(exact)) - rough) > 1e-9:
            return None, "длина посчиталась по-разному", ""
        return (
            as_answer(exact),
            "координаты + проверка счётом",
            f"Складываем покоординатно: $({sympy.latex(x)}; {sympy.latex(y)})$. "
            f"Длина — корень из суммы квадратов координат: ${sympy.latex(exact)}$.",
        )

    if "скалярное произведение" in lowered:
        if len(targets) >= 2:
            first, second = targets[-2], targets[-1]
        else:
            names = sorted(vectors)
            if len(names) < 2:
                return None, "нужны два вектора", ""
            first = f"\\overrightarrow{{{names[0]}}}"
            second = f"\\overrightarrow{{{names[1]}}}"

        x1, y1 = combination(first, vectors)
        x2, y2 = combination(second, vectors)
        exact = sympy.simplify(x1 * x2 + y1 * y2)
        rough = float(sympy.N(x1)) * float(sympy.N(x2)) + float(sympy.N(y1)) * float(sympy.N(y2))
        if abs(float(sympy.N(exact)) - rough) > 1e-9:
            return None, "произведение посчиталось по-разному", ""
        return (
            as_answer(exact),
            "координаты + проверка счётом",
            f"Координаты векторов: $({sympy.latex(x1)}; {sympy.latex(y1)})$ и "
            f"$({sympy.latex(x2)}; {sympy.latex(y2)})$. Скалярное произведение — "
            f"сумма произведений одноимённых координат: ${sympy.latex(exact)}$.",
        )

    return None, "формулировка про векторы не из знакомых", ""


# --------------------------------------------------------- вероятность (№4 и №5)

COIN = re.compile(
    r"монет[уы].*?(?:бросают|подбрасывают)\s*(дважды|трижды|(\d+)\s*раз)"
    r".*?(орёл|орел|решка|решк\w+)"
    r".*?(?:ровно\s*(один|два|три|\d+)\s*раз|(не\s+выпад\w+\s+ни\s+разу))",
    re.I | re.S,
)

# Числа берём якорями «из N …» и «… M <глагол>», а не через ленивые куски:
# ленивый вариант отгрызал по одной цифре и выдавал 3 из 3000.
AVERAGE = re.compile(
    r"в среднем из\s+(\d+)\b.{0,120}?\b(\d+)\s+"
    r"(подтекают|не\s+\w+|бракованн\w+|оказ\w+|окаж\w+|\w+ются|\w+ся)",
    re.I | re.S,
)

WORDS = {"один": 1, "дважды": 2, "два": 2, "трижды": 3, "три": 3}


def solve_coin(text: str) -> tuple[str | None, str, str]:
    """Монета: «бросают дважды, ровно один раз решка».

    Вторая дорога честная: формулу сверяем полным перебором исходов — для
    двух-трёх бросков их 4 и 8, перебор точный, а не приближённый."""
    match = COIN.search(text)
    if not match:
        return None, "не шаблон про монету", ""

    times_word, times_digits, side, exactly, never = match.groups()
    throws = int(times_digits) if times_digits else WORDS.get(times_word.lower())
    if never:
        wanted = 0
    else:
        wanted = WORDS.get(exactly.lower(), None)
        if wanted is None:
            wanted = int(exactly) if exactly.isdigit() else None
    if not throws or wanted is None or throws > 12:
        return None, "не разобрали числа в условии", ""

    formula = sympy.binomial(throws, wanted) / sympy.Integer(2) ** throws

    # перебор: считаем исходы напрямую, биномиальный коэффициент не используем
    from itertools import product

    outcomes = list(product([0, 1], repeat=throws))
    good = sum(1 for row in outcomes if sum(row) == wanted)
    direct = sympy.Rational(good, len(outcomes))

    if sympy.simplify(formula - direct) != 0:
        return None, "формула и перебор разошлись", ""

    return (
        as_answer(direct),
        "формула + полный перебор",
        f"Всего исходов ${len(outcomes)}$, подходящих ${good}$. "
        f"Вероятность равна ${sympy.latex(direct)}$.",
    )


# Ищем просто «равна 0,xx»: попытка привязаться к «вероятность того, что …»
# ломается на сокращениях вроде «учащийся А.» — точка обрывает совпадение.
PROB_VALUES = re.compile(r"равна\s+(0[.,]\d+)", re.I)


def solve_two_probabilities(text: str) -> tuple[str | None, str, str]:
    """Две названные вероятности: «ровно столько-то» и «одна из двух тем».

    Считать тут нечего — одно вычитание или одно сложение. Поэтому проверяем не
    арифметику, а то, что задача действительно этой схемы: вероятности лежат в
    [0;1], а для разности большая вероятность относится к более широкому событию.
    Врать в этих задачах может только понимание условия, и защита нужна от него.
    """
    values = [sympy.Rational(v.replace(",", ".")) for v in PROB_VALUES.findall(text)]
    if len(values) != 2:
        return None, "в условии не две вероятности", ""
    if any(v < 0 or v > 1 for v in values):
        return None, "вероятность вне [0;1]", ""

    tail = text.lower().split("найдите вероятность", 1)[-1]
    first, second = values

    # «больше четырёх» и «больше трёх», спрашивают «ровно четыре»
    if re.search(r"ровно", tail) and re.search(r"больше", text.lower()):
        answer_value = abs(second - first)
        bigger, smaller = max(values), min(values)
        if bigger <= smaller:
            return None, "вероятности не упорядочены", ""
        return (
            as_answer(answer_value),
            "разность вероятностей",
            f"Событие «ровно столько» — это разность двух вложенных событий: "
            f"${sympy.latex(bigger)} - {sympy.latex(smaller)} = {sympy.latex(answer_value)}$.",
        )

    # «вопрос по одной из этих двух тем», темы не пересекаются
    if re.search(r"одной из|одну из|или", tail) and re.search(
        r"не\s+встречаются|нет вопросов|одновременно", text.lower()
    ):
        total = first + second
        if total > 1:
            return None, "сумма вероятностей больше единицы", ""
        return (
            as_answer(total),
            "сумма несовместных событий",
            f"События несовместны, поэтому вероятности складываются: "
            f"${sympy.latex(first)} + {sympy.latex(second)} = {sympy.latex(total)}$.",
        )

    return None, "схема с двумя вероятностями не опознана", ""


def solve_average(text: str) -> tuple[str | None, str, str]:
    """«В среднем из N штук M бракованных» — доля годных или бракованных.

    Шаблон жёсткий намеренно: тут ошибается не арифметика, а понимание условия,
    и широкий шаблон дал бы уверенно посчитанный неверный ответ."""
    match = AVERAGE.search(text)
    if not match:
        return None, "не шаблон «в среднем из»", ""
    if "случайно выбранн" not in text.lower():
        return None, "нет опоры «случайно выбранный»", ""

    total, part = int(match.group(1)), int(match.group(2))
    if part > total or total == 0:
        return None, "числа не складываются в долю", ""

    # «не подтекает», «исправен», «годный» — спрашивают дополнение
    tail = text.lower().split("найдите вероятность")[-1]
    complement = bool(re.search(r"\bне\s+\w+|исправ|годн|качествен", tail))

    share = sympy.Rational(total - part, total) if complement else sympy.Rational(part, total)
    # вторая дорога: считаем дополнение и проверяем, что сумма равна единице
    other = sympy.Rational(part, total) if complement else sympy.Rational(total - part, total)
    if sympy.simplify(share + other - 1) != 0:
        return None, "доли не дают в сумме единицу", ""

    answer = as_answer(share)
    if answer is None:
        return None, "доля не выражается конечной дробью", ""

    what = "годных" if complement else "нужных"
    return (
        answer,
        "доля + проверка дополнением",
        f"Всего ${total}$, из них {what} ${total - part if complement else part}$. "
        f"Вероятность равна ${sympy.latex(share)}$.",
    )


# ------------------------------------------- вероятность: шаблоны школьных серий

ATHLETES = re.compile(
    r"(?:участву\w+|выступа\w+|среди них)[^\.]*?(\d+)\s*(?:спортсмен\w*|гимнаст\w*|"
    r"участник\w*|человек)", re.I | re.S
)
FROM_COUNTRY = re.compile(r"(\d+)\s+(?:из|спортсмен\w*\s+из)\s+([А-ЯЁ][а-яё]+)", re.I)
REST_COUNTRY = re.compile(r"остальные\s*(?:—|-)?\s*из\s+([А-ЯЁ][а-яё]+)", re.I)
ASKED_COUNTRY = re.compile(r"окаж\w+\s+из\s+([А-ЯЁ][а-яё]+)|будет выступать\s+\w+\s+из\s+([А-ЯЁ][а-яё]+)", re.I)


def solve_athletes(text: str) -> tuple[str | None, str, str]:
    """«Участвуют N спортсменов: a из одной страны, b из другой…»

    Позиция в жеребьёвке значения не имеет: вероятность для любого места одна и
    та же, поэтому ответ — просто доля. Проверяем разбор тем, что доли всех
    стран в сумме дают единицу: если числа выдернуты неверно, сумма разъедется.
    """
    total_match = ATHLETES.search(text)
    if not total_match:
        return None, "не нашли общее число участников", ""
    total = int(total_match.group(1))

    named = {country: int(count) for count, country in FROM_COUNTRY.findall(text)}
    if not named:
        return None, "не нашли, сколько из каждой страны", ""

    rest = REST_COUNTRY.search(text)
    counts = dict(named)
    if rest:
        counts[rest.group(1)] = total - sum(named.values())

    if sum(counts.values()) != total:
        return None, f"числа не сходятся: {counts} против {total}", ""
    if any(value < 0 for value in counts.values()):
        return None, "отрицательное число участников", ""

    asked = ASKED_COUNTRY.search(text)
    country = None
    if asked:
        country = asked.group(1) or asked.group(2)
    if country is None:
        return None, "не поняли, про какую страну спрашивают", ""

    # ищем страну по началу слова: в вопросе она в родительном падеже
    match = next((k for k in counts if k[:4].lower() == country[:4].lower()), None)
    if match is None:
        return None, f"страна «{country}» не встречается в условии", ""

    share = sympy.Rational(counts[match], total)
    answer = as_answer(share)
    if answer is None:
        return None, "доля не выражается конечной дробью", ""

    return (
        answer,
        "доля + сходимость по всем странам",
        f"Порядок выступления определяется жребием, поэтому для любого места "
        f"вероятность одна и та же — это доля: "
        f"$\\frac{{{counts[match]}}}{{{total}}}={sympy.latex(share)}$.",
    )


SHOTS = re.compile(
    r"по одному разу.{0,40}?(?:кажд\w+ из )?(\w+|\d+)\s*мишен\w+.*?"
    r"равна\s*(0[.,]\d+).*?попадёт в\s*(\w+|\d+)\s*(?:перв\w+)\s*мишен\w+",
    re.I | re.S,
)
COUNT_WORDS = {"одну": 1, "две": 2, "три": 3, "четыре": 4, "пять": 5,
               "одной": 1, "двух": 2, "трёх": 3, "трех": 3, "четырёх": 4, "четырех": 4}


def solve_shots(text: str) -> tuple[str | None, str, str]:
    """«Попадёт в k первых мишеней и не попадёт в остальные».

    Считаем формулой $p^{k}(1-p)^{n-k}$ и независимо — перебором всех исходов
    по мишеням: их $2^{n}$, каждый со своим весом. Перебор о формуле не знает.
    """
    match = SHOTS.search(text)
    if not match:
        return None, "не шаблон про мишени", ""

    total_word, probability, hits_word = match.groups()
    total = COUNT_WORDS.get(total_word.lower(), None)
    if total is None:
        total = int(total_word) if total_word.isdigit() else None
    hits = COUNT_WORDS.get(hits_word.lower(), None)
    if hits is None:
        hits = int(hits_word) if hits_word.isdigit() else None
    if not total or hits is None or total > 12 or hits > total:
        return None, "числа мишеней не разобрались", ""

    p = sympy.Rational(probability.replace(",", "."))
    formula = p**hits * (1 - p) ** (total - hits)

    # перебор: нужен ровно один исход — попал в первые hits и промазал в остальные
    from itertools import product

    direct = sympy.Integer(0)
    for outcome in product([1, 0], repeat=total):
        if list(outcome) != [1] * hits + [0] * (total - hits):
            continue
        weight = sympy.Integer(1)
        for shot in outcome:
            weight *= p if shot else (1 - p)
        direct += weight

    if sympy.simplify(formula - direct) != 0:
        return None, "формула и перебор разошлись", ""

    answer = as_answer(direct)
    if answer is None:
        return None, "ответ не выражается конечной дробью", ""

    return (
        answer,
        "формула + перебор исходов",
        f"Выстрелы независимы, поэтому вероятности перемножаются: "
        f"${sympy.latex(p)}^{{{hits}}}\\cdot({sympy.latex(1 - p)})^{{{total - hits}}}"
        f"={sympy.latex(direct)}$.",
    )


DICE = re.compile(
    r"игральную кость бросили два раза.*?шесть очков не выпало ни разу.*?"
    r"сумма очков равна\s*(\d+)", re.I | re.S,
)

NUMBER_WORDS = {
    "одном": 1, "двух": 2, "трёх": 3, "трех": 3, "четырёх": 4, "четырех": 4,
    "пяти": 5, "шести": 6, "семи": 7, "восьми": 8, "девяти": 9, "десяти": 10,
    "двенадцати": 12, "пятнадцати": 15, "двадцати": 20,
}

TICKETS = re.compile(
    r"всего\s*(\d+)\s*билет\w*|(\d+)\s*билет\w*", re.I
)
TICKETS_WITH = re.compile(r"в\s*(\d+|[а-яё]+)\s*из них", re.I)


def solve_dice(text: str) -> tuple[str | None, str, str]:
    """Условная вероятность на двух костях при запрете шестёрки.

    Основной способ — перебор оставшихся 25 исходов. Проверка независимая:
    то же количество считается формулой, без перебора."""
    match = DICE.search(text)
    if not match:
        return None, "не шаблон про кости", ""

    wanted = int(match.group(1))
    outcomes = [(a, b) for a in range(1, 6) for b in range(1, 6)]
    good = [pair for pair in outcomes if sum(pair) == wanted]

    # независимая формула: сколько a от 1 до 5 дают b = wanted - a в тех же границах
    counted = sum(1 for a in range(1, 6) if 1 <= wanted - a <= 5)
    if counted != len(good):
        return None, "перебор и подсчёт разошлись", ""

    share = sympy.Rational(len(good), len(outcomes))
    answer = as_answer(share)
    if answer is None:
        return None, "доля не выражается конечной дробью", ""

    return (
        answer,
        "перебор исходов + подсчёт формулой",
        f"Шестёрка не выпадала, значит на каждой кости от $1$ до $5$ — всего "
        f"${len(outcomes)}$ равновозможных исходов. Сумму ${wanted}$ дают "
        f"${len(good)}$ из них, поэтому вероятность равна ${sympy.latex(share)}$.",
    )


def solve_tickets(text: str) -> tuple[str | None, str, str]:
    """«Всего N билетов, в M из них вопрос по теме» — доля или её дополнение."""
    low = text.lower()
    if "билет" not in low or "из них" not in low:
        return None, "не шаблон про билеты", ""

    total_match = re.search(r"(?:всего\s*)?(\d+)\s*билет", low)
    part_match = TICKETS_WITH.search(low)
    if not total_match or not part_match:
        return None, "числа билетов не разобрались", ""

    total = int(total_match.group(1))
    raw = part_match.group(1)
    part = int(raw) if raw.isdigit() else NUMBER_WORDS.get(raw)
    if part is None or part > total:
        return None, f"не поняли число «{raw}»", ""

    tail = low.split("найдите вероятность", 1)[-1]
    complement = " не " in tail

    share = sympy.Rational(total - part if complement else part, total)
    if sympy.simplify(share + sympy.Rational(part if complement else total - part, total) - 1) != 0:
        return None, "доли не дают в сумме единицу", ""

    answer = as_answer(share)
    if answer is None:
        return None, "доля не выражается конечной дробью", ""

    kind = "без этого вопроса" if complement else "с этим вопросом"
    return (
        answer,
        "доля + проверка дополнением",
        f"Всего билетов ${total}$, {kind} — ${total - part if complement else part}$. "
        f"Вероятность равна ${sympy.latex(share)}$.",
    )


# ------------------------------------------------ прикладные и текстовые серии

BELL = re.compile(
    r"υ\s*=\s*(\d+).*?V_\{?1\}?\s*=\s*(\d+).*?α\s*=\s*([\d.,]+).*?T\s*=\s*(\d+).*?"
    r"работа\w*\s+в\s+([\d\s]+)\s*Дж",
    re.I | re.S,
)

HOUR_WORDS = {"первый": 1, "один": 1, "два": 2, "две": 2, "три": 3, "четыре": 4,
              "пять": 5, "шесть": 6, "семь": 7}


def solve_diving_bell(text: str) -> tuple[str | None, str, str]:
    r"""Водолазный колокол: $A=\alpha\upsilon T\log_2\frac{V_1}{V_2}$.

    Серия из восьми задач, отличаются только числами. Проверка прямая:
    найденный объём подставляем обратно в формулу и сверяем работу."""
    match = BELL.search(text.replace("\u2009", "").replace("\u00a0", " "))
    if not match:
        return None, "не шаблон про водолазный колокол", ""

    nu = sympy.Integer(match.group(1))
    v1 = sympy.Integer(match.group(2))
    alpha = sympy.Rational(match.group(3).replace(",", "."))
    temperature = sympy.Integer(match.group(4))
    work = sympy.Integer(match.group(5).replace(" ", ""))

    factor = alpha * nu * temperature
    if factor == 0:
        return None, "нулевой коэффициент", ""

    logarithm = sympy.Rational(work, 1) / factor
    v2 = sympy.simplify(v1 / 2**logarithm)

    # обратная подстановка: считаем работу по найденному объёму
    back = sympy.simplify(factor * sympy.log(v1 / v2, 2))
    if abs(sympy.N(back - work, 30)) > EPS_ZERO:
        return None, "обратная подстановка не сошлась", ""

    answer = as_answer(v2)
    if answer is None:
        return None, "объём не выражается конечной дробью", ""

    return (
        answer,
        "подстановка в формулу + обратная проверка",
        f"Подставим величины: ${sympy.latex(factor)}\\log_{{2}}\\frac{{{v1}}}{{V_2}}"
        f"={work}$, откуда $\\log_{{2}}\\frac{{{v1}}}{{V_2}}={sympy.latex(logarithm)}$. "
        f"Значит $\\frac{{{v1}}}{{V_2}}={sympy.latex(2**logarithm)}$ и "
        f"$V_2={sympy.latex(v2)}$.",
    )


def solve_average_speed(text: str) -> tuple[str | None, str, str]:
    """Средняя скорость: весь путь делить на всё время.

    Два вида условий — по часам и по километрам. Считаем и проверяем тем, что
    средняя скорость обязана лежать между наименьшей и наибольшей из данных:
    типичная ошибка здесь — сложить скорости и поделить на их количество,
    и такой ответ границы почти всегда нарушает."""
    low = text.lower()
    if "среднюю скорость" not in low:
        return None, "не про среднюю скорость", ""

    # Между «час» и «со скоростью» может стоять что угодно: «первый час
    # автомобиль ехал со скоростью». Раньше шаблон этого не допускал и молча
    # терял первый участок — ответ получался неверным.
    by_hours = re.findall(
        r"(перв\w+|следующ\w+|затем|потом)?\s*([а-яё]+|\d+)\s*час\w*[^,.;]{0,40}?"
        r"со скоростью\s*(\d+)",
        low,
    )
    by_distance = re.findall(
        r"(\d+)\s*км[^,.;/]{0,40}?со скоростью\s*(\d+)", low
    )

    if by_distance and len(by_distance) >= 2:
        parts = [(sympy.Integer(s), sympy.Integer(v)) for s, v in by_distance]
        distance = sum(s for s, _ in parts)
        duration = sum(sympy.Rational(s, v) for s, v in parts)
        speeds = [v for _, v in parts]
        detail = " + ".join(f"\\frac{{{s}}}{{{v}}}" for s, v in parts)
    elif by_hours and len(by_hours) >= 2:
        parts = []
        for prefix, amount, speed in by_hours:
            hours = HOUR_WORDS.get(amount) or (int(amount) if amount.isdigit() else None)
            if hours is None and prefix and prefix.startswith("перв"):
                hours = 1
            if hours is None:
                return None, f"не поняли, сколько часов: «{amount}»", ""
            parts.append((sympy.Integer(hours), sympy.Integer(speed)))
        duration = sum(t for t, _ in parts)
        distance = sum(t * v for t, v in parts)
        speeds = [v for _, v in parts]
        detail = " + ".join(f"{v}\\cdot {t}" for t, v in parts)
    else:
        return None, "участки пути не разобрались", ""

    if duration == 0:
        return None, "нулевое время", ""

    # Настоящая проверка разбора: сколько раз в условии сказано «со скоростью»,
    # столько участков и должно найтись. Проверка «результат между наименьшей и
    # наибольшей скоростью» этого не ловит — потерянный участок её проходит.
    mentioned = len(re.findall(r"со скоростью", low))
    if len(parts) != mentioned:
        return None, f"нашли {len(parts)} участков, а скоростей в условии {mentioned}", ""

    average = sympy.Rational(distance, 1) / duration
    if not (min(speeds) <= average <= max(speeds)):
        return None, "средняя скорость вне диапазона данных — разбор неверен", ""

    answer = as_answer(average)
    if answer is None:
        return None, "ответ не выражается конечной дробью", ""

    return (
        answer,
        "весь путь на всё время + проверка границами",
        f"Весь путь: ${detail} = {sympy.latex(distance)}$. "
        f"Всё время: ${sympy.latex(duration)}$. "
        f"Средняя скорость — это весь путь, делённый на всё время: "
        f"${sympy.latex(distance)}:{sympy.latex(duration)}={sympy.latex(average)}$.",
    )


# --------------------------------------------------------------------- разбор условий

EXPRESSION = re.compile(r"найдите значение выражения\s*(.+?)\s*[\.$]*$", re.I | re.S)
EQUATION = re.compile(r"найдите\s+(?:корень|корни)\s+уравнения\s*(.+?)\s*[\.]*$", re.I | re.S)
MIN_POINT = re.compile(r"найдите точку минимума функции\s*(.+?)\s*[\.]*$", re.I | re.S)
MAX_POINT = re.compile(r"найдите точку максимума функции\s*(.+?)\s*[\.]*$", re.I | re.S)
MIN_VALUE = re.compile(r"найдите наименьшее значение функции", re.I)
MAX_VALUE = re.compile(r"найдите наибольшее значение функции", re.I)
SEGMENT = re.compile(r"на отрезке\s*\[?\s*(-?[\d\.,]+)\s*[;,]\s*(-?[\d\.,]+)", re.I)


def formulas(statement: str) -> str:
    """Склеивает формулы из условия: они приходят кусками между долларами."""
    return " ".join(re.findall(r"\$([^$]+)\$", statement))


def parse_segment(chunks: list[str]) -> tuple[float, float, str, str] | None:
    r"""Границы отрезка из куска вида «[0;\frac{3π}{2}]».

    Возвращаем и числа для счёта, и исходную запись для разбора: печатать
    ученику $\frac{471238898038469}{100000000000000}$ вместо $\frac{3\pi}{2}$ —
    это издевательство, хотя число то же самое."""
    for chunk in chunks:
        text = chunk.strip().strip("$").strip()
        if not (text.startswith("[") and ";" in text):
            continue
        left, right = text.strip("[]").split(";", 1)
        try:
            return (
                float(sympy.N(tex_to_sympy(left))),
                float(sympy.N(tex_to_sympy(right))),
                left.strip(),
                right.strip(),
            )
        except Exception:
            return None
    return None


def solve(task: dict) -> tuple[str | None, str, str]:
    """Ответ, каким способом получен и готовый разбор для ученика."""
    text = " ".join(task["statement"].split())

    # Геометрия — шаблоны школьных свойств. Они идут до проверки на картинку
    # намеренно: у этих серий чертёж только иллюстрирует, а все числа есть в
    # тексте. Шаблон либо узнаёт условие целиком, либо молчит — угадывать по
    # обрывку он не станет.
    geometry = fipi_geometry.solve(text)
    if geometry[0] is not None:
        return geometry

    if task["images"]:
        return None, "условие с картинкой — сюда не лезем", ""

    lowered = text.lower()

    # Вероятность разбирается по тексту, формул там нет вовсе — поэтому эти
    # ветки идут до проверки на наличие формул.
    if "монет" in lowered and ("ровно" in lowered or "ни разу" in lowered):
        return solve_coin(text)

    if "в среднем из" in lowered:
        return solve_average(text)

    if "водолазный колокол" in lowered:
        return solve_diving_bell(text)

    if "среднюю скорость" in lowered:
        return solve_average_speed(text)

    if "игральную кость" in lowered:
        return solve_dice(text)

    if "билет" in lowered and "из них" in lowered:
        return solve_tickets(text)

    if "мишен" in lowered and "по одному разу" in lowered:
        return solve_shots(text)

    if re.search(r"жреб|жеребьёвк", lowered) and re.search(r"спортсмен|гимнаст|участ", lowered):
        return solve_athletes(text)

    if lowered.count("вероятность того") >= 2:
        return solve_two_probabilities(text)

    tex = formulas(text)
    if not tex:
        return None, "в условии нет формул", ""

    pick = "smaller" if "меньший" in lowered else "larger" if "больший" in lowered else "any"

    if "\\overrightarrow" in text or "длины векторов" in lowered:
        return solve_vectors(text)

    if EXPRESSION.search(lowered):
        return solve_expression(tex)
    if EQUATION.search(lowered):
        return solve_equation(tex, pick)
    if MIN_POINT.search(lowered):
        return solve_extremum(re.sub(r"^y\s*=", "", tex).strip(), "min")
    if MAX_POINT.search(lowered):
        return solve_extremum(re.sub(r"^y\s*=", "", tex).strip(), "max")

    if MIN_VALUE.search(lowered) or MAX_VALUE.search(lowered):
        kind = "min" if MIN_VALUE.search(lowered) else "max"
        # Отрезок в условии — отдельная формула: «$y=…$ на отрезке $[0;\frac{3π}{2}]$».
        # Поэтому функцию берём из первого куска, границы — из следующего.
        chunks = re.findall(r"\$([^$]+)\$", text)
        if not chunks:
            return None, "формулы не нашлись", ""
        formula = re.sub(r"^y\s*=", "", chunks[0]).strip()
        return solve_extreme_value(formula, kind, parse_segment(chunks[1:]))

    return None, "формулировка не из тех, что умеем", ""


# --------------------------------------------------------------------- запись


def write_solution(subject: str, guid: str, answer: str, how: str, solution: str) -> bool:
    """Кладёт в черновик ответ и разбор и переводит задачу в live.

    В live переводим только то, что прошло двойную проверку и получило разбор:
    импортёр всё равно не пустит live-задачу без разбора, а задача без разбора
    ученику бесполезна — после ошибки ему нужно объяснение, а не вердикт."""
    path = ROOT / "content" / subject / "_inbox" / f"{guid[:12].lower()}.yaml"
    if not path.exists():
        return False

    text = path.read_text(encoding="utf-8")
    # Прогон повторяемый: старую пометку снимаем, иначе она копится при каждом запуске
    text = re.sub(r"^# ответ[^\n]*\n(# [^\n]*\n)?", "", text, flags=re.M)
    text = text.replace("status: live", "status: draft")

    # Замены через lambda, а не строкой: в разборе есть \log и \sqrt, и re.sub
    # принял бы их за escape-последовательности шаблона и упал.
    text = re.sub(
        r"^  value: .*$", lambda _: f'  value: "{answer}"', text, count=1, flags=re.M
    )

    if not solution:
        body = None
    else:
        body = "\n".join("  " + line for line in solution.split("\n"))
    # Блок целиком: `solution:` может быть многострочным (|), и замена одной
    # строки оставила бы старый разбор висеть хвостом под новым.
    text = re.sub(
        r"^solution:.*?(?=^\S)",
        lambda _: (f"solution: |\n{body}\n" if body else "solution: null\n"),
        text,
        count=1,
        flags=re.M | re.S,
    )

    # difficulty у части 1 не выставляем на глаз: 3 — середина шкалы,
    # уточнится по реальной статистике решений, как и написано в CONTENT.md
    text = re.sub(r"^difficulty: .*$", "difficulty: 3", text, count=1, flags=re.M)

    text = re.sub(
        r"^status: draft$",
        lambda _: f"# ответ и разбор получены автоматически: {how}\nstatus: live",
        text,
        count=1,
        flags=re.M,
    )
    path.write_text(text, encoding="utf-8")

    # Готовую задачу кладём туда, откуда её забирает импортёр:
    # content/<предмет>/<номер задания>/<id>.yaml (docs/CONTENT.md).
    # Приёмник _inbox импортёр не смотрит — там лежат черновики без ответов.
    number = re.search(r"^task_type: (\d+)$", text, re.M)
    if number:
        ready = ROOT / "content" / subject / f"{int(number.group(1)):02d}"
        ready.mkdir(parents=True, exist_ok=True)
        (ready / f"{guid[:12].lower()}.yaml").write_text(text, encoding="utf-8")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="math_prof")
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--show", type=int, default=6, help="сколько решённых показать")
    args = parser.parse_args()

    parsed = ROOT / "content" / args.subject / "_inbox" / "_parsed.json"
    tasks = json.loads(parsed.read_text(encoding="utf-8"))

    solved: list[tuple[dict, str, str, str]] = []
    reasons: dict[str, int] = {}

    for task in tasks:
        try:
            with time_limit(TASK_SECONDS):
                answer, why, solution = solve(task)
        except Timeout:
            answer, why, solution = None, f"не уложились в {TASK_SECONDS} с", ""
        except Exception as error:
            answer, why, solution = None, f"разбор упал: {type(error).__name__}", ""

        if answer is None:
            reasons[why] = reasons.get(why, 0) + 1
        else:
            solved.append((task, answer, why, solution))

    print(f"задач всего: {len(tasks)}")
    print(f"решено и перепроверено: {len(solved)}")
    print("\nпочему остальные не решены:")
    for why, count in sorted(reasons.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {count:4}  {why}")

    print("\nпримеры решённого:")
    for task, answer, why, solution in solved[: args.show]:
        print(f"  · {' '.join(task['statement'].split())[:90]}")
        print(f"    ответ: {answer}   ({why})")
        print(f"    разбор: {solution[:150]}")

    if not args.dry:
        written = sum(
            write_solution(args.subject, t["guid"], a, w, sol) for t, a, w, sol in solved
        )
        print(f"\nответов записано в черновики: {written}")


if __name__ == "__main__":
    main()
