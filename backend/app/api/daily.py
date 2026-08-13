"""Задача дня — одна на всех, новая каждые сутки.

Смысл в том, чтобы был повод открыть сайт, даже когда заниматься не хочется:
одна задача, всем одинаковая, и таблица по времени решения. Задача выбирается
детерминированно по дате, поэтому её не нужно нигде хранить и назначать руками.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.quiz import STREAK_TZ, _correct_answer_text, _source_label
from app.core.answers import check_answer
from app.core.coins import award
from app.api.deps import DbSession, PlayerUser
from app.models import Attempt, CoinReason, DailyStart, Task, TaskStatus, User

router = APIRouter(prefix="/api/daily", tags=["daily"])

REWARD = 20  # заметно больше обычной задачи: это ежедневный крючок, а не фарм
LIMIT_SECONDS = 5 * 60  # столько даётся на решение с момента открытия условия


def today() -> date:
    return datetime.now(STREAK_TZ).date()


def _seed(day: date) -> int:
    """Номер дня — он же индекс в списке задач. Обычный хеш даты не годится:
    он меняется от запуска к запуску, и задача дня прыгала бы после рестарта."""
    return day.toordinal()


async def _task_of(session: DbSession, day: date) -> Task:
    ids = list(
        await session.scalars(
            select(Task.id).where(Task.status == TaskStatus.LIVE).order_by(Task.id)
        )
    )
    if not ids:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "в банке нет задач")

    task = await session.get(Task, ids[_seed(day) % len(ids)])
    assert task is not None
    await session.refresh(task, ["task_type"])
    return task


class DailyOut(BaseModel):
    day: str
    task_id: int
    task_type_number: int
    task_type_title: str
    statement: str
    image_url: str | None
    answer_type: str
    source: str | None

    solved: bool
    started: bool
    seconds_left: int | None  # None, пока не начал
    limit_seconds: int
    your_seconds: int | None
    your_place: int | None
    solved_today: int
    reward: int
    next_in_hours: int


class DailyRow(BaseModel):
    place: int
    user_id: int
    display_name: str
    seconds: int
    is_you: bool


class DailyAnswerIn(BaseModel):
    answer: str = Field(max_length=512)
    time_spent_ms: int = 0


class DailyAnswerOut(BaseModel):
    is_correct: bool
    expired: bool
    correct_answer: str
    solution: str | None
    coins: int
    seconds: int
    place: int | None


async def _attempts_today(session: DbSession, task_id: int) -> list[Attempt]:
    start = datetime.combine(today(), datetime.min.time(), STREAK_TZ).astimezone(UTC)
    return list(
        await session.scalars(
            select(Attempt).where(
                Attempt.task_id == task_id,
                Attempt.created_at >= start,
                Attempt.quiz_id.is_(None),
            )
        )
    )


def _ranked(attempts: list[Attempt]) -> list[Attempt]:
    """Только первая верная попытка каждого, отсортированная по времени решения."""
    best: dict[int, Attempt] = {}
    for attempt in sorted(attempts, key=lambda a: a.id):
        if attempt.is_correct and attempt.user_id not in best:
            best[attempt.user_id] = attempt
    return sorted(best.values(), key=lambda a: a.time_spent_ms)


async def _start_of(session: DbSession, user_id: int, day: date) -> DailyStart | None:
    return await session.scalar(
        select(DailyStart).where(DailyStart.user_id == user_id, DailyStart.day == day)
    )


def _left(start: DailyStart | None) -> int | None:
    if start is None:
        return None
    spent = (datetime.now(UTC) - start.started_at.replace(tzinfo=UTC)).total_seconds()
    return max(0, round(LIMIT_SECONDS - spent))


@router.post("/start", response_model=DailyOut)
async def start(session: DbSession, user: PlayerUser) -> DailyOut:
    """Открывает условие и запускает отсчёт. Повторный вызов ничего не сбрасывает —
    иначе таймер обнулялся бы при каждом возврате на вкладку."""
    day = today()
    if await _start_of(session, user.id, day) is None:
        session.add(DailyStart(user_id=user.id, day=day))
        await session.commit()
    return await daily(session, user)


@router.get("", response_model=DailyOut)
async def daily(session: DbSession, user: PlayerUser) -> DailyOut:
    day = today()
    task = await _task_of(session, day)
    ranked = _ranked(await _attempts_today(session, task.id))
    start = await _start_of(session, user.id, day)

    mine = next((i for i, a in enumerate(ranked) if a.user_id == user.id), None)
    tomorrow = datetime.combine(day + timedelta(days=1), datetime.min.time(), STREAK_TZ)

    return DailyOut(
        day=day.isoformat(),
        task_id=task.id,
        task_type_number=task.task_type.number,
        task_type_title=task.task_type.title,
        statement=task.statement if (start is not None or mine is not None) else "",
        image_url=task.image_url if (start is not None or mine is not None) else None,
        answer_type=task.answer_type.value,
        source=_source_label(task),
        solved=mine is not None,
        started=start is not None,
        seconds_left=_left(start),
        limit_seconds=LIMIT_SECONDS,
        your_seconds=round(ranked[mine].time_spent_ms / 1000) if mine is not None else None,
        your_place=mine + 1 if mine is not None else None,
        solved_today=len(ranked),
        reward=REWARD,
        next_in_hours=max(1, round((tomorrow - datetime.now(STREAK_TZ)).total_seconds() / 3600)),
    )


@router.get("/leaderboard", response_model=list[DailyRow])
async def leaderboard(session: DbSession, user: PlayerUser) -> list[DailyRow]:
    task = await _task_of(session, today())
    rows = []
    for place, attempt in enumerate(_ranked(await _attempts_today(session, task.id))[:20], 1):
        author = await session.get(User, attempt.user_id)
        rows.append(
            DailyRow(
                place=place,
                user_id=attempt.user_id,
                display_name=author.display_name if author else "неизвестно",
                seconds=round(attempt.time_spent_ms / 1000),
                is_you=attempt.user_id == user.id,
            )
        )
    return rows


@router.post("/answer", response_model=DailyAnswerOut)
async def answer(payload: DailyAnswerIn, session: DbSession, user: PlayerUser) -> DailyAnswerOut:
    day = today()
    task = await _task_of(session, day)

    mine = [a for a in await _attempts_today(session, task.id) if a.user_id == user.id]
    if any(a.is_correct for a in mine):
        raise HTTPException(status.HTTP_409_CONFLICT, "задача дня уже решена")

    start = await _start_of(session, user.id, day)
    if start is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "сначала открой условие")

    # Время считает сервер: клиентскому таймеру нельзя верить, раз от него
    # зависит место в таблице.
    spent = (datetime.now(UTC) - start.started_at.replace(tzinfo=UTC)).total_seconds()
    seconds = round(spent)
    expired = spent > LIMIT_SECONDS

    is_correct = not expired and check_answer(
        task.answer_type, task.answer_payload, payload.answer
    )

    session.add(
        Attempt(
            user_id=user.id,
            task_id=task.id,
            answer_raw=(payload.answer or "—")[:512],
            is_correct=is_correct,
            used_hint=False,
            time_spent_ms=round(spent * 1000),
        )
    )

    coins = 0
    if is_correct:
        coins = await award(session, user, CoinReason.DAILY_TASK, amount=REWARD, note=task.slug)

    await session.commit()

    place = None
    if is_correct:
        ranked = _ranked(await _attempts_today(session, task.id))
        place = next((i + 1 for i, a in enumerate(ranked) if a.user_id == user.id), None)

    return DailyAnswerOut(
        is_correct=is_correct,
        expired=expired,
        correct_answer=_correct_answer_text(task),
        solution=task.solution,
        coins=coins,
        seconds=seconds,
        place=place,
    )
