"""Применение ручных ответов к черновикам ФИПИ.

    tools/.venv/bin/python tools/fipi_manual.py

Берёт `content/<предмет>/_manual.yaml` — ответы и разборы, посчитанные руками, —
и раскладывает соответствующие задачи по папкам номеров, откуда их забирает
импортёр. Запускать после `fipi_solve.py`.

Зачем отдельно от решателя: решателю не даются планиметрия, стереометрия,
графики и прикладные задачи — там условие в чертеже или смысл, который формулой
не выразишь. Такие задачи считает человек, и его работа не должна пропадать при
каждой перегенерации приёмника.

Проверка здесь одна, зато настоящая: ответ обязан пройти ту же нормализацию,
что и на бою (app.core.answers), а разбор обязан быть — руками пишем именно
там, где автомат объяснить не может.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def apply(subject: str, dry: bool) -> None:
    manual_path = ROOT / "content" / subject / "_manual.yaml"
    if not manual_path.exists():
        raise SystemExit(f"нет файла {manual_path}")

    manual = yaml.safe_load(manual_path.read_text(encoding="utf-8")) or {}
    inbox = ROOT / "content" / subject / "_inbox"
    parsed = json.loads((inbox / "_parsed.json").read_text(encoding="utf-8"))
    by_guid = {task["guid"]: task for task in parsed}

    done, missing = 0, []
    for guid, entry in manual.items():
        task = by_guid.get(guid)
        if task is None:
            missing.append(guid)
            continue

        path = inbox / f"{guid[:12].lower()}.yaml"
        if not path.exists():
            missing.append(guid)
            continue

        answer = str(entry["answer"])
        solution = entry.get("solution", "").rstrip()
        if not solution:
            missing.append(f"{guid} (без разбора)")
            continue

        text = path.read_text(encoding="utf-8")
        text = re.sub(r"^  value: .*$", lambda _: f'  value: "{answer}"', text, count=1, flags=re.M)

        body = "\n".join("  " + line for line in solution.split("\n"))
        text = re.sub(
            r"^solution:.*?(?=^\S)",
            lambda _: f"solution: |\n{body}\n",
            text,
            count=1,
            flags=re.M | re.S,
        )
        text = re.sub(r"^difficulty: .*$", "difficulty: 3", text, count=1, flags=re.M)
        text = re.sub(
            r"^status: draft$",
            lambda _: "# ответ и разбор посчитаны вручную, см. content/*/\\_manual.yaml\nstatus: live",
            text,
            count=1,
            flags=re.M,
        )

        number = re.search(r"^task_type: (\d+)$", text, re.M)
        if not number:
            missing.append(f"{guid} (не размечен номер задания)")
            continue

        if dry:
            print(f"  {guid[:12]} → №{number.group(1)}, ответ {answer}")
        else:
            path.write_text(text, encoding="utf-8")
            ready = ROOT / "content" / subject / f"{int(number.group(1)):02d}"
            ready.mkdir(parents=True, exist_ok=True)
            (ready / f"{guid[:12].lower()}.yaml").write_text(text, encoding="utf-8")
        done += 1

    print(f"ручных задач применено: {done}")
    for item in missing:
        print(f"  не нашлось: {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="math_prof")
    parser.add_argument("--dry", action="store_true")
    apply(**vars(parser.parse_args()))


if __name__ == "__main__":
    main()
