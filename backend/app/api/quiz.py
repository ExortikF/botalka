from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import DbSession, PlayerUser
from app.core.answers import check_answer
from app.models import Attempt, Quiz, QuizMode, Task, TaskStatus, TaskType, User

router = APIRouter(prefix="/api", tags=["quiz"])

QUIZ_LENGTH = 10

# «Сегодня» для серии дней — по Москве. По UTC день заканчивался бы в 03:00 МСК,
# и вечернее занятие засчитывалось бы следующим днём.
STREAK_TZ = ZoneInfo("Europe/Moscow")


class TaskTypeOut(BaseModel):
    id: int
    number: int
    title: str
    tasks_count: int


class TaskOut(BaseModel):
    """То, что видит игрок. Правильного ответа здесь нет и быть не должно."""

    id: int
    task_type_number: int
    task_type_title: str
    statement: str
    image_url: str | None
    answer_type: str
    hints: list[str]
    source: str | None


class QuizOut(BaseModel):
    id: int
    mode: str
    tasks: list[TaskOut]


class AnswerIn(BaseModel):
    task_id: int
    answer: str = Field(max_length=512)
    time_spent_ms: int = 0
    used_hint: bool = False


class AnswerOut(BaseModel):
    is_correct: bool
    used_hint: bool
    correct_answer: str
    solution: str | None
    score: int


class QuizResultItem(BaseModel):
    task_id: int
    statement: str
    task_type_number: int
    your_answer: str
    correct_answer: str
    is_correct: bool
    used_hint: bool
    solution: str | None


class QuizResultOut(BaseModel):
    quiz_id: int
    score: int
    total: int
    finished: bool
    items: list[QuizResultItem]
    streak_days: int


def _to_task_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        task_type_number=task.task_type.number,
        task_type_title=task.task_type.title,
        statement=task.statement,
        image_url=task.image_url,
        answer_type=task.answer_type.value,
        hints=task.hints or [],
        source=_source_label(task),
    )


SOURCE_LABELS = {
    "fipi": "Открытый банк ФИПИ",
    "exam": "Реальный ЕГЭ",
    "demo": "Демоверсия ФИПИ",
    "book": "Сборник",
}


def _source_label(task: Task) -> str | None:
    """Короткая подпись под условием: ученику важно знать, что задача настоящая."""
    if task.source:
        return task.source
    kind = task.source_kind.value
    if kind == "own":
        return None
    parts = [SOURCE_LABELS.get(kind, "Источник")]
    if task.source_year:
        parts.append(str(task.source_year))
    if task.source_ref:
        parts.append(f"№ {task.source_ref}")
    return ", ".join(parts)


def _correct_answer_text(task: Task) -> str:
    return str((task.answer_payload or {}).get("value", ""))


@router.get("/task-types", response_model=list[TaskTypeOut])
async def list_task_types(session: DbSession, subject: str = "math_prof") -> list[TaskTypeOut]:
    """Типы заданий с количеством живых задач — для выбора режима тренировки."""
    # outer join: номера без задач тоже показываем — по ним видно, чего в банке нет
    stmt = (
        select(TaskType, func.count(Task.id))
        .join(
            Task,
            (Task.task_type_id == TaskType.id) & (Task.status == TaskStatus.LIVE),
            isouter=True,
        )
        .where(TaskType.subject.has(slug=subject))
        .group_by(TaskType.id)
        .order_by(TaskType.number)
    )
    rows = (await session.execute(stmt)).all()
    return [
        TaskTypeOut(id=tt.id, number=tt.number, title=tt.title, tasks_count=count)
        for tt, count in rows
    ]


class TypeSelection(BaseModel):
    """Сколько задач взять из конкретного номера."""

    task_type_id: int
    count: int = Field(default=5, ge=1, le=20)


class QuizStartIn(BaseModel):
    """Конструктор квиза: пресет, список номеров или номера с количествами."""

    subject: str = "math_prof"
    task_type_ids: list[int] = Field(default_factory=list)
    selection: list[TypeSelection] = Field(default_factory=list)
    preset: str | None = None  # weak | mistakes | unsolved
    length: int = QUIZ_LENGTH


async def _weak_type_ids(session: DbSession, user: User, subject: str) -> list[int]:
    """Номера, где процент верных ниже всего. Нужно хотя бы две попытки —
    иначе одна случайная ошибка объявляет тему слабой."""
    rows = (
        await session.execute(
            select(
                TaskType.id,
                func.count(Attempt.id).label("total"),
                func.count(Attempt.id).filter(Attempt.is_correct).label("correct"),
            )
            .join(Task, Task.task_type_id == TaskType.id)
            .join(Attempt, Attempt.task_id == Task.id)
            .where(Attempt.user_id == user.id, TaskType.subject.has(slug=subject))
            .group_by(TaskType.id)
            .having(func.count(Attempt.id) >= 2)
        )
    ).all()
    ranked = sorted(rows, key=lambda r: r.correct / r.total)
    return [r.id for r in ranked if r.correct < r.total][:4]


