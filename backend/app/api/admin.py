"""Админка: создание и правка задач через интерфейс.

Доступ — только пользователям с is_admin. Назначается командой:
    docker compose exec backend python -m app.cli.make_admin <tg_id или id>
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession
from app.core.answers import check_answer
from app.models import AnswerType, SourceKind, Subject, Task, TaskStatus, TaskType, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "нужны права администратора")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


class TaskIn(BaseModel):
    slug: str | None = None
    task_type_id: int
    statement: str = Field(min_length=3)
    image_url: str | None = None
    answer_type: AnswerType
    answer_value: str = Field(min_length=1)
    answer_tolerance: str | None = None
    answer_synonyms: list[str] = Field(default_factory=list)
    solution: str | None = None
    hints: list[str] = Field(default_factory=list)
    difficulty: int = Field(default=3, ge=1, le=5)
    source: str | None = None
    source_kind: SourceKind = SourceKind.OWN
    source_year: int | None = None
    source_ref: str | None = None
    source_url: str | None = None
    status: TaskStatus = TaskStatus.DRAFT

    def payload(self) -> dict:
        data: dict = {"value": self.answer_value}
        if self.answer_type is AnswerType.NUMBER_TOLERANCE and self.answer_tolerance:
            data["tolerance"] = self.answer_tolerance
        if self.answer_type is AnswerType.STRING and self.answer_synonyms:
            data["synonyms"] = self.answer_synonyms
        return data


class TaskOut(BaseModel):
    id: int
    slug: str
    task_type_id: int
    task_type_number: int
    statement: str
    image_url: str | None
    answer_type: str
    answer_value: str
    answer_tolerance: str | None
    answer_synonyms: list[str]
    solution: str | None
    hints: list[str]
    difficulty: int
    source: str | None
    source_kind: str
    source_year: int | None
    source_ref: str | None
    source_url: str | None
    status: str
    attempts: int
    accuracy: int | None


class TaskListOut(BaseModel):
    total: int
    items: list[TaskOut]


def _to_out(task: Task, attempts: int = 0, correct: int = 0) -> TaskOut:
    payload = task.answer_payload or {}
    return TaskOut(
        id=task.id,
        slug=task.slug,
        task_type_id=task.task_type_id,
        task_type_number=task.task_type.number,
        statement=task.statement,
        image_url=task.image_url,
        answer_type=task.answer_type.value,
        answer_value=str(payload.get("value", "")),
        answer_tolerance=payload.get("tolerance"),
        answer_synonyms=payload.get("synonyms", []),
        solution=task.solution,
        hints=task.hints or [],
        difficulty=task.difficulty,
        source=task.source,
        source_kind=task.source_kind.value,
        source_year=task.source_year,
        source_ref=task.source_ref,
        source_url=task.source_url,
        status=task.status.value,
        attempts=attempts,
        accuracy=round(100 * correct / attempts) if attempts else None,
    )


def _validate(payload: TaskIn) -> None:
    """Задача обязана засчитывать собственный эталонный ответ."""
    if not check_answer(payload.answer_type, payload.payload(), payload.answer_value):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "эталонный ответ не проходит собственную проверку — проверь тип ответа",
        )
    if payload.status is TaskStatus.LIVE and not (payload.solution or "").strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "нельзя публиковать задачу без разбора",
        )


@router.get("/tasks", response_model=TaskListOut)
async def list_tasks(
    session: DbSession,
    admin: AdminUser,
    q: str | None = None,
    task_type_id: int | None = None,
    task_status: TaskStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> TaskListOut:
    stmt = select(Task).join(TaskType, TaskType.id == Task.task_type_id)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Task.statement.ilike(pattern), Task.slug.ilike(pattern)))
    if task_type_id:
        stmt = stmt.where(Task.task_type_id == task_type_id)
    if task_status:
        stmt = stmt.where(Task.status == task_status)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    tasks = list(
        (await session.scalars(stmt.order_by(Task.id.desc()).limit(limit).offset(offset))).all()
    )
    for task in tasks:
        await session.refresh(task, ["task_type"])

    return TaskListOut(total=total, items=[_to_out(t) for t in tasks])


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, session: DbSession, admin: AdminUser) -> TaskOut:
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не найдена")
    await session.refresh(task, ["task_type"])
    return _to_out(task)


async def _next_slug(session: DbSession, task_type_id: int) -> str:
    task_type = await session.get(TaskType, task_type_id)
    if task_type is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "неизвестный номер задания")
    subject = await session.get(Subject, task_type.subject_id)
    count = (
        await session.scalar(
            select(func.count(Task.id)).where(Task.task_type_id == task_type_id)
        )
    ) or 0
    slug = f"{subject.slug}_{task_type.number:02d}_{count + 1:04d}"
    # на случай удалённых задач — ищем свободный
    while await session.scalar(select(Task.id).where(Task.slug == slug)):
        count += 1
        slug = f"{subject.slug}_{task_type.number:02d}_{count + 1:04d}"
    return slug


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskIn, session: DbSession, admin: AdminUser) -> TaskOut:
    _validate(payload)

    task = Task(
        slug=payload.slug or await _next_slug(session, payload.task_type_id),
        task_type_id=payload.task_type_id,
        statement=payload.statement.strip(),
        image_url=payload.image_url,
        answer_type=payload.answer_type,
        answer_payload=payload.payload(),
        solution=(payload.solution or "").strip() or None,
        hints=payload.hints,
        difficulty=payload.difficulty,
        source=payload.source,
        source_kind=payload.source_kind,
        source_year=payload.source_year,
        source_ref=payload.source_ref,
        source_url=payload.source_url,
        status=payload.status,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    await session.refresh(task, ["task_type"])
    return _to_out(task)


@router.put("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, payload: TaskIn, session: DbSession, admin: AdminUser
) -> TaskOut:
    _validate(payload)

    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не найдена")

    task.task_type_id = payload.task_type_id
    task.statement = payload.statement.strip()
    task.image_url = payload.image_url
    task.answer_type = payload.answer_type
    task.answer_payload = payload.payload()
    task.solution = (payload.solution or "").strip() or None
    task.hints = payload.hints
    task.difficulty = payload.difficulty
    task.source = payload.source
    task.source_kind = payload.source_kind
    task.source_year = payload.source_year
    task.source_ref = payload.source_ref
    task.source_url = payload.source_url
    task.status = payload.status

    await session.commit()
    await session.refresh(task, ["task_type"])
    return _to_out(task)


@router.delete("/tasks/{task_id}")
async def archive_task(task_id: int, session: DbSession, admin: AdminUser) -> dict:
    """Не удаляем физически: на задачу ссылаются попытки и чужая статистика."""
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не найдена")
    task.status = TaskStatus.BROKEN
    await session.commit()
    return {"ok": True, "status": task.status.value}


class AdminStats(BaseModel):
    total: int
    live: int
    draft: int
    broken: int
    by_type: list[dict]


@router.get("/stats", response_model=AdminStats)
async def admin_stats(session: DbSession, admin: AdminUser) -> AdminStats:
    rows = (
        await session.execute(
            select(TaskType.number, TaskType.title, Task.status, func.count(Task.id))
            .join(Task, Task.task_type_id == TaskType.id)
            .group_by(TaskType.number, TaskType.title, Task.status)
            .order_by(TaskType.number)
        )
    ).all()

    per_type: dict[int, dict] = {}
    totals = {"live": 0, "draft": 0, "broken": 0}
    for number, title, task_status, count in rows:
        entry = per_type.setdefault(
            number, {"number": number, "title": title, "live": 0, "draft": 0, "broken": 0}
        )
        entry[task_status.value] += count
        totals[task_status.value] += count

    return AdminStats(
        total=sum(totals.values()),
        live=totals["live"],
        draft=totals["draft"],
        broken=totals["broken"],
        by_type=list(per_type.values()),
    )
