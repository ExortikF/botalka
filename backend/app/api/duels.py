"""Дуэль по ссылке.

Оба игрока решают **один и тот же набор задач**, но каждый в своё время. Побеждает
тот, у кого больше верных ответов; при равенстве — кто потратил меньше времени.

Реалтайма здесь нет намеренно: вызов по ссылке работает при пустом онлайне, а живой
матч имеет смысл, только когда игроков много.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import DbSession, PlayerUser
from app.api.quiz import QuizOut, _to_task_out
from app.models import Attempt, Duel, DuelState, Quiz, QuizMode, Task, TaskStatus, TaskType, User

router = APIRouter(prefix="/api/duels", tags=["duels"])

DUEL_LENGTH = 7
DUEL_TTL_HOURS = 48
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # без похожих символов


class CreateDuelIn(BaseModel):
    subject: str = "math_prof"
    task_type_ids: list[int] = Field(default_factory=list)
    length: int = Field(default=DUEL_LENGTH, ge=3, le=30)
    # если задан — вызов адресный: принять его сможет только этот человек
    opponent_id: int | None = None


class DuelSideOut(BaseModel):
    name: str
    score: int | None
    time_ms: int | None
    finished: bool


class DuelOut(BaseModel):
    code: str
    state: str
    total: int
    challenger: DuelSideOut
    opponent: DuelSideOut | None
    winner: str | None          # «challenger» | «opponent» | «draw» | None
    your_side: str | None       # чья это дуэль с точки зрения запрашивающего
    can_play: bool              # можно ли начать своё прохождение
    expires_at: datetime | None


async def _new_code(session: DbSession) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(ALPHABET) for _ in range(7))
        if not await session.scalar(select(Duel.id).where(Duel.code == code)):
            return code
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "не удалось создать код")


async def _side_stats(session: DbSession, quiz_id: int | None) -> tuple[int | None, int | None, bool]:
    """Счёт и суммарное время по квизу одной стороны."""
    if quiz_id is None:
        return None, None, False
    quiz = await session.get(Quiz, quiz_id)
    if quiz is None:
        return None, None, False
    time_ms = (
        await session.scalar(
            select(func.coalesce(func.sum(Attempt.time_spent_ms), 0)).where(
                Attempt.quiz_id == quiz.id
            )
        )
    ) or 0
    return quiz.score, int(time_ms), quiz.finished_at is not None


async def _refresh(session: DbSession, duel: Duel) -> None:
    """Пересчитывает итог дуэли по завершённым квизам обеих сторон."""
    c_score, c_time, c_done = await _side_stats(session, duel.challenger_quiz_id)
    o_score, o_time, o_done = await _side_stats(session, duel.opponent_quiz_id)

    duel.challenger_score, duel.challenger_time_ms = c_score, c_time
    duel.opponent_score, duel.opponent_time_ms = o_score, o_time

    if c_done and o_done:
        duel.state = DuelState.FINISHED
        duel.finished_at = duel.finished_at or datetime.now(UTC)
        if c_score != o_score:
            duel.winner_id = duel.challenger_id if c_score > o_score else duel.opponent_id
        elif c_time != o_time:
            # при равном счёте выигрывает тот, кто решал быстрее
            duel.winner_id = duel.challenger_id if c_time < o_time else duel.opponent_id
        else:
            duel.winner_id = None
    await session.commit()


async def _to_out(session: DbSession, duel: Duel, user: User) -> DuelOut:
    challenger = await session.get(User, duel.challenger_id)
    opponent = await session.get(User, duel.opponent_id) if duel.opponent_id else None

    _, _, c_done = await _side_stats(session, duel.challenger_quiz_id)
    _, _, o_done = await _side_stats(session, duel.opponent_quiz_id)

    if user.id == duel.challenger_id:
        your_side = "challenger"
        can_play = not c_done
    elif duel.opponent_id in (None, user.id):
        your_side = "opponent" if duel.opponent_id == user.id else None
        can_play = not o_done
    else:
        your_side = None
        can_play = False

    winner = None
    if duel.state is DuelState.FINISHED:
        if duel.winner_id is None:
            winner = "draw"
        else:
            winner = "challenger" if duel.winner_id == duel.challenger_id else "opponent"

    return DuelOut(
        code=duel.code,
        state=duel.state.value,
        total=len(duel.task_ids),
        challenger=DuelSideOut(
            name=challenger.display_name if challenger else "—",
            score=duel.challenger_score,
            time_ms=duel.challenger_time_ms,
            finished=c_done,
        ),
        opponent=(
            DuelSideOut(
                name=opponent.display_name,
                score=duel.opponent_score,
                time_ms=duel.opponent_time_ms,
                finished=o_done,
            )
            if opponent
            else None
        ),
        winner=winner,
        your_side=your_side,
        can_play=can_play,
        expires_at=duel.expires_at,
    )


@router.post("", response_model=DuelOut, status_code=status.HTTP_201_CREATED)
async def create_duel(payload: CreateDuelIn, session: DbSession, user: PlayerUser) -> DuelOut:
    stmt = (
        select(Task)
        .join(TaskType, TaskType.id == Task.task_type_id)
        .where(Task.status == TaskStatus.LIVE, TaskType.subject.has(slug=payload.subject))
    )
    if payload.task_type_ids:
        stmt = stmt.where(Task.task_type_id.in_(payload.task_type_ids))

    tasks = list((await session.scalars(stmt.order_by(func.random()).limit(payload.length))).all())
    if len(tasks) < 3:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "мало задач для дуэли — выберите другие темы"
        )

    if payload.opponent_id is not None:
        # вызвать можно только друга — иначе можно спамить вызовами кому угодно
        from app.models import Friendship, FriendshipState

        friendship = await session.scalar(
            select(Friendship).where(
                Friendship.state == FriendshipState.ACCEPTED,
                (
                    (Friendship.from_user_id == user.id)
                    & (Friendship.to_user_id == payload.opponent_id)
                )
                | (
                    (Friendship.from_user_id == payload.opponent_id)
                    & (Friendship.to_user_id == user.id)
                ),
            )
        )
        if friendship is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "вызвать можно только друга")

    duel = Duel(
        code=await _new_code(session),
        task_ids=[t.id for t in tasks],
        challenger_id=user.id,
        opponent_id=payload.opponent_id,
        expires_at=datetime.now(UTC) + timedelta(hours=DUEL_TTL_HOURS),
    )
    session.add(duel)
    await session.commit()
    await session.refresh(duel)
    return await _to_out(session, duel, user)


async def _load(session: DbSession, code: str) -> Duel:
    duel = await session.scalar(select(Duel).where(Duel.code == code))
    if duel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "дуэль не найдена")
    return duel


@router.get("/{code}", response_model=DuelOut)
async def get_duel(code: str, session: DbSession, user: PlayerUser) -> DuelOut:
    duel = await _load(session, code)
    await _refresh(session, duel)
    return await _to_out(session, duel, user)


@router.post("/{code}/play", response_model=QuizOut)
async def play_duel(code: str, session: DbSession, user: PlayerUser) -> QuizOut:
    """Начать своё прохождение. Задачи те же самые и в том же порядке."""
    duel = await _load(session, code)

    if duel.expires_at and duel.expires_at < datetime.now(UTC) and duel.state is DuelState.WAITING:
        duel.state = DuelState.EXPIRED
        await session.commit()
        raise HTTPException(status.HTTP_410_GONE, "срок вызова истёк")

    is_challenger = user.id == duel.challenger_id
    if not is_challenger:
        if duel.opponent_id not in (None, user.id):
            raise HTTPException(status.HTTP_409_CONFLICT, "вызов уже принят другим игроком")
        duel.opponent_id = user.id

    existing_id = duel.challenger_quiz_id if is_challenger else duel.opponent_quiz_id
    if existing_id is not None:
        quiz = await session.get(Quiz, existing_id)
        if quiz is not None and quiz.finished_at is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "ты уже прошёл эту дуэль")
    else:
        quiz = Quiz(
            user_id=user.id,
            mode=QuizMode.DUEL,
            task_ids=list(duel.task_ids),
            duel_id=duel.id,
        )
        session.add(quiz)
        await session.flush()
        if is_challenger:
            duel.challenger_quiz_id = quiz.id
        else:
            duel.opponent_quiz_id = quiz.id

    await session.commit()
    await session.refresh(quiz)

    tasks = []
    for task_id in duel.task_ids:
        task = await session.get(Task, task_id)
        if task is None:
            continue
        await session.refresh(task, ["task_type"])
        tasks.append(task)

    return QuizOut(id=quiz.id, mode=quiz.mode.value, tasks=[_to_task_out(t) for t in tasks])


class DuelListItem(BaseModel):
    code: str
    state: str
    role: str
    opponent_name: str | None
    your_score: int | None
    their_score: int | None
    outcome: str | None  # win | loss | draw | None
    created_at: datetime


@router.get("", response_model=list[DuelListItem])
async def my_duels(session: DbSession, user: PlayerUser) -> list[DuelListItem]:
    duels = list(
        await session.scalars(
            select(Duel)
            .where((Duel.challenger_id == user.id) | (Duel.opponent_id == user.id))
            .order_by(Duel.id.desc())
            .limit(30)
        )
    )

    items: list[DuelListItem] = []
    for duel in duels:
        mine_is_challenger = duel.challenger_id == user.id
        other_id = duel.opponent_id if mine_is_challenger else duel.challenger_id
        other = await session.get(User, other_id) if other_id else None

        your_score = duel.challenger_score if mine_is_challenger else duel.opponent_score
        their_score = duel.opponent_score if mine_is_challenger else duel.challenger_score

        outcome = None
        if duel.state is DuelState.FINISHED:
            if duel.winner_id is None:
                outcome = "draw"
            else:
                outcome = "win" if duel.winner_id == user.id else "loss"

        items.append(
            DuelListItem(
                code=duel.code,
                state=duel.state.value,
                role="challenger" if mine_is_challenger else "opponent",
                opponent_name=other.display_name if other else None,
                your_score=your_score,
                their_score=their_score,
                outcome=outcome,
                created_at=duel.created_at,
            )
        )
    return items
