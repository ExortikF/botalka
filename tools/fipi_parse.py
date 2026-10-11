"""Разбор скачанных страниц ФИПИ в черновики задач.

    python3 tools/fipi_parse.py                 # разобрать всё скачанное
    python3 tools/fipi_parse.py --limit 5       # только первые пять, посмотреть глазами

Читает `content/_raw/fipi/<subject>/page_*.html`, пишет черновики в
`content/<subject>/_inbox/<guid>.yaml` в формате из docs/CONTENT.md.

Важное: **ответа в выдаче банка нет** — ФИПИ проверяет его у себя на сервере.
Поэтому у всех черновиков `answer.value: null` и `status: draft`. Ответ
проставляет решатель (`fipi_solve.py`), а в `live` задача попадает только после
двойной проверки. Ни одна задача не должна доехать до ученика с ответом,
который никто не перепроверил.

Что делает разборщик:
  * вынимает guid, тип ответа (по подсказке банка) и текст условия;
  * переводит MathML в LaTeX — тот же формат, что уже рендерит KaTeX на фронте;
  * заменяет вызовы ShowPictureQ на путь к картинке;
  * помечает `needs_review: true`, если в условии осталось что-то непонятное:
    неизвестный тег MathML, таблица, картинка-график.
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import re
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "content" / "_raw" / "fipi"

MML = "{http://www.w3.org/1998/Math/MathML}"

# Куда складываем картинки задач: путь относительно content/, его же отдаёт
# бэкенд по адресу /content/<путь>.
IMG_DIR = "math_prof/img"

# Как банк подписывает тип ответа → наш answer.type из docs/CONTENT.md
ANSWER_KINDS = {
    "впишите правильный ответ": "number",
    "выберите один ответ": "string",
    "установите соответствие": "digits",
    "запишите ответ": "number",
}


# ----------------------------------------------------------------- MathML → LaTeX

# Названия функций пишем командами LaTeX, иначе KaTeX сочтёт их произведением букв.
FUNCTIONS = {
    "ln", "lg", "log", "sin", "cos", "tg", "ctg", "arcsin", "arccos",
    "arctg", "arcctg", "sh", "ch", "exp", "max", "min",
}

OPERATORS = {
    "−": "-",
    "⁢": "",       # невидимое умножение
    "⁡": "",       # невидимое применение функции
    "·": r"\cdot ",
    "⋅": r"\cdot ",
    "×": r"\times ",
    "≤": r"\le ",
    "≥": r"\ge ",
    "≠": r"\ne ",
    "∞": r"\infty ",
    "±": r"\pm ",
    "→": r"\to ",
    "∈": r"\in ",
    "≈": r"\approx ",
}


def _tex(node: ElementTree.Element, unknown: set[str]) -> str:
    tag = node.tag.replace(MML, "").replace("m:", "")
    kids = list(node)

    def join(sep: str = "") -> str:
        return sep.join(_tex(k, unknown) for k in kids)

    text = (node.text or "").strip()

    if tag in {"math", "semantics", "mrow", "mstyle", "mpadded"}:
        return join()
    if tag in {"mi", "mn", "mtext"}:
        # Названия функций в MathML — обычные mi, и без обратного слеша KaTeX
        # печатает их курсивом как произведение букв: «lnx» вместо «ln x».
        if text in FUNCTIONS:
            return f"\\{text} "
        return text
    if tag == "mo":
        return OPERATORS.get(text, text)
    if tag == "mspace":
        return " "
    if tag == "msub":
        return f"{_tex(kids[0], unknown)}_{{{_tex(kids[1], unknown)}}}" if len(kids) == 2 else join()
    if tag == "msup":
        return f"{_tex(kids[0], unknown)}^{{{_tex(kids[1], unknown)}}}" if len(kids) == 2 else join()
    if tag == "msubsup" and len(kids) == 3:
        base, sub, sup = (_tex(k, unknown) for k in kids)
        return f"{base}_{{{sub}}}^{{{sup}}}"
    if tag == "mfrac" and len(kids) == 2:
        return rf"\frac{{{_tex(kids[0], unknown)}}}{{{_tex(kids[1], unknown)}}}"
    if tag == "msqrt":
        return rf"\sqrt{{{join()}}}"
    if tag == "mroot" and len(kids) == 2:
        return rf"\sqrt[{_tex(kids[1], unknown)}]{{{_tex(kids[0], unknown)}}}"
    if tag == "mover" and len(kids) == 2:
        return rf"\overrightarrow{{{_tex(kids[0], unknown)}}}"
    if tag == "mtable":
        # Таблица внутри формулы — обычно система уравнений или таблица значений.
        # KaTeX умеет array, но проверить такую задачу глазами всё равно нужно,
        # поэтому она уедет в needs_review вместе с остальными непростыми.
        rows = [_tex(row, unknown) for row in kids]
        width = max((len(list(row)) for row in kids), default=1)
        return r"\begin{array}{" + "c" * width + "}" + r" \\ ".join(rows) + r"\end{array}"
    if tag == "mtr":
        return " & ".join(_tex(cell, unknown) for cell in kids)
    if tag == "mtd":
        return join()
    if tag == "mfenced":
        # Скобки заданы атрибутами, а не символами: без этой ветки f(x)
        # превращается в fx, а интервал (-9; 4) — в -9; 4.
        separator = node.get("separators", "")
        inner = join(separator[:1] if separator else "")
        return f"{node.get('open', '(')}{inner}{node.get('close', ')')}"
    if tag == "annotation":
        return ""  # дубль формулы в другом формате, нам не нужен

    unknown.add(tag)
    return join()


def mathml_to_tex(fragment: str, unknown: set[str]) -> str:
    """Одна формула `<m:math>…</m:math>` в кусок LaTeX для KaTeX.

    Префикс `m:` просто срезаем: пространство имён нам ни к чему, а
    ElementTree без объявленного xmlns на префикс ругается."""
    xml = re.sub(r"</?m:", lambda m: m.group(0).replace("m:", ""), fragment)
    xml = re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", xml)
    # HTML-мнемоники вроде &nbsp; для XML не определены и роняют разбор,
    # поэтому разворачиваем их заранее — кроме тех трёх, что значимы для XML.
    xml = re.sub(
        r"&(?!amp;|lt;|gt;)[a-zA-Z]+;",
        lambda m: html_mod.unescape(m.group(0)),
        xml,
    )
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        unknown.add("не разобрался xml")
        return "[формула]"
    body = _tex(root, unknown).strip()
    return f"${body}$" if body else ""


# ----------------------------------------------------------------- разбор страницы


def strip_tags(fragment: str) -> str:
    fragment = re.sub(r"<script.*?</script>", " ", fragment, flags=re.S | re.I)
    fragment = re.sub(r"<style.*?</style>", " ", fragment, flags=re.S | re.I)
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"</p>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    fragment = html_mod.unescape(fragment).replace("\xa0", " ")
    fragment = re.sub(r"[ \t]+", " ", fragment)
    return "\n".join(line.strip() for line in fragment.split("\n") if line.strip())


def properties(block: str) -> dict:
    """Панель «СВОЙСТВА ЗАДАНИЯ»: коды КЭС, тип ответа и номер задания в банке.

    КЭС — это кодификатор элементов содержания. Номер задания в КИМ банк не
    указывает, но по КЭС его можно вывести — этим занимается fipi_classify.py."""
    panel = re.search(r'class="task-info-content".*?</table>', block, re.S)
    if not panel:
        return {}

    text = panel.group(0)
    kes = [strip_tags(div) for div in re.findall(r"<div>(.*?)</div>", text, re.S)]
    answer_kind = re.search(r"Тип ответа:</td><td[^>]*>(.*?)</td>", text, re.S)
    number = re.search(r"Номер:</td><td[^>]*>(.*?)</td>", text, re.S)

    return {
        "kes": [k for k in kes if re.match(r"^\d", k)],
        "answer_kind": strip_tags(answer_kind.group(1)) if answer_kind else "",
        "bank_number": strip_tags(number.group(1)) if number else "",
    }


def statement_cell(body: str) -> str:
    """Только ячейка с условием.

    Банк заворачивает задачу в служебные таблицы: рамка вокруг всего блока и
    блок отправки ответа снизу. Условие лежит в первой ячейке `cell_0` и
    заканчивается на её закрывающем теге — дальше идёт разметка, а не текст."""
    cell = re.search(r"class='cell_0'>(.*?)</TD>", body, re.S | re.I)
    return cell.group(1) if cell else body


def parse_block(block: str) -> dict | None:
    guid = re.search(r"name=\"guid\" value=\"([A-F0-9]+)\"", block, re.I)
    if not guid:
        return None

    unknown: set[str] = set()
    body = block

    # Картинка может быть не только иллюстрацией под условием, но и куском самого
    # предложения: ФИПИ так вставляет, например, «36,8 °C». Поэтому не вырезаем,
    # а ставим метку на место — иначе из условия молча пропадает число.
    images: list[str] = []

    def mark_image(match: re.Match) -> str:
        path = match.group(1)
        images.append(path)
        return f" [[img:{IMG_DIR}/{path.rsplit('/', 1)[-1]}]] "

    body = re.sub(
        r"<script[^>]*>\s*ShowPictureQ\w*\('([^']+\.(?:png|jpg|gif))'[^<]*</script>",
        mark_image,
        body,
        flags=re.I | re.S,
    )

    # формулы → LaTeX до того, как срежем теги
    for formula in re.findall(r"<m:math.*?</m:math>", body, re.S):
        body = body.replace(formula, " " + mathml_to_tex(formula, unknown) + " ")

    hint = re.search(r'class="hint"[^>]*>(.*?)</div>', block, re.S)
    hint_text = strip_tags(hint.group(1)).lower() if hint else ""

    props = properties(block)
    # служебная панель «СВОЙСТВА ЗАДАНИЯ» не часть условия
    body = re.sub(r"<div class=\"task-header-panel\".*", "", body, flags=re.S)
    body = re.sub(r"<div id='i[A-F0-9]+'>.*", "", body, flags=re.S)

    cell = statement_cell(body)
    statement = strip_tags(re.sub(r'<div id="hint".*?</div>', "", cell, flags=re.S))
    statement = re.sub(r"\s*\$\s*\$\s*", " ", statement)
    statement = re.sub(r"[ ]{2,}", " ", statement).strip()

    answer_type = next((v for k, v in ANSWER_KINDS.items() if k in hint_text), "number")

    return {
        "guid": guid.group(1),
        "kes": props.get("kes", []),
        "answer_kind": props.get("answer_kind", ""),
        "bank_number": props.get("bank_number", ""),
        "block_id": (re.search(r"id='(q[A-F0-9]+)'", block, re.I) or [None, None])[1],
        "hint": hint_text,
        "answer_type": answer_type,
        "statement": statement,
        "images": [p.rsplit("/", 1)[-1] for p in images],
        "unknown_mathml": sorted(unknown),
        # Ручной приёмки требует всё, где мы не уверены, что условие полное
        "needs_review": (
            bool(unknown) or bool(images) or "<table" in cell.lower()
            or "begin{array}" in statement
        ),
    }


def parse_subject(subject: str, limit: int | None) -> list[dict]:
    pages = sorted((RAW / subject).glob("page_*.html"))
    if not pages:
        raise SystemExit(f"нет скачанных страниц в {RAW / subject} — сначала fipi_fetch.py")

    tasks: list[dict] = []
    for page in pages:
        html = page.read_text(encoding="utf-8")
        for block in re.split(r"(?=<div class=\"qblock\")", html)[1:]:
            parsed = parse_block(block)
            if parsed:
                parsed["source_page"] = page.name
                tasks.append(parsed)
            if limit and len(tasks) >= limit:
                return tasks
    return tasks


# ----------------------------------------------------------------- запись черновиков


def yaml_block(text: str, indent: str = "  ") -> str:
    return "|\n" + "\n".join(indent + line for line in text.split("\n"))


def write_drafts(subject: str, tasks: list[dict]) -> Path:
    out = ROOT / "content" / subject / "_inbox"
    out.mkdir(parents=True, exist_ok=True)

    for task in tasks:
        image = f"{IMG_DIR}/{task['images'][0]}" if task["images"] else "null"
        text = f"""# Черновик из открытого банка ФИПИ. Ответа в банке нет — его проставляет