async def _unsolved_task_ids(session: DbSession, user: User, subject: str) -> list[int]:
    """Задачи, которые пользователь ни разу не решил верно (включая нетронутые)."""
    solved = select(func.distinct(Attempt.task_id)).where(
        Attempt.user_id == user.id, Attempt.is_correct.is_(True)
    )
    rows = await session.scalars(
        select(Task.id)
        .join(TaskType, TaskType.id == Task.task_type_id)
        .where(
            Task.id.not_in(solved),
            Task.status == TaskStatus.LIVE,
            TaskType.subject.has(slug=subject),
        )
    )
    return list(rows)


async def _mistake_task_ids(session: DbSession, user: User, subject: str) -> list[int]:
    """Задачи, где пользователь уже ошибался и с тех пор не решил верно."""
    wrong = select(func.distinct(Attempt.task_id)).where(
        Attempt.user_id == user.id, Attempt.is_correct.is_(False)
    )
    fixed = select(func.distinct(Attempt.task_id)).where(
        Attempt.user_id == user.id, Attempt.is_correct.is_(True)
    )
    rows = await session.scalars(
        select(Task.id)
        .join(TaskType, TaskType.id == Task.task_type_id)
        .where(
            Task.id.in_(wrong),
            Task.id.not_in(fixed),
            Task.status == TaskStatus.LIVE,
            TaskType.subject.has(slug=subject),
        )
    )
    return list(rows)


@router.post("/quiz/start", response_model=QuizOut)
async def start_quiz(payload: QuizStartIn, session: DbSession, user: PlayerUser) -> QuizOut:
    length = max(1, min(payload.length, 30))

    stmt = (
        select(Task)
        .join(TaskType, TaskType.id == Task.task_type_id)
        .where(Task.status == TaskStatus.LIVE, TaskType.subject.has(slug=payload.subject))
    )

    type_ids = list(payload.task_type_ids)

    # Пустой пресет — это не повод молча подсунуть обычный квиз: пользователь
    # просил конкретный набор и должен понять, почему его нет.
    if payload.preset == "weak":
        type_ids = await _weak_type_ids(session, user, payload.subject)
        if not type_ids:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "слабых тем пока нет — порешай обычный квиз, и они появятся",
            )
    elif payload.preset == "unsolved":
        task_ids = await _unsolved_task_ids(session, user, payload.subject)
        if not task_ids:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "нерешённых задач не осталось — весь банк пройден",
            )
        stmt = stmt.where(Task.id.in_(task_ids))
    elif payload.preset == "mistakes":
        task_ids = await _mistake_task_ids(session, user, payload.subject)
        if not task_ids:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "нерешённых ошибок нет — все прошлые ошибки уже разобраны",
            )
        stmt = stmt.where(Task.id.in_(task_ids))

    if payload.selection and not payload.preset:
        # по каждому номеру берём ровно столько, сколько попросили
        tasks = []
        for item in payload.selection:
            chunk = await session.scalars(
                stmt.where(Task.task_type_id == item.task_type_id)
                .order_by(func.random())
                .limit(item.count)
            )
            tasks.extend(chunk.all())
        random.shuffle(tasks)
    else:
        if type_ids:
            stmt = stmt.where(Task.task_type_id.in_(type_ids))
        tasks = list((await session.scalars(stmt.order_by(func.random()).limit(length))).all())

    if not tasks:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "по такому набору задач не нашлось")

    quiz = Quiz(user_id=user.id, mode=QuizMode.SOLO, task_ids=[t.id for t in tasks])
    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)

    for task in tasks:
        await session.refresh(task, ["task_type"])

    return QuizOut(id=quiz.id, mode=quiz.mode.value, tasks=[_to_task_out(t) for t in tasks])


def _bump_streak(user: User) -> None:
    today = datetime.now(STREAK_TZ).date()
    if user.streak_last_date == today:
        return
    yesterday = today - timedelta(days=1)
    user.streak_days = user.streak_days + 1 if user.streak_last_date == yesterday else 1
    user.streak_last_date = today


