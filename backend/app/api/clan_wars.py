"""Клановые войны.

Один клан вызывает другой, обе стороны ставят одинаковую сумму из казны.
Пять часов на общий набор случайных задач; очко — за задачу, закрытую **первым
в своём клане**. Победитель забирает обе ставки, при ничьей ставки возвращаются.

Почему из казны, а не из личных монет: проигрыш иначе бьёт по тем, кто в войну
не вписывался и ничего не решал, а решение о вызове принимает глава.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.api.clans import MIN_FOR_BOARD, _membership
from app.api.deps import DbSession, PlayerUser
from app.api.quiz import _correct_answer_text
from app.core.answers import check_answer
from app.core.coins import award
from app.models import (
    Clan,
    ClanMember,
    ClanRole,
    ClanWar,
    ClanWarSolve,
    CoinReason,
    Task,
    TaskStatus,
    User,
    WarState,
)

router = APIRouter(prefix="/api/clans/wars", tags=["clan-wars"])

DURATION = timedelta(hours=5)
ACCEPT_WINDOW = timedelta(hours=24)  # столько живёт неотвеченный вызов
TASKS = 20
MIN_STAKE, MAX_STAKE = 50, 5000


class WarTask(BaseModel):
    task_id: int
    number: int
    title: str
    statement: str
    solved_by_us: bool
    solved_by_them: bool
    solver: str | None  # кто из наших закрыл


class WarSide(BaseModel):
    clan_id: int
    name: str
    tag: str
    color: str
    score: int


class WarOut(BaseModel):
    id: int
    state: str
    stake: int
    us: WarSide
    them: WarSide
    you_challenged: bool
    seconds_left: int | None
    tasks: list[WarTask]
    can_answer: bool
    winner: str | None  # «мы», «они», «ничья»
    prize: int


async def _clan_of(session: DbSession, user: User) -> Clan:
    member = await _membership(session, user.id)
    if member is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "ты не в клане")
    clan = await session.scalar(
        select(Clan)
        .where(Clan.id == member.clan_id)
        .options(selectinload(Clan.members))
        .execution_options(populate_existing=True)
    )
    assert clan is not None
    return clan


async def _require_officer(session: DbSession, user: User) -> Clan:
    member = await _membership(session, user.id)
    if member is None or member.role is ClanRole.MEMBER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "решает глава или офицер")
    return await _clan_of(session, user)


async def _scores(session: DbSession, war: ClanWar) -> dict[int, int]:
    rows = await session.scalars(
        select(ClanWarSolve.clan_id).where(ClanWarSolve.war_id == war.id)
    )
    scores = {war.challenger_id: 0, war.opponent_id: 0}
    for clan_id in rows:
        scores[clan_id] = scores.get(clan_id, 0) + 1
    return scores


async def settle(session: DbSession, war: ClanWar) -> None:
    """Подводит итоги, когда время вышло.

    Вызывается лениво при чтении, а не по таймеру: отдельный планировщик ради
    одного действия — лишняя точка отказа, а результат нужен ровно тогда, когда
    на войну кто-то смотрит.
    """
    if war.state is not WarState.ACTIVE or war.ends_at is None:
        return
    if datetime.now(UTC) < war.ends_at.replace(tzinfo=UTC):
        return

    scores = await _scores(session, war)
    challenger = await session.get(Clan, war.challenger_id)
    opponent = await session.get(Clan, war.opponent_id)
    if challenger is None or opponent is None:
        war.state = WarState.EXPIRED
        await session.commit()
        return

    ours, theirs = scores[war.challenger_id], scores[war.opponent_id]
    if ours == theirs:
        # Ничья: ставки возвращаются, никто ничего не теряет.
        challenger.coins += war.stake
        opponent.coins += war.stake
    else:
        winner = challenger if ours > theirs else opponent
        winner.coins += war.stake * 2
        war.winner_id = winner.id

    war.state = WarState.FINISHED
    await session.commit()


async def _out(session: DbSession, war: ClanWar, user: User, clan: Clan) -> WarOut:
    await settle(session, war)

    us_id = clan.id
    them_id = war.opponent_id if us_id == war.challenger_id else war.challenger_id
    them = await session.get(Clan, them_id)
    scores = await _scores(session, war)

    solves = list(
        await session.scalars(select(ClanWarSolve).where(ClanWarSolve.war_id == war.id))
    )
    ours = {s.task_id: s for s in solves if s.clan_id == us_id}
    theirs = {s.task_id for s in solves if s.clan_id == them_id}

    now = datetime.now(UTC)
    active = war.state is WarState.ACTIVE
    left = (
        max(0, round((war.ends_at.replace(tzinfo=UTC) - now).total_seconds()))
        if active and war.ends_at
        else None
    )

    tasks: list[WarTask] = []
    if war.state in (WarState.ACTIVE, WarState.FINISHED):
        for task_id in war.task_ids:
            task = await session.get(Task, task_id)
            if task is None:
                continue
            await session.refresh(task, ["task_type"])
            solve = ours.get(task_id)
            solver = None
            if solve is not None:
                author = await session.get(User, solve.user_id)
                solver = author.display_name if author else None

            tasks.append(
                WarTask(
                    task_id=task.id,
                    number=task.task_type.number,
                    title=task.task_type.title,
                    statement=task.statement,
                    solved_by_us=solve is not None,
                    solved_by_them=task_id in theirs,
                    solver=solver,
                )
            )

    winner = None
    if war.state is WarState.FINISHED:
        if war.winner_id is None:
            winner = "ничья"
        else:
            winner = "мы" if war.winner_id == us_id else "они"

    return WarOut(
        id=war.id,
        state=war.state.value,
        stake=war.stake,
        us=WarSide(
            clan_id=clan.id,
            name=clan.name,
            tag=clan.tag,
            color=clan.color,
            score=scores.get(us_id, 0),
        ),
        them=WarSide(
            clan_id=them_id,
            name=them.name if them else "клан",
            tag=them.tag if them else "?",
            color=them.color if them else "#7d7979",
            score=scores.get(them_id, 0),
        ),
        you_challenged=war.challenger_id == us_id,
        seconds_left=left,
        tasks=tasks,
        can_answer=active,
        winner=winner,
        prize=war.stake * 2,
    )


async def _active_war(session: DbSession, clan_id: int) -> ClanWar | None:
    return await session.scalar(
        select(ClanWar)
        .where(
            or_(ClanWar.challenger_id == clan_id, ClanWar.opponent_id == clan_id),
            ClanWar.state.in_([WarState.PENDING, WarState.ACTIVE]),
        )
        .order_by(ClanWar.id.desc())
    )


@router.get("", response_model=list[WarOut])
async def my_wars(session: DbSession, user: PlayerUser) -> list[WarOut]:
    """Активная война и вызовы, плюс последние завершённые."""
    clan = await _clan_of(session, user)
    wars = list(
        await session.scalars(
            select(ClanWar)
            .where(or_(ClanWar.challenger_id == clan.id, ClanWar.opponent_id == clan.id))
            .order_by(ClanWar.id.desc())
            .limit(10)
        )
    )
    return [await _out(session, war, user, clan) for war in wars]


class ChallengeIn(BaseModel):
    clan_id: int
    stake: int = Field(default=500, ge=MIN_STAKE, le=MAX_STAKE)


@router.post("", response_model=WarOut, status_code=status.HTTP_201_CREATED)
async def challenge(
    payload: ChallengeIn, session: DbSession, user: PlayerUser
) -> WarOut:
    clan = await _require_officer(session, user)

    if payload.clan_id == clan.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "сам с собой воевать нельзя")
    if clan.coins < payload.stake:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"в казне {clan.coins} — на ставку {payload.stake} не хватает",
        )
    if len(clan.members) < MIN_FOR_BOARD:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"нужно хотя бы {MIN_FOR_BOARD} человека в клане"
        )

    target = await session.scalar(
        select(Clan).where(Clan.id == payload.clan_id).options(selectinload(Clan.members))
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "клан не найден")
    if len(target.members) < MIN_FOR_BOARD:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "в том клане слишком мало людей для войны"
        )
    if target.coins < payload.stake:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "у соперника в казне нет такой суммы"
        )

    if await _active_war(session, clan.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "у вас уже есть война или вызов")
    if await _active_war(session, target.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "этот клан уже занят войной")

    # Ставку удерживаем сразу: иначе можно разослать вызовы на сумму, которой нет.
    clan.coins -= payload.stake
    war = ClanWar(challenger_id=clan.id, opponent_id=target.id, stake=payload.stake)
    session.add(war)
    await session.commit()
    await session.refresh(war)

    return await _out(session, war, user, clan)


async def _load_war(session: DbSession, war_id: int, clan: Clan) -> ClanWar:
    war = await session.get(ClanWar, war_id)
    if war is None or clan.id not in (war.challenger_id, war.opponent_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "война не найдена")
    return war


@router.post("/{war_id}/accept", response_model=WarOut)
async def accept(war_id: int, session: DbSession, user: PlayerUser) -> WarOut:
    clan = await _require_officer(session, user)
    war = await _load_war(session, war_id, clan)

    if war.state is not WarState.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "вызов уже разобран")
    if war.opponent_id != clan.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "это твой собственный вызов")
    if clan.coins < war.stake:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED, f"в казне нет {war.stake} монет"
        )

    if datetime.now(UTC) - war.created_at.replace(tzinfo=UTC) > ACCEPT_WINDOW:
        war.state = WarState.EXPIRED
        challenger = await session.get(Clan, war.challenger_id)
        if challenger is not None:
            challenger.coins += war.stake  # ставка вызвавшего возвращается
        await session.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "вызов просрочен")

    ids = list(
        await session.scalars(
            select(Task.id).where(Task.status == TaskStatus.LIVE).order_by(Task.id)
        )
    )
    if len(ids) < TASKS:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "в банке мало задач")

    clan.coins -= war.stake
    war.task_ids = random.sample(ids, TASKS)
    war.state = WarState.ACTIVE
    war.starts_at = datetime.now(UTC)
    war.ends_at = war.starts_at + DURATION
    await session.commit()

    return await _out(session, war, user, clan)


@router.post("/{war_id}/decline", response_model=WarOut)
async def decline(war_id: int, session: DbSession, user: PlayerUser) -> WarOut:
    """Отклонить вызов. Отменить свой — тоже сюда: ставка возвращается."""
    clan = await _require_officer(session, user)
    war = await _load_war(session, war_id, clan)

    if war.state is not WarState.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "вызов уже разобран")

    challenger = await session.get(Clan, war.challenger_id)
    if challenger is not None:
        challenger.coins += war.stake
    war.state = WarState.DECLINED
    await session.commit()

    return await _out(session, war, user, clan)


class AnswerIn(BaseModel):
    task_id: int
    answer: str = Field(max_length=512)


class AnswerOut(BaseModel):
    is_correct: bool
    already: bool  # задачу уже закрыл кто-то из своих
    correct_answer: str | None
    score: int


@router.post("/{war_id}/answer", response_model=AnswerOut)
async def answer(
    war_id: int, payload: AnswerIn, session: DbSession, user: PlayerUser
) -> AnswerOut:
    clan = await _clan_of(session, user)
    war = await _load_war(session, war_id, clan)
    await settle(session, war)

    if war.state is not WarState.ACTIVE:
        raise HTTPException(status.HTTP_409_CONFLICT, "война не идёт")
    if payload.task_id not in war.task_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не из этой войны")

    existing = await session.scalar(
        select(ClanWarSolve).where(
            ClanWarSolve.war_id == war.id,
            ClanWarSolve.clan_id == clan.id,
            ClanWarSolve.task_id == payload.task_id,
        )
    )
    scores = await _scores(session, war)
    if existing is not None:
        return AnswerOut(
            is_correct=True,
            already=True,
            correct_answer=None,
            score=scores.get(clan.id, 0),
        )

    task = await session.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не найдена")

    is_correct = check_answer(task.answer_type, task.answer_payload, payload.answer)
    if is_correct:
        session.add(
            ClanWarSolve(
                war_id=war.id, clan_id=clan.id, user_id=user.id, task_id=task.id
            )
        )
        # Монеты за войну идут в казну, а решившему — обычная награда за задачу,
        # чтобы участие в войне не было беднее домашнего квиза.
        await award(session, user, CoinReason.TASK_FIRST_SOLVE, note="война кланов")
        await session.commit()

    scores = await _scores(session, war)
    return AnswerOut(
        is_correct=is_correct,
        already=False,
        correct_answer=_correct_answer_text(task) if is_correct else None,
        score=scores.get(clan.id, 0),
    )


class DepositIn(BaseModel):
    amount: int = Field(ge=1, le=100000)


@router.post("/deposit")
async def deposit(payload: DepositIn, session: DbSession, user: PlayerUser) -> dict:
    """Скинуться в казну. Может любой участник — это и есть вклад в клан."""
    clan = await _clan_of(session, user)
    if user.coins < payload.amount:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "не хватает монет")

    await award(
        session, user, CoinReason.PURCHASE, amount=-payload.amount, note="казна клана"
    )
    clan.coins += payload.amount
    await session.commit()
    return {"ok": True, "clan_coins": clan.coins}