# решатель, и только после двойной проверки задача переводится в live.
id: fipi_{task['guid'][:12].lower()}
subject: {subject}
task_type: null           # номер задания КИМ проставляется отдельно, см. fipi_classify.py
difficulty: null
statement: {yaml_block(task['statement'])}
image: {image}
answer:
  type: {task['answer_type']}
  value: null
solution: null
source:
  kind: fipi
  year: null
  ref: "{task['guid']}"
  label: "Открытый банк ФИПИ"
  url: "https://ege.fipi.ru/bank/"
status: draft
needs_review: {str(task['needs_review']).lower()}
"""
        (out / f"{task['guid'][:12].lower()}.yaml").write_text(text, encoding="utf-8")

    (out / "_parsed.json").write_text(
        json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="math_prof")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry", action="store_true", help="только показать, не писать файлы")
    args = parser.parse_args()

    tasks = parse_subject(args.subject, args.limit)
    print(f"разобрано задач: {len(tasks)}")
    print(f"из них требуют глаз: {sum(t['needs_review'] for t in tasks)}")

    unknown = sorted({tag for t in tasks for tag in t["unknown_mathml"]})
    if unknown:
        print(f"неизвестные элементы MathML: {', '.join(unknown)}")

    for task in tasks[:3]:
        print("\n---", task["guid"])
        print(task["statement"][:220])

    if not args.dry:
        print("\nчерновики:", write_drafts(args.subject, tasks))


if __name__ == "__main__":
    main()
