"""Турниры: витрина для учеников и конструктор для админа.

Правила подсчёта живут в `app/core/tournaments.py`; здесь — только выдача
таблиц, настройка и подведение итогов.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, PlayerUser
from app.api.shop import cosmetics_of
from app.core.coins import award
from app.core.answers import check_answer
from app.core.tournaments import standings
from app.models import (
    CoinReason,
    ContestProblem,
    ContestSubmission,
    RuleEvent,
    ShopItem,
    Task,
    Tournament,
    TournamentFormat,
    TournamentPrize,
    TournamentResult,
    TournamentRule,
    TournamentStatus,
    User,
    UserItem,
)

router = APIRouter(prefix="/api/tournaments", tags=["tournaments"])

EVENT_TITLES = {
    RuleEvent.TASK_SOLVED: "за решённую задачу",
    RuleEvent.QUIZ_FINISHED: "за пройденный квиз",
    RuleEvent.QUIZ_PERFECT: "за квиз без ошибок",
    RuleEvent.DUEL_WIN: "за победу в онлайн-дуэли",
    RuleEvent.DUEL_PLAYED: "за сыгранный онлайн-матч",
    RuleEvent.MOCK_FINISHED: "за сданный пробник",
    RuleEvent.DAILY_SOLVED: "за задачу дня",
}


class RuleOut(BaseModel):
    event: str
    title: str
    points: int
    daily_cap: int | None
    task_numbers: list[int]
    exclude_hints: bool


class PrizeOut(BaseModel):
    place_from: int
    place_to: int
    coins: int
    item_code: str | None
    item_title: str | None


class RowOut(BaseModel):
    place: int
    user_id: int
    display_name: str
    nick_color: str | None
    prefix: str | None
    avatar: str | None
    frame: str | None
    points: int
    penalty: int
    solved: int
    cells: dict[str, str]  # буква задачи → «+», «+3», «−2», ""
    is_you: bool
    prize_coins: int
    prize_item: str | None


class ProblemOut(BaseModel):
    letter: str
    task_id: int
    points: int
    task_type_number: int
    task_type_title: str
    statement: str      # пусто, пока контест не начался
    image_url: str | None
    answer_type: str

    solved: bool
    wrong: int
    minute: int | None
    solved_count: int   # сколько человек решило — как на Codeforces


class TournamentOut(BaseModel):
    id: int
    title: str
    description: str | None
    color: str
    status: str
    starts_at: datetime
    ends_at: datetime
    min_rating: int | None

    state: str  # ждёт | идёт | завершён
    seconds_left: int | None
    eligible: bool
    ineligible_reason: str | None

    format: str
    penalty_minutes: int
    started: bool          # контест уже начался
    over: bool             # время вышло
    seconds_to_start: int | None

    rules: list[RuleOut]
    prizes: list[PrizeOut]
    problems: list[ProblemOut]
    rows: list[RowOut]
    your_place: int | None
    your_points: int
    your_penalty: int


def letter_of(position: int) -> str:
    """A, B, C… — привычная нумерация задач контеста."""
    return chr(ord("A") + position) if position < 26 else f"#{position + 1}"


async def _load(session: DbSession, tournament_id: int) -> Tournament:
    tournament = await session.scalar(
        select(Tournament)
        .where(Tournament.id == tournament_id)
        .options(
            selectinload(Tournament.rules),
            selectinload(Tournament.prizes),
            selectinload(Tournament.problems),
        )
    )
    if tournament is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "турнир не найден")
    return tournament


def _state(tournament: Tournament) -> str:
    now = datetime.now(UTC)
    if tournament.status is TournamentStatus.FINISHED:
        return "завершён"
    if tournament.starts_at > now:
        return "ждёт старта"
    if tournament.ends_at < now:
        return "подводим итоги"
    return "идёт"


def _prize_for(tournament: Tournament, place: int) -> TournamentPrize | None:
    for prize in tournament.prizes:
        if prize.place_from <= place <= prize.place_to:
            return prize
    return None


def _cells(tournament: Tournament, row) -> dict[str, str]:
    """Клетка задачи в таблице: «+» решено с первой, «+2» со второй попытки,
    «−3» три неверных и не решено."""
    out: dict[str, str] = {}
    for problem in tournament.problems:
        result = row.problems.get(problem.task_id)
        letter = letter_of(problem.position)
        if result is None:
            out[letter] = ""
        elif result.solved:
            out[letter] = "+" if result.wrong == 0 else f"+{result.wrong + 1}"
        else:
            out[letter] = f"−{result.wrong}" if result.wrong else ""
    return out


async def _problems_out(
    session: DbSession, tournament: Tournament, user: User, started: bool
) -> list[ProblemOut]:
    """Условия отдаём только после старта — иначе набор можно прочитать заранее
    прямо из ответа API."""
    table = await standings(session, tournament)
    mine = next((row for row in table if row.user_id == user.id), None)

    solved_by: dict[int, int] = {}
    for row in table:
        for task_id, result in row.problems.items():
            if result.solved:
                solved_by[task_id] = solved_by.get(task_id, 0) + 1

    out: list[ProblemOut] = []
    for problem in tournament.problems:
        task = await session.get(Task, problem.task_id)
        if task is None:
            continue
        await session.refresh(task, ["task_type"])
        result = mine.problems.get(problem.task_id) if mine else None

        out.append(
            ProblemOut(
                letter=letter_of(problem.position),
                task_id=task.id,
                points=problem.points,
                task_type_number=task.task_type.number,
                task_type_title=task.task_type.title,
                statement=task.statement if started else "",
                image_url=task.image_url if started else None,
                answer_type=task.answer_type.value,
                solved=bool(result and result.solved),
                wrong=result.wrong if result else 0,
                minute=result.minute if result else None,
                solved_count=solved_by.get(task.id, 0),
            )
        )
    return out


async def _out(
    session: DbSession, tournament: Tournament, user: User, limit: int = 50
) -> TournamentOut:
    """Собирает витрину турнира: правила, награды и текущую таблицу."""
    rows: list[RowOut] = []
    your_place: int | None = None
    your_points = 0
    your_penalty = 0

    # У завершённого берём снимок: правила могли поправить, а призёры
    # должны остаться те же, что были в момент подведения итогов.
    if tournament.status is TournamentStatus.FINISHED:
        saved = list(
            await session.scalars(
                select(TournamentResult)
                .where(TournamentResult.tournament_id == tournament.id)
                .order_by(TournamentResult.place)
                .limit(limit)
            )
        )
        for row in saved:
            author = await session.get(User, row.user_id) if row.user_id else None
            if author is None:
                continue
            cos = await cosmetics_of(session, author.id)
            mine = author.id == user.id
            if mine:
                your_place, your_points = row.place, row.points
            rows.append(
                RowOut(
                    place=row.place,
                    user_id=author.id,
                    display_name=author.display_name,
                    nick_color=cos.nick_color,
                    prefix=cos.prefix,
                    avatar=cos.avatar,
                    frame=cos.frame,
                    points=row.points,
                    penalty=0,
                    solved=0,
                    cells={},
                    is_you=mine,
                    prize_coins=row.coins_awarded,
                    prize_item=row.item_awarded,
                )
            )
    else:
        table = await standings(session, tournament)
        for place, row in enumerate(table[:limit], 1):
            author = await session.get(User, row.user_id)
            if author is None:
                continue
            cos = await cosmetics_of(session, author.id)
            prize = _prize_for(tournament, place)
            mine = author.id == user.id
            if mine:
                your_place, your_points, your_penalty = place, row.points, row.penalty
            rows.append(
                RowOut(
                    place=place,
                    user_id=author.id,
                    display_name=author.display_name,
                    nick_color=cos.nick_color,
                    prefix=cos.prefix,
                    avatar=cos.avatar,
                    frame=cos.frame,
                    points=row.points,
                    penalty=row.penalty,
                    solved=row.solved,
                    cells=_cells(tournament, row),
                    is_you=mine,
                    prize_coins=prize.coins if prize else 0,
                    prize_item=prize.item_code if prize else None,
                )
            )
        if your_place is None:
            mine = next((r for r in table if r.user_id == user.id), None)
            if mine is not None:
                your_points = mine.points
                your_place = table.index(mine) + 1

    prizes: list[PrizeOut] = []
    for prize in sorted(tournament.prizes, key=lambda p: p.place_from):
        item = (
            await session.scalar(select(ShopItem).where(ShopItem.code == prize.item_code))
            if prize.item_code
            else None
        )
        prizes.append(
            PrizeOut(
                place_from=prize.place_from,
                place_to=prize.place_to,
                coins=prize.coins,
                item_code=prize.item_code,
                item_title=item.title if item else None,
            )
        )

    eligible = True
    reason = None
    if tournament.min_rating is not None and user.rating < tournament.min_rating:
        eligible = False
        reason = f"нужен рейтинг от {tournament.min_rating}, у тебя {user.rating}"

    now = datetime.now(UTC)
    left = None
    if tournament.status is not TournamentStatus.FINISHED and tournament.ends_at > now:
        left = round((tournament.ends_at - now).total_seconds())

    now2 = datetime.now(UTC)
    started = tournament.starts_at <= now2
    over = tournament.ends_at < now2

    return TournamentOut(
        id=tournament.id,
        title=tournament.title,
        description=tournament.description,
        color=tournament.color,
        status=tournament.status.value,
        starts_at=tournament.starts_at,
        ends_at=tournament.ends_at,
        min_rating=tournament.min_rating,
        state=_state(tournament),
        seconds_left=left,
        eligible=eligible,
        ineligible_reason=reason,
        format=tournament.format.value,
        penalty_minutes=tournament.penalty_minutes,
        started=started,
        over=over,
        seconds_to_start=(
            round((tournament.starts_at - now2).total_seconds()) if not started else None
        ),
        problems=(
            await _problems_out(session, tournament, user, started)
            if tournament.format is TournamentFormat.CONTEST
            else []
        ),
        rules=[
            RuleOut(
                event=rule.event.value,
                title=EVENT_TITLES.get(rule.event, rule.event.value),
                points=rule.points,
                daily_cap=rule.daily_cap,
                task_numbers=rule.task_numbers or [],
                exclude_hints=rule.exclude_hints,
            )
            for rule in tournament.rules
        ],
        prizes=prizes,
        rows=rows,
        your_place=your_place,
        your_points=your_points,
        your_penalty=your_penalty,
    )


@router.get("", response_model=list[TournamentOut])
async def list_tournaments(session: DbSession, user: PlayerUser) -> list[TournamentOut]:
    """Опубликованные турниры: сначала идущие, потом будущие, потом завершённые."""
    rows = list(
        await session.scalars(
            select(Tournament)
            .where(Tournament.status != TournamentStatus.DRAFT)
            .options(
                selectinload(Tournament.rules),
                selectinload(Tournament.prizes),
                selectinload(Tournament.problems),
            )
            .order_by(Tournament.ends_at.desc())
            .limit(20)
        )
    )
    order = {"идёт": 0, "ждёт старта": 1, "подводим итоги": 2, "завершён": 3}
    rows.sort(key=lambda t: (order[_state(t)], t.ends_at))
    # Таблицу в списке показываем короткую: считать полную для каждого турнира дорого.
    return [await _out(session, t, user, limit=3) for t in rows]


@router.get("/{tournament_id}", response_model=TournamentOut)
async def tournament(tournament_id: int, session: DbSession, user: PlayerUser) -> TournamentOut:
    found = await _load(session, tournament_id)
    if found.status is TournamentStatus.DRAFT and not user.is_admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "турнир не найден")
    return await _out(session, found, user)


class SubmitIn(BaseModel):
    task_id: int
    answer: str = Field(max_length=512)


class SubmitOut(BaseModel):
    is_correct: bool
    upsolve: bool
    wrong: int
    minute: int | None
    message: str


@router.post("/{tournament_id}/submit", response_model=SubmitOut)
async def submit(
    tournament_id: int, payload: SubmitIn, session: DbSession, user: PlayerUser
) -> SubmitOut:
    """Сдать задачу контеста.

    Верный ответ закрывает задачу; неверные до него дают штраф. После конца
    контеста сдавать можно, но такие попытки помечаются дорешиванием и в
    таблицу не идут — иначе места менялись бы неделями после финиша.
    """
    tournament = await _load(session, tournament_id)
    if tournament.format is not TournamentFormat.CONTEST:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "это не контест")
    if tournament.status is TournamentStatus.DRAFT:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "турнир не найден")

    problem = next((p for p in tournament.problems if p.task_id == payload.task_id), None)
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не из этого контеста")

    now = datetime.now(UTC)
    if now < tournament.starts_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "контест ещё не начался")

    upsolve = now > tournament.ends_at
    if not upsolve and tournament.min_rating is not None and user.rating < tournament.min_rating:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "не проходишь по рейтингу")

    mine = list(
        await session.scalars(
            select(ContestSubmission)
            .where(
                ContestSubmission.tournament_id == tournament.id,
                ContestSubmission.user_id == user.id,
                ContestSubmission.task_id == payload.task_id,
            )
            .order_by(ContestSubmission.id)
        )
    )
    if any(sub.is_correct for sub in mine):
        raise HTTPException(status.HTTP_409_CONFLICT, "задача уже решена")

    task = await session.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не найдена")

    is_correct = check_answer(task.answer_type, task.answer_payload, payload.answer)
    session.add(
        ContestSubmission(
            tournament_id=tournament.id,
            user_id=user.id,
            task_id=task.id,
            answer_raw=payload.answer[:512],
            is_correct=is_correct,
            upsolve=upsolve,
        )
    )
    await session.commit()

    wrong = sum(1 for sub in mine if not sub.is_correct) + (0 if is_correct else 1)
    minute = (
        max(0, int((now - tournament.starts_at).total_seconds() // 60)) if is_correct else None
    )

    if upsolve:
        message = "Верно — но это дорешивание, в таблицу не идёт" if is_correct else "Неверно"
    elif is_correct:
        penalty = wrong * tournament.penalty_minutes
        message = (
            f"Принято на {minute}-й минуте"
            + (f", штраф {penalty} мин за {wrong} неверных" if penalty else "")
        )
    else:
        message = f"Неверно. Попыток: {wrong}"

    return SubmitOut(
        is_correct=is_correct, upsolve=upsolve, wrong=wrong, minute=minute, message=message
    )


# --------------------------------------------------------------- подведение итогов


class AwardOut(BaseModel):
    winners: int
    coins_total: int
    items_total: int


async def finish_and_award(session: DbSession, tournament: Tournament) -> AwardOut:
    """Фиксирует итоги и выдаёт награды. Повторный вызов не удваивает призы:
    защита стоит на `awarded_at`, а не на статусе — статус можно вернуть руками."""
    if tournament.awarded_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "награды уже выданы")

    table = await standings(session, tournament)
    coins_total = items_total = 0

    for place, row in enumerate(table, 1):
        prize = _prize_for(tournament, place)
        author = await session.get(User, row.user_id)
        coins = 0
        item_code = None

        if prize is not None and author is not None:
            if prize.coins:
                coins = await award(
                    session,
                    author,
                    CoinReason.TOURNAMENT_PRIZE,
                    amount=prize.coins,
                    note=f"{tournament.title}: {place} место",
                )
                coins_total += coins

            if prize.item_code:
                item = await session.scalar(
                    select(ShopItem).where(ShopItem.code == prize.item_code)
                )
                if item is not None:
                    owned = await session.scalar(
                        select(UserItem).where(
                            UserItem.user_id == author.id, UserItem.item_id == item.id
                        )
                    )
                    if owned is None:
                        session.add(UserItem(user_id=author.id, item_id=item.id))
                        items_total += 1
                    item_code = item.code

        session.add(
            TournamentResult(
                tournament_id=tournament.id,
                user_id=row.user_id,
                place=place,
                points=row.points,
                coins_awarded=coins,
                item_awarded=item_code,
            )
        )

    tournament.status = TournamentStatus.FINISHED
    tournament.awarded_at = datetime.now(UTC)
    await session.commit()

    return AwardOut(winners=len(table), coins_total=coins_total, items_total=items_total)


# ------------------------------------------------------------------- настройка


class RuleIn(BaseModel):
    event: RuleEvent
    points: int = Field(default=1, ge=0, le=1000)
    daily_cap: int | None = Field(default=None, ge=1, le=1000)
    task_numbers: list[int] = Field(default_factory=list)
    min_difficulty: int | None = Field(default=None, ge=1, le=5)
    max_difficulty: int | None = Field(default=None, ge=1, le=5)
    exclude_hints: bool = False


class PrizeIn(BaseModel):
    place_from: int = Field(ge=1)
    place_to: int = Field(ge=1)
    coins: int = Field(default=0, ge=0, le=100000)
    item_code: str | None = None


class ProblemIn(BaseModel):
    task_id: int
    points: int = Field(default=100, ge=1, le=10000)


class TournamentIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    format: TournamentFormat = TournamentFormat.CONTEST
    penalty_minutes: int = Field(default=10, ge=0, le=120)
    problems: list[ProblemIn] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=2000)
    color: str = "#0088b0"
    starts_at: datetime
    ends_at: datetime
    min_rating: int | None = None
    rules: list[RuleIn] = Field(default_factory=list)
    prizes: list[PrizeIn] = Field(default_factory=list)


async def apply_config(
    session: DbSession, tournament: Tournament, payload: TournamentIn
) -> Tournament:
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "конец раньше начала")

    tournament.title = payload.title
    tournament.description = payload.description
    tournament.color = payload.color
    tournament.starts_at = payload.starts_at
    tournament.ends_at = payload.ends_at
    tournament.min_rating = payload.min_rating
    tournament.format = payload.format
    tournament.penalty_minutes = payload.penalty_minutes

    # Правила и награды заменяем целиком: редактировать по одной строке незачем,
    # а частичное обновление легко рассинхронизировать с формой.
    #
    # Удаляем запросом, а не через коллекцию: обращение к `tournament.rules` у
    # только что созданного объекта тянет ленивую загрузку, а она в асинхронной
    # сессии падает (MissingGreenlet).
    await session.execute(
        delete(TournamentRule).where(TournamentRule.tournament_id == tournament.id)
    )
    await session.execute(
        delete(TournamentPrize).where(TournamentPrize.tournament_id == tournament.id)
    )

    for rule in payload.rules:
        session.add(TournamentRule(tournament_id=tournament.id, **rule.model_dump()))

    for prize in payload.prizes:
        if prize.place_to < prize.place_from:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "диапазон мест наоборот")
        session.add(TournamentPrize(tournament_id=tournament.id, **prize.model_dump()))

    # Задачи контеста. Сданные ответы не трогаем: если задачу убрали из набора,
    # её попытки просто перестают учитываться, а вернут — снова учтутся.
    await session.execute(
        delete(ContestProblem).where(ContestProblem.tournament_id == tournament.id)
    )
    for position, problem in enumerate(payload.problems):
        session.add(
            ContestProblem(
                tournament_id=tournament.id,
                task_id=problem.task_id,
                points=problem.points,
                position=position,
            )
        )

    await session.commit()
    return await _load(session, tournament.id)
