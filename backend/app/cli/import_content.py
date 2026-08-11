"""Импорт банка задач из YAML в БД.

    docker compose exec backend python -m app.cli.import_content

Идемпотентно: задача сопоставляется по `id` из файла (он же `slug`), повторный запуск
обновляет существующие, а не плодит дубли. Файлы — источник правды, БД — проекция.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import yaml
from sqlalchemy import select

from app.core.answers import check_answer
from app.core.db import SessionLocal
from app.models import AnswerType, Subject, Task, TaskStatus, TaskType

CONTENT_DIR = Path("/content")

SUBJECT_TITLES = {
    "math_prof": "Математика (профиль)",
    "math_base": "Математика (база)",
    "rus": "Русский язык",
}


def _load_files() -> list[tuple[Path, dict]]:
    docs: list[tuple[Path, dict]] = []
    for path in sorted(CONTENT_DIR.rglob("*.yaml")):
        if path.name.startswith("_"):
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("id"):
            docs.append((path, data))
    return docs


def _validate(path: Path, data: dict) -> list[str]:
    problems = []
    for field in ("id", "subject", "task_type", "statement", "answer"):
        if not data.get(field):
            problems.append(f"{path.name}: нет поля «{field}»")

    answer = data.get("answer") or {}
    try:
        answer_type = AnswerType(answer.get("type", ""))
    except ValueError:
        problems.append(f"{path.name}: неизвестный тип ответа «{answer.get('type')}»")
        return problems

    payload = {k: v for k, v in answer.items() if k != "type"}
    # задача обязана засчитывать собственный эталонный ответ — иначе она сломана
    if not check_answer(answer_type, payload, str(payload.get("value", ""))):
        problems.append(f"{path.name}: эталонный ответ не проходит собственную проверку")

    if data.get("status") == "live" and not data.get("solution"):
        problems.append(f"{path.name}: live-задача без разбора")

    return problems


async def _upsert(data: dict, types_meta: dict) -> str:
    async with SessionLocal() as session:
        subject_slug = data["subject"]
        subject = await session.scalar(select(Subject).where(Subject.slug == subject_slug))
        if subject is None:
            subject = Subject(
                slug=subject_slug, title=SUBJECT_TITLES.get(subject_slug, subject_slug)
            )
            session.add(subject)
            await session.flush()

        number = int(data["task_type"])
        year_spec = int(data.get("year_spec", 2026))
        task_type = await session.scalar(
            select(TaskType).where(
                TaskType.subject_id == subject.id,
                TaskType.number == number,
                TaskType.year_spec == year_spec,
            )
        )
        meta = types_meta.get(subject_slug, {}).get(number, {})
        if task_type is None:
            task_type = TaskType(
                subject_id=subject.id,
                number=number,
                year_spec=year_spec,
                title=meta.get("title", f"Задание {number}"),
                description=meta.get("description"),
            )
            session.add(task_type)
            await session.flush()
        elif meta.get("title"):
            task_type.title = meta["title"]
            task_type.description = meta.get("description")

        answer = dict(data["answer"])
        answer_type = AnswerType(answer.pop("type"))

        task = await session.scalar(select(Task).where(Task.slug == data["id"]))
        created = task is None
        if task is None:
            task = Task(slug=data["id"])
            session.add(task)

        task.task_type_id = task_type.id
        task.statement = data["statement"].strip()
        task.image_url = data.get("image")
        task.answer_type = answer_type
        task.answer_payload = answer
        task.solution = (data.get("solution") or "").strip() or None
        task.hints = data.get("hints") or []
        task.difficulty = int(data.get("difficulty", 3))
        task.source = data.get("source")
        task.status = TaskStatus(data.get("status", "draft"))

        await session.commit()
        return "создана" if created else "обновлена"


async def main() -> int:
    meta_path = CONTENT_DIR / "task_types.yaml"
    types_meta: dict = {}
    if meta_path.exists():
        raw = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        types_meta = {
            subject: {int(n): v for n, v in numbers.items()} for subject, numbers in raw.items()
        }

    docs = _load_files()
    if not docs:
        print(f"В {CONTENT_DIR} не найдено ни одной задачи")
        return 1

    problems = [p for path, data in docs for p in _validate(path, data)]
    if problems:
        print("Импорт остановлен, найдены проблемы:")
        for p in problems:
            print("  •", p)
        return 1

    stats = {"создана": 0, "обновлена": 0}
    for _, data in docs:
        stats[await _upsert(data, types_meta)] += 1

    live = sum(1 for _, d in docs if d.get("status") == "live")
    print(
        f"Готово: {stats['создана']} создано, {stats['обновлена']} обновлено, "
        f"{live} из {len(docs)} со статусом live"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