@router.post("/quiz/{quiz_id}/answer", response_model=AnswerOut)
async def submit_answer(
    quiz_id: int, payload: AnswerIn, session: DbSession, user: PlayerUser
) -> AnswerOut:
    quiz = await session.get(Quiz, quiz_id)
    if quiz is None or quiz.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "квиз не найден")
    if payload.task_id not in quiz.task_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "задача не из этого квиза")

    already = await session.scalar(
        select(Attempt).where(Attempt.quiz_id == quiz.id, Attempt.task_id == payload.task_id)
    )
    if already is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "на эту задачу уже отвечали")

    task = await session.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не найдена")

    is_correct = check_answer(task.answer_type, task.answer_payload, payload.answer)

    session.add(
        Attempt(
            user_id=user.id,
            task_id=task.id,
            quiz_id=quiz.id,
            answer_raw=payload.answer[:512],
            is_correct=is_correct,
            used_hint=payload.used_hint,
            time_spent_ms=max(0, payload.time_spent_ms),
        )
    )
    if is_correct:
        quiz.score += 1

    answered = await session.scalar(
        select(func.count(Attempt.id)).where(Attempt.quiz_id == quiz.id)
    )
    # +1 — текущая попытка ещё не в базе на момент подсчёта
    quiz_just_finished = (answered or 0) + 1 >= len(quiz.task_ids)
    if quiz_just_finished:
        quiz.finished_at = datetime.now(UTC)
        _bump_streak(user)

    await session.commit()

    if quiz_just_finished and quiz.duel_id is not None:
        # импорт здесь, чтобы не было кольцевой зависимости модулей
        from app.api.duels import _refresh
        from app.models import Duel

        duel = await session.get(Duel, quiz.duel_id)
        if duel is not None:
            await _refresh(session, duel)

    return AnswerOut(
        is_correct=is_correct,
        used_hint=payload.used_hint,
        correct_answer=_correct_answer_text(task),
        solution=task.solution,
        score=quiz.score,
    )


@router.get("/quiz/{quiz_id}/result", response_model=QuizResultOut)
async def quiz_result(quiz_id: int, session: DbSession, user: PlayerUser) -> QuizResultOut:
    quiz = await session.get(Quiz, quiz_id)
    if quiz is None or quiz.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "квиз не найден")

    attempts = {
        a.task_id: a
        for a in (await session.scalars(select(Attempt).where(Attempt.quiz_id == quiz.id))).all()
    }

    items: list[QuizResultItem] = []
    for task_id in quiz.task_ids:
        task = await session.get(Task, task_id)
        if task is None:
            continue
        await session.refresh(task, ["task_type"])
        attempt = attempts.get(task_id)
        items.append(
            QuizResultItem(
                task_id=task.id,
                statement=task.statement,
                task_type_number=task.task_type.number,
                your_answer=attempt.answer_raw if attempt else "",
                correct_answer=_correct_answer_text(task),
                is_correct=bool(attempt and attempt.is_correct),
                used_hint=bool(attempt and attempt.used_hint),
                solution=task.solution,
            )
        )

    return QuizResultOut(
        quiz_id=quiz.id,
        score=quiz.score,
        total=len(quiz.task_ids),
        finished=quiz.finished_at is not None,
        items=items,
        streak_days=user.streak_days,
    )


class ReportIn(BaseModel):
    message: str = Field(min_length=3, max_length=1000)
    given_answer: str | None = Field(default=None, max_length=512)


@router.post("/tasks/{task_id}/report", status_code=status.HTTP_201_CREATED)
async def report_task(
    task_id: int, payload: ReportIn, session: DbSession, user: PlayerUser
) -> dict:
    """«Нашли ошибку?» — жалоба уходит в админку, задача остаётся в выдаче.

    Автоматически снимать задачу нельзя: так любой сможет вычистить банк.
    """
    from app.models import TaskReport

    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не найдена")

    session.add(
        TaskReport(
            task_id=task_id,
            user_id=user.id,
            message=payload.message.strip(),
            given_answer=payload.given_answer,
        )
    )
    await session.commit()
    return {"ok": True}


class IdeaIn(BaseModel):
    message: str = Field(min_length=5, max_length=2000)
    page: str | None = Field(default=None, max_length=200)


@router.post("/ideas", status_code=status.HTTP_201_CREATED)
async def submit_idea(payload: IdeaIn, session: DbSession, user: PlayerUser) -> dict:
    """«Есть идеи по улучшению сайта?» — предложение уходит в админку."""
    from app.models import Idea

    session.add(
        Idea(user_id=user.id, message=payload.message.strip(), page=payload.page)
    )
    await session.commit()
    return {"ok": True}


class StatsRow(BaseModel):
    task_type_number: int
    task_type_title: str
    total: int
    correct: int


@router.get("/stats", response_model=list[StatsRow])
async def stats(session: DbSession, user: PlayerUser) -> list[StatsRow]:
    """Процент решаемости по типам заданий — что именно проседает."""
    stmt = (
        select(
            TaskType.number,
            TaskType.title,
            func.count(Attempt.id),
            func.count(Attempt.id).filter(Attempt.is_correct),
        )
        .join(Task, Task.id == Attempt.task_id)
        .join(TaskType, TaskType.id == Task.task_type_id)
        .where(Attempt.user_id == user.id)
        .group_by(TaskType.number, TaskType.title)
        .order_by(TaskType.number)
    )
    rows = (await session.execute(stmt)).all()
    return [
        StatsRow(task_type_number=n, task_type_title=t, total=total, correct=correct)
        for n, t, total, correct in rows
    ]
