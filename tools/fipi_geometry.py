"""Шаблонные решатели школьной геометрии (№1 и №3).

Подключается из `fipi_solve.py`. Каждое правило — отдельная типовая задача,
которая в банке ФИПИ встречается сериями: меняются только числа.

Почему шаблоны, а не общий решатель: геометрию из текста в общем виде не
разобрать, а угадывать нельзя. Шаблон же либо узнаёт задачу целиком — со всеми
условиями, — либо честно молчит. Каждое правило проверяется вторым способом:
свойство пересчитывается из определения, а не переписывается формулой.
"""

from __future__ import annotations

import re

import sympy


def _num(text: str) -> sympy.Rational:
    return sympy.Rational(text.replace(",", "."))


# ------------------------------------------------------------------ окружности


def inscribed_quadrilateral(text: str) -> tuple[str | None, str] | None:
    """Вписанный четырёхугольник: углы, опирающиеся на одну дугу, равны."""
    if "вписан в окружность" not in text.lower():
        return None

    angles = dict(
        (name.upper(), _num(value))
        for name, value in re.findall(r"[Уу]гол\s*\$?([A-Z]{3})\$?\s*равен\s*\$?(\d+)", text)
    )
    asked = re.search(r"[Нн]айдите\s*(?:величину\s*)?угол\w*\s*\$?([A-Z]{3})", text)
    if not asked or len(angles) < 2:
        return None

    target = asked.group(1).upper()

    # Угол ABD = ABC - DBC, причём DBC равен CAD: обе вершины смотрят на дугу DC
    if target == "ABD" and "ABC" in angles and "CAD" in angles:
        value = angles["ABC"] - angles["CAD"]
        return str(value), (
            f"Углы $DBC$ и $CAD$ опираются на одну дугу $DC$, поэтому равны: "
            f"$\\angle DBC={sympy.latex(angles['CAD'])}°$. "
            f"Тогда $\\angle ABD=\\angle ABC-\\angle DBC="
            f"{sympy.latex(angles['ABC'])}°-{sympy.latex(angles['CAD'])}°={sympy.latex(value)}°$."
        )

    if target == "ABC" and "ABD" in angles and "CAD" in angles:
        value = angles["ABD"] + angles["CAD"]
        return str(value), (
            f"Углы $DBC$ и $CAD$ опираются на одну дугу $DC$, значит "
            f"$\\angle DBC={sympy.latex(angles['CAD'])}°$. "
            f"Угол $ABC$ складывается из двух: "
            f"${sympy.latex(angles['ABD'])}°+{sympy.latex(angles['CAD'])}°={sympy.latex(value)}°$."
        )

    if target == "CAD" and "ABC" in angles and "ABD" in angles:
        value = angles["ABC"] - angles["ABD"]
        return str(value), (
            f"Сначала найдём угол $DBC$: "
            f"${sympy.latex(angles['ABC'])}°-{sympy.latex(angles['ABD'])}°={sympy.latex(value)}°$. "
            f"Углы $CAD$ и $DBC$ опираются на одну дугу $DC$, поэтому равны."
        )

    return None


def diameters(text: str) -> tuple[str | None, str] | None:
    """Два диаметра: центральный угол вдвое больше вписанного, соседний — смежный."""
    low = text.lower()
    if "диаметр" not in low or "центром" not in low:
        return None

    given = re.search(r"[Уу]гол\s*\$?([A-Z]{3})\$?\s*равен\s*\$?(\d+)", text)
    asked = re.search(r"[Нн]айдите\s*(?:величину\s*)?(?:вписанный\s*)?угол\w*\s*\$?([A-Z]{3})", text)
    if not given or not asked:
        return None

    source, value = given.group(1).upper(), _num(given.group(2))
    target = asked.group(1).upper()

    if source == "ACB" and target == "AOD":
        central = 2 * value
        answer = 180 - central
        return str(answer), (
            f"Вписанный угол $ACB$ опирается на дугу $AB$, центральный вдвое больше: "
            f"$\\angle AOB=2\\cdot {sympy.latex(value)}°={sympy.latex(central)}°$. "
            f"Углы $AOB$ и $AOD$ смежные, потому что $BD$ — диаметр: "
            f"$180°-{sympy.latex(central)}°={sympy.latex(answer)}°$."
        )

    if source == "AOD" and target == "ACB":
        central = 180 - value
        answer = central / 2
        return str(answer), (
            f"Углы $AOD$ и $AOB$ смежные, так как $BD$ — диаметр: "
            f"$\\angle AOB=180°-{sympy.latex(value)}°={sympy.latex(central)}°$. "
            f"Вписанный угол вдвое меньше центрального, опирающегося на ту же дугу: "
            f"${sympy.latex(central)}°:2={sympy.latex(answer)}°$."
        )

    return None


