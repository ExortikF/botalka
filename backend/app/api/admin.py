"""Админка: создание и правка задач через интерфейс.

Доступ — только пользователям с is_admin. Назначается командой:
    docker compose exec backend python -m app.cli.make_admin <tg_id или id>
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession
from app.core.answers import check_answer
from app.models import (
    AnswerType,
    CoinTransaction,
    Idea,
    IdeaStatus,
    MockAttempt,
    MockExam,
    MockStatus,
    ReportStatus,
    TaskReport,
    Attempt,
    Duel,
    DuelKind,
    Quiz,
    SourceKind,
    Subject,
    Task,
    TaskStatus,
    TaskType,
    User,
)

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


# --------------------------------------------------------------------- дашборд

class UserRow(BaseModel):
    """Только неконфиденциальное: ни tg_id, ни username здесь нет."""

    id: int
    display_name: str
    kind: str            # guest | telegram
    solved: int
    accuracy: int | None
    streak_days: int
    rating: int
    duels: int
    registered: datetime
    last_seen: datetime | None


class ProblemTask(BaseModel):
    id: int
    number: int
    statement: str
    attempts: int
    accuracy: int


class Funnel(BaseModel):
    registered: int
    started_quiz: int
    finished_quiz: int
    came_back: int          # вернулись на другой день
    played_duel: int


class Dashboard(BaseModel):
    users_total: int
    users_telegram: int
    users_guests: int
    users_new_week: int
    users_active_week: int
    users_active_today: int

    attempts_total: int
    attempts_week: int
    accuracy_avg: int | None
    quizzes_finished: int
    duels_link: int
    duels_online: int

    coins_issued: int
    avg_seconds: int
    retention_d1: int       # % вернувшихся на следующий день
    retention_d7: int
    funnel: Funnel

    users: list[UserRow]
    hardest: list[ProblemTask]
    easiest: list[ProblemTask]


@router.get("/dashboard", response_model=Dashboard)
async def dashboard(session: DbSession, admin: AdminUser, limit: int = 100) -> Dashboard:
    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)
    day_ago = now - timedelta(days=1)

    users = list(await session.scalars(select(User).order_by(User.id.desc())))

    stats = {
        row.user_id: row
        for row in (
            await session.execute(
                select(
                    Attempt.user_id.label("user_id"),
                    func.count(Attempt.id).label("attempts"),
                    func.count(Attempt.id).filter(Attempt.is_correct).label("correct"),
                    func.count(func.distinct(Attempt.task_id))
                    .filter(Attempt.is_correct)
                    .label("solved"),
                    func.max(Attempt.created_at).label("last"),
                )
                .group_by(Attempt.user_id)
            )
        ).all()
    }

    duel_counts = {
        row.user_id: row.count
        for row in (
            await session.execute(
                select(Duel.challenger_id.label("user_id"), func.count(Duel.id).label("count"))
                .group_by(Duel.challenger_id)
            )
        ).all()
    }

    rows: list[UserRow] = []
    for user in users[:limit]:
        stat = stats.get(user.id)
        accuracy = (
            round(100 * stat.correct / stat.attempts) if stat and stat.attempts else None
        )
        rows.append(
            UserRow(
                id=user.id,
                display_name=user.display_name,
                kind="guest" if user.is_guest else "telegram",
                solved=stat.solved if stat else 0,
                accuracy=accuracy,
                streak_days=user.streak_days,
                rating=user.rating,
                duels=duel_counts.get(user.id, 0),
                registered=user.created_at,
                last_seen=stat.last if stat else None,
            )
        )

    attempts_total = await session.scalar(select(func.count(Attempt.id))) or 0
    attempts_week = (
        await session.scalar(
            select(func.count(Attempt.id)).where(Attempt.created_at >= week_ago)
        )
        or 0
    )
    correct_total = (
        await session.scalar(
            select(func.count(Attempt.id)).where(Attempt.is_correct.is_(True))
        )
        or 0
    )

    active_week = (
        await session.scalar(
            select(func.count(func.distinct(Attempt.user_id))).where(
                Attempt.created_at >= week_ago
            )
        )
        or 0
    )
    active_today = (
        await session.scalar(
            select(func.count(func.distinct(Attempt.user_id))).where(
                Attempt.created_at >= day_ago
            )
        )
        or 0
    )

    # Задачи с аномальной решаемостью — главный сигнал о битом контенте:
    # 0% почти всегда значит неверный эталонный ответ, 100% — что задача слишком простая.
    task_rows = (
        await session.execute(
            select(
                Task.id,
                TaskType.number,
                Task.statement,
                func.count(Attempt.id).label("attempts"),
                func.count(Attempt.id).filter(Attempt.is_correct).label("correct"),
            )
            .join(TaskType, TaskType.id == Task.task_type_id)
            .join(Attempt, Attempt.task_id == Task.id)
            .group_by(Task.id, TaskType.number, Task.statement)
            .having(func.count(Attempt.id) >= 3)
        )
    ).all()

    scored = [
        ProblemTask(
            id=r.id,
            number=r.number,
            statement=r.statement[:90],
            attempts=r.attempts,
            accuracy=round(100 * r.correct / r.attempts),
        )
        for r in task_rows
    ]
    scored.sort(key=lambda t: t.accuracy)

    # Ретеншн: из тех, кто зарегистрировался достаточно давно, сколько вернулись
    # хотя бы раз на следующий день и на седьмой. Главная метрика продукта.
    day_sets: dict[int, set] = {}
    for row in (
        await session.execute(
            select(Attempt.user_id, func.date(Attempt.created_at)).distinct()
        )
    ).all():
        day_sets.setdefault(row[0], set()).add(row[1])

    def _retention(days: int) -> int:
        eligible = [u for u in users if (now - u.created_at).days >= days]
        if not eligible:
            return 0
        returned = 0
        for u in eligible:
            active = day_sets.get(u.id, set())
            start = u.created_at.date()
            if any((d - start).days >= days for d in active):
                returned += 1
        return round(100 * returned / len(eligible))

    quizzes_started = (
        await session.scalar(select(func.count(func.distinct(Quiz.user_id)))) or 0
    )
    quizzes_done = (
        await session.scalar(
            select(func.count(func.distinct(Quiz.user_id))).where(Quiz.finished_at.is_not(None))
        )
        or 0
    )
    duelists = (
        await session.scalar(
            select(func.count(func.distinct(Duel.challenger_id)))
        )
        or 0
    )
    multi_day = sum(1 for days in day_sets.values() if len(days) > 1)

    coins_issued = (
        await session.scalar(
            select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
                CoinTransaction.amount > 0
            )
        )
        or 0
    )
    avg_ms = await session.scalar(
        select(func.avg(Attempt.time_spent_ms)).where(Attempt.time_spent_ms > 0)
    )

    return Dashboard(
        coins_issued=coins_issued,
        avg_seconds=round((avg_ms or 0) / 1000),
        retention_d1=_retention(1),
        retention_d7=_retention(7),
        funnel=Funnel(
            registered=len(users),
            started_quiz=quizzes_started,
            finished_quiz=quizzes_done,
            came_back=multi_day,
            played_duel=duelists,
        ),
        users_total=len(users),
        users_telegram=sum(1 for u in users if not u.is_guest),
        users_guests=sum(1 for u in users if u.is_guest),
        users_new_week=sum(1 for u in users if u.created_at >= week_ago),
        users_active_week=active_week,
        users_active_today=active_today,
        attempts_total=attempts_total,
        attempts_week=attempts_week,
        accuracy_avg=round(100 * correct_total / attempts_total) if attempts_total else None,
        quizzes_finished=await session.scalar(
            select(func.count(Quiz.id)).where(Quiz.finished_at.is_not(None))
        )
        or 0,
        duels_link=await session.scalar(
            select(func.count(Duel.id)).where(Duel.kind == DuelKind.LINK)
        )
        or 0,
        duels_online=await session.scalar(
            select(func.count(Duel.id)).where(Duel.kind == DuelKind.ONLINE)
        )
        or 0,
        users=rows,
        hardest=scored[:10],
        easiest=list(reversed(scored[-10:])),
    )


# ------------------------------------------------------------------ жалобы

class ReportOut(BaseModel):
    id: int
    task_id: int
    task_number: int
    statement: str
    correct_answer: str
    message: str
    given_answer: str | None
    status: str
    created_at: datetime


@router.get("/reports", response_model=list[ReportOut])
async def list_reports(
    session: DbSession, admin: AdminUser, only_new: bool = True
) -> list[ReportOut]:
    stmt = select(TaskReport).order_by(TaskReport.id.desc()).limit(100)
    if only_new:
        stmt = stmt.where(TaskReport.status == ReportStatus.NEW)

    out: list[ReportOut] = []
    for report in await session.scalars(stmt):
        task = await session.get(Task, report.task_id)
        if task is None:
            continue
        await session.refresh(task, ["task_type"])
        out.append(
            ReportOut(
                id=report.id,
                task_id=task.id,
                task_number=task.task_type.number,
                statement=task.statement,
                correct_answer=str((task.answer_payload or {}).get("value", "")),
                message=report.message,
                given_answer=report.given_answer,
                status=report.status.value,
                created_at=report.created_at,
            )
        )
    return out


@router.post("/reports/{report_id}/{action}")
async def resolve_report(
    report_id: int, action: str, session: DbSession, admin: AdminUser
) -> dict:
    if action not in ("resolve", "decline"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "действие не поддерживается")
    report = await session.get(TaskReport, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "жалоба не найдена")

    report.status = ReportStatus.RESOLVED if action == "resolve" else ReportStatus.DECLINED
    report.resolved_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True, "status": report.status.value}


# --------------------------------------------------------- конструктор пробников

class MockIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    subject_slug: str = "math_prof"
    description: str | None = None
    duration_minutes: int = Field(default=235, ge=10, le=360)
    status: MockStatus = MockStatus.DRAFT
    # либо явный список задач, либо «собрать автоматически по номерам»
    task_ids: list[int] = Field(default_factory=list)
    auto_numbers: list[int] = Field(default_factory=list)


class MockOut(BaseModel):
    id: int
    subject_slug: str
    title: str
    description: str | None
    duration_minutes: int
    status: str
    task_ids: list[int]
    numbers: list[int]
    attempts: int


async def _mock_out(session: DbSession, exam: MockExam) -> MockOut:
    numbers = []
    for task_id in exam.task_ids:
        task = await session.get(Task, task_id)
        if task is None:
            continue
        await session.refresh(task, ["task_type"])
        numbers.append(task.task_type.number)

    attempts = (
        await session.scalar(
            select(func.count(MockAttempt.id)).where(MockAttempt.exam_id == exam.id)
        )
    ) or 0
    return MockOut(
        id=exam.id,
        subject_slug=exam.subject_slug,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        status=exam.status.value,
        task_ids=list(exam.task_ids),
        numbers=numbers,
        attempts=attempts,
    )


async def _collect_tasks(session: DbSession, numbers: list[int], subject: str) -> list[int]:
    """По одной случайной задаче на каждый указанный номер — как в настоящем варианте."""
    picked: list[int] = []
    for number in numbers:
        task_id = await session.scalar(
            select(Task.id)
            .join(TaskType, TaskType.id == Task.task_type_id)
            .where(
                Task.status == TaskStatus.LIVE,
                TaskType.number == number,
                TaskType.subject.has(slug=subject),
            )
            .order_by(func.random())
            .limit(1)
        )
        if task_id:
            picked.append(task_id)
    return picked


@router.get("/mocks", response_model=list[MockOut])
async def list_mocks_admin(session: DbSession, admin: AdminUser) -> list[MockOut]:
    exams = list(await session.scalars(select(MockExam).order_by(MockExam.id.desc())))
    return [await _mock_out(session, exam) for exam in exams]


@router.post("/mocks", response_model=MockOut, status_code=status.HTTP_201_CREATED)
async def create_mock(payload: MockIn, session: DbSession, admin: AdminUser) -> MockOut:
    task_ids = payload.task_ids or await _collect_tasks(
        session, payload.auto_numbers or list(range(1, 13)), payload.subject_slug
    )
    if len(task_ids) < 3:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "не набралось задач — проверь, что по выбранным номерам они есть",
        )

    exam = MockExam(
        subject_slug=payload.subject_slug,
        title=payload.title.strip(),
        description=(payload.description or "").strip() or None,
        task_ids=task_ids,
        duration_minutes=payload.duration_minutes,
        status=payload.status,
    )
    session.add(exam)
    await session.commit()
    await session.refresh(exam)
    return await _mock_out(session, exam)


@router.put("/mocks/{exam_id}", response_model=MockOut)
async def update_mock(
    exam_id: int, payload: MockIn, session: DbSession, admin: AdminUser
) -> MockOut:
    exam = await session.get(MockExam, exam_id)
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "пробник не найден")

    exam.title = payload.title.strip()
    exam.description = (payload.description or "").strip() or None
    exam.duration_minutes = payload.duration_minutes
    exam.status = payload.status
    if payload.task_ids:
        exam.task_ids = payload.task_ids
    elif payload.auto_numbers:
        exam.task_ids = await _collect_tasks(session, payload.auto_numbers, payload.subject_slug)

    await session.commit()
    return await _mock_out(session, exam)


@router.delete("/mocks/{exam_id}")
async def hide_mock(exam_id: int, session: DbSession, admin: AdminUser) -> dict:
    exam = await session.get(MockExam, exam_id)
    if exam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "пробник не найден")
    exam.status = MockStatus.HIDDEN
    await session.commit()
    return {"ok": True}


class IdeaOut(BaseModel):
    id: int
    message: str
    page: str | None
    author: str
    status: str
    created_at: datetime


@router.get("/ideas", response_model=list[IdeaOut])
async def list_ideas(session: DbSession, admin: AdminUser, only_new: bool = True) -> list[IdeaOut]:
    stmt = select(Idea).order_by(Idea.id.desc()).limit(100)
    if only_new:
        stmt = stmt.where(Idea.status == IdeaStatus.NEW)

    out: list[IdeaOut] = []
    for idea in await session.scalars(stmt):
        author = await session.get(User, idea.user_id) if idea.user_id else None
        out.append(
            IdeaOut(
                id=idea.id,
                message=idea.message,
                page=idea.page,
                author=author.display_name if author else "аноним",
                status=idea.status.value,
                created_at=idea.created_at,
            )
        )
    return out


@router.post("/ideas/{idea_id}/{action}")
async def resolve_idea(idea_id: int, action: str, session: DbSession, admin: AdminUser) -> dict:
    if action not in ("accept", "decline"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "действие не поддерживается")
    idea = await session.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "идея не найдена")
    idea.status = IdeaStatus.ACCEPTED if action == "accept" else IdeaStatus.DECLINED
    await session.commit()
    return {"ok": True}


class TaskPickRow(BaseModel):
    id: int
    number: int
    statement: str
    answer_value: str
    difficulty: int


@router.get("/tasks/pick/{number}", response_model=list[TaskPickRow])
async def pick_tasks(
    number: int, session: DbSession, admin: AdminUser, q: str | None = None, limit: int = 40
) -> list[TaskPickRow]:
    """Задачи одного номера — для ручного набора пробника."""
    stmt = (
        select(Task)
        .join(TaskType, TaskType.id == Task.task_type_id)
        .where(Task.status == TaskStatus.LIVE, TaskType.number == number)
        .order_by(Task.id.desc())
        .limit(limit)
    )
    if q:
        stmt = stmt.where(Task.statement.ilike(f"%{q}%"))

    return [
        TaskPickRow(
            id=t.id,
            number=number,
            statement=t.statement,
            answer_value=str((t.answer_payload or {}).get("value", "")),
            difficulty=t.difficulty,
        )
        for t in await session.scalars(stmt)
    ]


# ------------------------------------------- отладка магазина (только для себя)

class CoinsIn(BaseModel):
    amount: int = Field(default=1000, ge=-100000, le=100000)


@router.post("/self/coins")
async def grant_self_coins(payload: CoinsIn, session: DbSession, admin: AdminUser) -> dict:
    """Начислить монеты **себе**. Чужой баланс трогать нельзя даже админу —
    иначе однажды это случится по ошибке и разбираться будет невозможно."""
    from app.core.coins import award
    from app.models import CoinReason

    await award(session, admin, CoinReason.ADMIN, amount=payload.amount, note="ручное начисление")
    await session.commit()
    await session.refresh(admin)
    return {"coins": admin.coins}


@router.post("/self/reset-purchases")
async def reset_self_purchases(session: DbSession, admin: AdminUser) -> dict:
    """Сбросить свои покупки — чтобы прогонять магазин заново."""
    from app.models import UserItem

    mine = list(await session.scalars(select(UserItem).where(UserItem.user_id == admin.id)))
    for row in mine:
        await session.delete(row)
    await session.commit()
    return {"removed": len(mine)}
