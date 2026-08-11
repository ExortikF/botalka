from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import func, select

from fastapi import APIRouter

from app.api.deps import DbSession, OptionalUser
from app.models import Attempt, Subject, Task, TaskStatus, TaskType

router = APIRouter(prefix="/api", tags=["catalog"])

# Предметы, которые показываем как «скоро»: их ещё нет в БД, но видно направление.
PLANNED_SUBJECTS = [
    {"slug": "rus", "title": "Русский язык"},
    {"slug": "inf", "title": "Информатика"},
]


class SubjectOut(BaseModel):
    id: int | None
    slug: str
    title: str
    tasks_count: int
    types_count: int
    solved: int
    available: bool


@router.get("/subjects", response_model=list[SubjectOut])
async def list_subjects(session: DbSession, user: OptionalUser) -> list[SubjectOut]:
    """Плитки предметов. Недоступные тоже отдаём — с available=false."""
    rows = (
        await session.execute(
            select(
                Subject,
                func.count(func.distinct(Task.id)),
                func.count(func.distinct(TaskType.id)),
            )
            .join(TaskType, TaskType.subject_id == Subject.id, isouter=True)
            .join(
                Task,
                (Task.task_type_id == TaskType.id) & (Task.status == TaskStatus.LIVE),
                isouter=True,
            )
            .group_by(Subject.id)
            .order_by(Subject.id)
        )
    ).all()

    result: list[SubjectOut] = []
    existing = set()

    for subject, tasks_count, types_count in rows:
        existing.add(subject.slug)
        solved = 0
        if user is not None:
            solved = (
                await session.scalar(
                    select(func.count(func.distinct(Attempt.task_id)))
                    .join(Task, Task.id == Attempt.task_id)
                    .join(TaskType, TaskType.id == Task.task_type_id)
                    .where(Attempt.user_id == user.id, TaskType.subject_id == subject.id)
                )
                or 0
            )
        result.append(
            SubjectOut(
                id=subject.id,
                slug=subject.slug,
                title=subject.title,
                tasks_count=tasks_count,
                types_count=types_count,
                solved=solved,
                available=tasks_count > 0,
            )
        )

    for planned in PLANNED_SUBJECTS:
        if planned["slug"] not in existing:
            result.append(
                SubjectOut(
                    id=None,
                    slug=planned["slug"],
                    title=planned["title"],
                    tasks_count=0,
                    types_count=0,
                    solved=0,
                    available=False,
                )
            )

    return result