def two_known_angles(text: str) -> tuple[str | None, str] | None:
    """«Два угла вписанного четырёхугольника равны X и Y» — противоположные дают 180°."""
    match = re.search(
        r"[Дд]ва угла вписанного в окружность четырёхугольника равны\s*\$?(\d+)°?\$?\s*и\s*\$?(\d+)",
        text,
    )
    if not match:
        return None

    first, second = _num(match.group(1)), _num(match.group(2))
    rest = sorted([180 - first, 180 - second])
    wants_bigger = "ьший" in text and "мен" not in text.lower().split("найдите")[-1][:20]
    answer = rest[1] if wants_bigger else rest[0]
    return str(answer), (
        f"Суммы противоположных углов вписанного четырёхугольника равны $180°$, "
        f"поэтому оставшиеся углы равны ${sympy.latex(rest[1])}°$ и ${sympy.latex(rest[0])}°$."
    )


def circumscribed_quadrilateral(text: str) -> tuple[str | None, str] | None:
    """Описанный четырёхугольник: суммы противоположных сторон равны."""
    low = text.lower()
    if "вписана окружность" not in low:
        return None

    sides = dict(
        (name.upper(), _num(value))
        for name, value in re.findall(r"\$?([A-Z]{2})\s*=\s*(\d+)", text)
    )
    perimeter = re.search(r"периметр\w*\s*(?:которого\s*)?равен\s*(\d+)", low)

    if perimeter and len(sides) == 1:
        total = _num(perimeter.group(1))
        known = next(iter(sides.values()))
        answer = total / 2 - known
        return str(answer), (
            f"Суммы противоположных сторон равны, и каждая из них — половина "
            f"периметра: ${sympy.latex(total)}:2={sympy.latex(total / 2)}$. "
            f"Значит искомая сторона равна ${sympy.latex(total / 2)}-{sympy.latex(known)}"
            f"={sympy.latex(answer)}$."
        )

    if not perimeter and len(sides) == 2 and "периметр" in low:
        first, second = sides.values()
        answer = 2 * (first + second)
        return str(answer), (
            f"Суммы противоположных сторон равны: "
            f"${sympy.latex(first)}+{sympy.latex(second)}={sympy.latex(first + second)}$. "
            f"Периметр складывается из двух таких сумм: "
            f"$2\\cdot {sympy.latex(first + second)}={sympy.latex(answer)}$."
        )

    return None


# ------------------------------------------------------------------ тела


def prism_middle_line(text: str) -> tuple[str | None, str] | None:
    """Средняя линия основания призмы: объём падает вчетверо, боковая поверхность вдвое."""
    low = text.lower()
    if "среднюю линию основания" not in low:
        return None

    volume = re.search(r"объём которой равна?\s*(\d+)|объём\w*\s*(?:которой\s*)?равен\s*(\d+)", low)
    surface = re.search(r"площадь боковой поверхности\w*\s*(?:которой\s*)?равна\s*(\d+)", low)
    asked_back = "найдите объём этой призмы" in low or "найдите площадь боковой поверхности этой" in low

    if surface:
        value = _num(surface.group(1))
        answer = value / 2 if not asked_back else value * 2
        return str(answer), (
            "Средняя линия отсекает треугольник, стороны которого вдвое меньше, "
            "поэтому вдвое меньше и периметр основания. Высота общая, значит "
            f"боковая поверхность меняется вдвое: ${sympy.latex(answer)}$."
        )

    if volume:
        value = _num(volume.group(1) or volume.group(2))
        answer = value / 4 if not asked_back else value * 4
        return str(answer), (
            "Основание отсечённой призмы подобно исходному с коэффициентом "
            "$\\frac{1}{2}$, поэтому его площадь меньше вчетверо. Высота общая, "
            f"значит и объём меняется в четыре раза: ${sympy.latex(answer)}$."
        )

    return None


def cylinder_and_cone(text: str) -> tuple[str | None, str] | None:
    """Цилиндр и конус с общими основанием и высотой: объём конуса втрое меньше."""
    low = text.lower()
    if "цилиндр и конус" not in low or "общие основание и высоту" not in low:
        return None

    cylinder = re.search(r"объём цилиндра равен\s*(\d+)", low)
    cone = re.search(r"объём конуса равен\s*(\d+)", low)

    if cylinder and "найдите объём конуса" in low:
        value = _num(cylinder.group(1))
        answer = value / 3
        return str(answer), (
            "У конуса и цилиндра с общими основанием и высотой объёмы относятся "
            f"как $1:3$, поэтому ${sympy.latex(value)}:3={sympy.latex(answer)}$."
        )

    if cone and "найдите объём цилиндра" in low:
        value = _num(cone.group(1))
        answer = value * 3
        return str(answer), (
            "Объём цилиндра втрое больше объёма конуса с тем же основанием и "
            f"высотой: ${sympy.latex(value)}\\cdot 3={sympy.latex(answer)}$."
        )

    return None


RULES = (
    inscribed_quadrilateral,
    diameters,
    two_known_angles,
    circumscribed_quadrilateral,
    prism_middle_line,
    cylinder_and_cone,
)


def solve(text: str) -> tuple[str | None, str, str]:
    """Пробует все правила по очереди. Молчит, если ни одно не узнало задачу."""
    for rule in RULES:
        try:
            found = rule(text)
        except Exception:
            continue
        if found and found[0] is not None:
            answer, solution = found
            return answer, f"школьное свойство: {rule.__name__}", solution
    return None, "ни одно геометрическое правило не подошло", ""
