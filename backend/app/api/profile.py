"""Профиль: статистика, активность по дням и достижения.

Достижения считаются из попыток на лету, а не хранятся отдельной таблицей.
Пока их немного, это проще и не рассинхронизируется с данными; когда появится
всплывающее уведомление «получено», понадобится хранить факт и дату выдачи.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DbSession, PlayerUser
from app.api.shop import cosmetics_of
from app.models import (
    AchievementUnlock,
    Attempt,
    CoinTransaction,
    Duel,
    DuelKind,
    DuelState,
    Quiz,
    Task,
    TaskStatus,
    TaskType,
    User,
)

WEAK_BELOW = 0.7  # ниже этой доли верных тема считается проседающей

# Ранги по рейтингу — чтобы число само по себе что-то значило
RANKS = [
    (1800, "Гуру задач", "#7c3aed"),
    (1600, "Гранд-мастер", "#d6006c"),
    (1450, "Мастер", "#e0a800"),
    (1300, "Пахарь", "#1f9d55"),
    (1150, "Любитель задачек", "#0088b0"),
    (1000, "Ученик", "#5b6570"),
    (0, "Новичок", "#8a5a2b"),
]


def rank_for(rating: int) -> str:
    for threshold, name, _ in RANKS:
        if rating >= threshold:
            return name
    return "Новичок"


def rank_color(rating: int) -> str:
    for threshold, _, color in RANKS:
        if rating >= threshold:
            return color
    return "#8a5a2b"

router = APIRouter(prefix="/api", tags=["profile"])

TZ = ZoneInfo("Europe/Moscow")
ACTIVITY_DAYS = 30


class Achievement(BaseModel):
    code: str
    title: str
    description: str
    rarity: str  # bronze | silver | gold
    progress: int
    target: int
    unlocked: bool


class ActivityDay(BaseModel):
    day: date
    solved: int


class DayTypeRow(BaseModel):
    number: int
    title: str
    total: int
    correct: int


class DayStatsOut(BaseModel):
    day: date
    total: int
    correct: int
    wrong: int
    with_hint: int
    minutes: int
    quizzes: int
    by_type: list[DayTypeRow]


class WeakTopic(BaseModel):
    """Самое проседающее — то, с чего стоит начать занятие."""

    number: int
    title: str
    accuracy: int


class ProfileOut(BaseModel):
    display_name: str
    is_guest: bool
    avatar_url: str | None
    rating: int
    rank: str
    rank_color: str
    coins: int
    coins_week: int
    cosmetics: dict
    incoming_duels: list[dict]
    duels_played: int
    duels_won: int
    duel_win_streak: int

    solved_total: int
    correct_total: int
    accuracy: int
    streak_days: int
    streak_record: int
    best_correct_run: int
    perfect_quizzes: int
    numbers_covered: int

    # попытки: сколько раз ответил верно и сколько ошибся
    attempts_total: int
    attempts_correct: int
    attempts_wrong: int

    # работа над ошибками: задачи, где ошибался, и сколько из них уже закрыто
    mistakes_total: int
    mistakes_fixed: int
    mistakes_open: int
    weak_topics: list[WeakTopic]
    rating_history: list[int]

    tasks_total: int

    activity: list[ActivityDay]
    achievements: list[Achievement]


def _longest_daily_run(days: list[date]) -> int:
    """Самая длинная серия подряд идущих дней с занятиями."""
    if not days:
        return 0
    unique = sorted(set(days))
    best = run = 1
    for prev, cur in zip(unique, unique[1:]):
        run = run + 1 if cur - prev == timedelta(days=1) else 1
        best = max(best, run)
    return best


def _build_achievements(**m) -> list[Achievement]:
    """Три группы: объём, результат и «прикольные» — за характер занятий."""
    cap = lambda value, target: min(value, target)  # noqa: E731
    raw = [
        # — объём
        ("first_blood", "Первая задача", "Решить одну задачу", "bronze",
         cap(m["solved"], 1), 1),
        ("solved_50", "Полсотни", "Решить 50 задач", "bronze", cap(m["solved"], 50), 50),
        ("solved_100", "Сотня", "Решить 100 задач", "silver", cap(m["solved"], 100), 100),
        ("solved_500", "Пятьсот", "Решить 500 задач", "gold", cap(m["solved"], 500), 500),
        ("all_numbers", "Полный охват", "Решить хотя бы по одной задаче каждого номера",
         "gold", m["numbers"], 12),

        # — результат
        ("run_10", "Десять подряд", "10 верных ответов подряд", "silver",
         cap(m["best_run"], 10), 10),
        ("run_25", "Снайпер", "25 верных ответов подряд", "gold", cap(m["best_run"], 25), 25),
        ("perfect_quiz", "Без единой ошибки", "Пройти квиз целиком без ошибок", "silver",
         cap(m["perfect"], 1), 1),
        ("accuracy_80", "Точность", "80% верных при 100 решённых задачах", "gold",
         m["accuracy"] if m["attempts"] >= 100 else 0, 80),
        ("fix_10", "Работа над ошибками", "Исправить 10 задач, где ошибался", "silver",
         cap(m["fixed"], 10), 10),
        ("fix_50", "Феникс", "Исправить 50 задач, где ошибался", "gold", cap(m["fixed"], 50), 50),
        ("week_streak", "Неделя без пропусков", "7 дней подряд", "silver",
         cap(m["streak_record"], 7), 7),
        ("two_weeks", "Две недели без пропусков", "14 дней подряд", "gold",
         cap(m["streak_record"], 14), 14),

        # — дуэли
        ("duelist", "Дуэлянт", "Сыграть 10 онлайн-матчей", "silver",
         cap(m["duels_played"], 10), 10),
        ("win_streak_3", "На кураже", "Три победы подряд в онлайне", "silver",
         cap(m["duel_win_streak"], 3), 3),
        ("rating_1200", "Заслуженный", "Поднять рейтинг до 1200", "gold",
         cap(m["rating"], 1200), 1200),

        # — прикольные
        ("lightning", "Молния", "10 верных ответов быстрее 15 секунд", "silver",
         cap(m["fast_correct"], 10), 10),
        ("night_owl", "Ночной ботаник", "Решать задачи между полуночью и пятью утра",
         "bronze", cap(m["night_attempts"], 5), 5),
        ("marathon", "Стахановец", "50 задач за один день", "gold",
         cap(m["best_day"], 50), 50),
        ("comeback", "Возвращение", "Вернуться после недельного перерыва", "bronze",
         1 if m["came_back"] else 0, 1),
    ]
    return [
        Achievement(
            code=code,
            title=title,
            description=desc,
            rarity=rarity,
            progress=progress,
            target=target,
            unlocked=progress >= target,
        )
        for code, title, desc, rarity, progress, target in raw
    ]


async def sync_unlocks(
    session: DbSession, user_id: int, achievements: list[Achievement]
) -> list[Achievement]:
    """Записывает новые достижения и возвращает те, что получены прямо сейчас.

    У аккаунта, который завёлся до появления таблицы, всё уже давно заслужено —
    показывать пачку всплывашек задним числом незачем. Поэтому первый прогон
    записывает молча.
    """
    known = set(
        await session.scalars(
            select(AchievementUnlock.code).where(AchievementUnlock.user_id == user_id)
        )
    )
    unlocked = [a for a in achievements if a.unlocked]
    fresh = [a for a in unlocked if a.code not in known]
    if not fresh:
        return []

    for a in fresh:
        session.add(AchievementUnlock(user_id=user_id, code=a.code))
    await session.commit()

    first_run = not known
    return [] if first_run else fresh


@router.post("/achievements/check", response_model=list[Achievement])
async def check_achievements(session: DbSession, user: PlayerUser) -> list[Achievement]:
    """Что человек получил с прошлой проверки. Дёргается после квиза и дуэли —
    чтобы всплывашка появилась в момент события, а не когда откроют профиль."""
    data = await profile(session, user)
    return await sync_unlocks(session, user.id, data.achievements)


@router.get("/profile", response_model=ProfileOut)
async def profile(session: DbSession, user: PlayerUser) -> ProfileOut:
    attempts = list(
        await session.scalars(
            select(Attempt).where(Attempt.user_id == user.id).order_by(Attempt.id)
        )
    )

    solved_total = len({a.task_id for a in attempts})
    correct_total = len({a.task_id for a in attempts if a.is_correct})
    accuracy = round(100 * sum(a.is_correct for a in attempts) / len(attempts)) if attempts else 0

    days = [a.created_at.astimezone(TZ).date() for a in attempts]
    streak_record = max(_longest_daily_run(days), user.streak_days)

    best_run = run = 0
    for a in attempts:
        run = run + 1 if a.is_correct else 0
        best_run = max(best_run, run)

    perfect = (
        await session.scalar(
            select(func.count(Quiz.id)).where(
                Quiz.user_id == user.id,
                Quiz.finished_at.is_not(None),
                Quiz.score == func.cardinality(Quiz.task_ids),
            )
        )
    ) or 0

    numbers_covered = (
        await session.scalar(
            select(func.count(func.distinct(TaskType.number)))
            .join(Task, Task.task_type_id == TaskType.id)
            .join(Attempt, Attempt.task_id == Task.id)
            .where(Attempt.user_id == user.id, Attempt.is_correct.is_(True))
        )
    ) or 0

    # Работа над ошибками. Ошибочной считается задача, где хоть раз ответили неверно;
    # закрытой — если потом на ней же ответили верно.
    wrong_tasks = {a.task_id for a in attempts if not a.is_correct}
    correct_tasks = {a.task_id for a in attempts if a.is_correct}
    fixed = len(wrong_tasks & correct_tasks)
    mistakes_open = len(wrong_tasks - correct_tasks)

    # Слабые темы: где процент верных ниже всего. Меньше трёх попыток не считаем —
    # одна случайная ошибка не делает тему слабой, а выше порога это уже не слабое
    # место, и показывать его под таким заголовком было бы враньём.
    per_type = (
        await session.execute(
            select(
                TaskType.number,
                TaskType.title,
                func.count(Attempt.id),
                func.count(Attempt.id).filter(Attempt.is_correct.is_(True)),
            )
            .join(Task, Task.task_type_id == TaskType.id)
            .join(Attempt, Attempt.task_id == Task.id)
            .where(Attempt.user_id == user.id)
            .group_by(TaskType.number, TaskType.title)
        )
    ).all()

    weak = sorted(
        (
            WeakTopic(number=number, title=title, accuracy=round(100 * correct / total))
            for number, title, total, correct in per_type
            if total >= 3 and correct / total < WEAK_BELOW
        ),
        key=lambda topic: topic.accuracy,
    )[:3]

    today = max(days) if days else date.today()
    counts: dict[date, int] = {}
    for day in days:
        counts[day] = counts.get(day, 0) + 1
    activity = [
        ActivityDay(day=today - timedelta(days=offset), solved=counts.get(today - timedelta(days=offset), 0))
        for offset in reversed(range(ACTIVITY_DAYS))
    ]

    tasks_total = (
        await session.scalar(
            select(func.count(Task.id)).where(Task.status == TaskStatus.LIVE)
        )
    ) or 0

    # дуэли считаются только онлайновые: рейтинг меняют только они
    online = list(
        await session.scalars(
            select(Duel)
            .where(
                Duel.kind == DuelKind.ONLINE,
                Duel.state == DuelState.FINISHED,
                (Duel.challenger_id == user.id) | (Duel.opponent_id == user.id),
            )
            .order_by(Duel.id.desc())
        )
    )

    # История рейтинга. Отдельной таблицы нет и заводить её ради спарклайна
    # незачем: в дуэлях сохранены дельты, поэтому идём от текущего рейтинга
    # назад и в конце разворачиваем.
    rating_history = [user.rating]
    for duel in online:  # уже от свежих к старым
        delta = (
            duel.challenger_rating_delta
            if duel.challenger_id == user.id
            else duel.opponent_rating_delta
        )
        rating_history.append(rating_history[-1] - (delta or 0))
    rating_history.reverse()

    duels_won = sum(1 for d in online if d.winner_id == user.id)
    win_streak = 0
    for duel in online:  # от свежих к старым
        if duel.winner_id == user.id:
            win_streak += 1
        else:
            break

    coins_week = (
        await session.scalar(
            select(func.coalesce(func.sum(CoinTransaction.amount), 0)).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.amount > 0,
                CoinTransaction.created_at >= datetime.now(TZ) - timedelta(days=7),
            )
        )
    ) or 0

    # входящие вызовы: тебя позвали, ты ещё не играл
    incoming = []
    for duel in await session.scalars(
        select(Duel)
        .where(
            Duel.kind == DuelKind.LINK,
            Duel.state == DuelState.WAITING,
            Duel.opponent_id == user.id,
            Duel.opponent_quiz_id.is_(None),
        )
        .order_by(Duel.id.desc())
        .limit(5)
    ):
        challenger = await session.get(User, duel.challenger_id)
        incoming.append(
            {
                "code": duel.code,
                "from": challenger.display_name if challenger else "—",
                "rounds": len(duel.task_ids),
            }
        )

    fast_correct = sum(1 for a in attempts if a.is_correct and 0 < a.time_spent_ms < 15_000)
    night_attempts = sum(1 for a in attempts if a.created_at.astimezone(TZ).hour < 5)
    best_day = max(counts.values()) if counts else 0

    # «вернулся»: между двумя днями занятий разрыв больше недели
    unique_days = sorted(set(days))
    came_back = any(
        (later - earlier).days >= 7 for earlier, later in zip(unique_days, unique_days[1:])
    )

    return ProfileOut(
        display_name=user.display_name,
        is_guest=user.is_guest,
        avatar_url=user.avatar_url,
        rating=user.rating,
        rank=rank_for(user.rating),
        rank_color=rank_color(user.rating),
        coins=user.coins,
        coins_week=coins_week,
        cosmetics=(await cosmetics_of(session, user.id)).model_dump(),
        incoming_duels=incoming,
        duels_played=len(online),
        duels_won=duels_won,
        duel_win_streak=win_streak,
        solved_total=solved_total,
        correct_total=correct_total,
        accuracy=accuracy,
        streak_days=user.streak_days,
        streak_record=streak_record,
        best_correct_run=best_run,
        perfect_quizzes=perfect,
        weak_topics=weak,
        rating_history=rating_history,
        numbers_covered=numbers_covered,
        attempts_total=len(attempts),
        attempts_correct=sum(a.is_correct for a in attempts),
        attempts_wrong=sum(not a.is_correct for a in attempts),
        mistakes_total=len(wrong_tasks),
        mistakes_fixed=fixed,
        mistakes_open=mistakes_open,
        tasks_total=tasks_total,
        activity=activity,
        achievements=_build_achievements(
            solved=solved_total,
            streak_record=streak_record,
            best_run=best_run,
            perfect=perfect,
            numbers=numbers_covered,
            fixed=fixed,
            accuracy=accuracy,
            attempts=len(attempts),
            duels_played=len(online),
            duel_win_streak=win_streak,
            rating=user.rating,
            fast_correct=fast_correct,
            night_attempts=night_attempts,
            best_day=best_day,
            came_back=came_back,
        ),
    )


@router.get("/profile/day", response_model=DayStatsOut)
async def day_stats(day: date, session: DbSession, user: PlayerUser) -> DayStatsOut:
    """Подробности одного дня — открывается кликом по квадратику активности."""
    attempts = list(
        await session.scalars(
            select(Attempt).where(Attempt.user_id == user.id).order_by(Attempt.id)
        )
    )
    todays = [a for a in attempts if a.created_at.astimezone(TZ).date() == day]

    by_type: dict[int, DayTypeRow] = {}
    for attempt in todays:
        row = (
            await session.execute(
                select(TaskType.number, TaskType.title)
                .join(Task, Task.task_type_id == TaskType.id)
                .where(Task.id == attempt.task_id)
            )
        ).first()
        if row is None:
            continue
        number, title = row
        entry = by_type.setdefault(
            number, DayTypeRow(number=number, title=title, total=0, correct=0)
        )
        entry.total += 1
        entry.correct += int(attempt.is_correct)

    return DayStatsOut(
        day=day,
        total=len(todays),
        correct=sum(a.is_correct for a in todays),
        wrong=sum(not a.is_correct for a in todays),
        with_hint=sum(a.used_hint for a in todays),
        minutes=round(sum(a.time_spent_ms for a in todays) / 60000),
        quizzes=len({a.quiz_id for a in todays if a.quiz_id}),
        by_type=sorted(by_type.values(), key=lambda r: r.number),
    )


# ------------------------------------------------------------------ лидерборд

class LeaderRow(BaseModel):
    place: int
    user_id: int
    display_name: str
    rating: int
    rank: str
    rank_color: str
    nick_color: str | None
    prefix: str | None
    avatar: str | None
    frame: str | None
    duels: int
    wins: int
    solved_week: int
    is_you: bool


class LeaderboardOut(BaseModel):
    board: str
    rows: list[LeaderRow]
    your_place: int | None


@router.get("/leaderboard", response_model=LeaderboardOut)
async def leaderboard(
    session: DbSession, user: PlayerUser, board: str = "rating", limit: int = 30
) -> LeaderboardOut:
    """Две таблицы: по рейтингу (только те, кто играл онлайн) и по активности за неделю.

    Гостей в рейтинговой таблице нет: рейтинг привязан к куке, и её можно очистить,
    чтобы обнулить неудачную серию.
    """
    week_ago = datetime.now(TZ) - timedelta(days=7)

    solved_week = {
        row.user_id: row.count
        for row in (
            await session.execute(
                select(
                    Attempt.user_id.label("user_id"),
                    func.count(func.distinct(Attempt.task_id)).label("count"),
                )
                .where(Attempt.is_correct.is_(True), Attempt.created_at >= week_ago)
                .group_by(Attempt.user_id)
            )
        ).all()
    }

    duel_rows = (
        await session.execute(
            select(Duel).where(Duel.kind == DuelKind.ONLINE, Duel.state == DuelState.FINISHED)
        )
    ).scalars()
    played: dict[int, int] = {}
    won: dict[int, int] = {}
    for duel in duel_rows:
        for uid in (duel.challenger_id, duel.opponent_id):
            if uid:
                played[uid] = played.get(uid, 0) + 1
        if duel.winner_id:
            won[duel.winner_id] = won.get(duel.winner_id, 0) + 1

    users = list(await session.scalars(select(User)))

    if board == "week":
        candidates = [u for u in users if solved_week.get(u.id, 0) > 0]
        candidates.sort(key=lambda u: -solved_week.get(u.id, 0))
    else:
        candidates = [u for u in users if not u.is_guest and played.get(u.id, 0) > 0]
        candidates.sort(key=lambda u: (-u.rating, -played.get(u.id, 0)))

    worn: dict[int, dict] = {}
    for candidate in candidates[: limit + 5]:
        cos = await cosmetics_of(session, candidate.id)
        worn[candidate.id] = cos.model_dump()

    rows = [
        LeaderRow(
            place=i + 1,
            nick_color=worn.get(u.id, {}).get("nick_color"),
            prefix=worn.get(u.id, {}).get("prefix"),
            avatar=worn.get(u.id, {}).get("avatar"),
            frame=worn.get(u.id, {}).get("frame"),
            user_id=u.id,
            display_name=u.display_name,
            rating=u.rating,
            rank=rank_for(u.rating),
            rank_color=rank_color(u.rating),
            duels=played.get(u.id, 0),
            wins=won.get(u.id, 0),
            solved_week=solved_week.get(u.id, 0),
            is_you=u.id == user.id,
        )
        for i, u in enumerate(candidates)
    ]

    your_place = next((r.place for r in rows if r.is_you), None)
    # свою строку показываем всегда, даже если она за пределами топа
    top = rows[:limit]
    if your_place and your_place > limit:
        top = top + [r for r in rows if r.is_you]

    return LeaderboardOut(board=board, rows=top, your_place=your_place)


# --------------------------------------------------------------- статистика за год

class MonthRow(BaseModel):
    month: str          # «2026-08»
    solved: int
    correct: int
    days_active: int


class HourRow(BaseModel):
    hour: int
    attempts: int


class TypeRow(BaseModel):
    number: int
    title: str
    total: int
    correct: int
    accuracy: int
    avg_seconds: int


class StatsYearOut(BaseModel):
    days_total: int
    attempts_total: int
    correct_total: int
    accuracy: int
    minutes_total: int
    avg_seconds: int
    best_day: dict | None
    quizzes: int
    mocks: int
    duels: int
    forecast_secondary: int      # прогноз тестового балла по текущей точности
    months: list[MonthRow]
    hours: list[HourRow]
    by_type: list[TypeRow]


@router.get("/stats/year", response_model=StatsYearOut)
async def stats_year(session: DbSession, user: PlayerUser) -> StatsYearOut:
    """Всё, что накопилось за год: помесячно, по часам и по номерам заданий."""
    from app.core.scoring import secondary_score
    from app.models import MockAttempt

    year_ago = datetime.now(TZ) - timedelta(days=365)
    attempts = list(
        await session.scalars(
            select(Attempt).where(Attempt.user_id == user.id, Attempt.created_at >= year_ago)
        )
    )

    months: dict[str, dict] = {}
    hours: dict[int, int] = {h: 0 for h in range(24)}
    per_day: dict[date, int] = {}

    for attempt in attempts:
        local = attempt.created_at.astimezone(TZ)
        key = f"{local.year}-{local.month:02d}"
        entry = months.setdefault(key, {"solved": 0, "correct": 0, "days": set()})
        entry["solved"] += 1
        entry["correct"] += int(attempt.is_correct)
        entry["days"].add(local.date())
        hours[local.hour] += 1
        per_day[local.date()] = per_day.get(local.date(), 0) + 1

    correct_total = sum(a.is_correct for a in attempts)
    accuracy = round(100 * correct_total / len(attempts)) if attempts else 0
    total_ms = sum(a.time_spent_ms for a in attempts)
    timed = [a for a in attempts if a.time_spent_ms > 0]

    rows = (
        await session.execute(
            select(
                TaskType.number,
                TaskType.title,
                func.count(Attempt.id),
                func.count(Attempt.id).filter(Attempt.is_correct),
                func.avg(Attempt.time_spent_ms),
            )
            .join(Task, Task.id == Attempt.task_id)
            .join(TaskType, TaskType.id == Task.task_type_id)
            .where(Attempt.user_id == user.id)
            .group_by(TaskType.number, TaskType.title)
            .order_by(TaskType.number)
        )
    ).all()

    best = max(per_day.items(), key=lambda kv: kv[1], default=None)

    # прогноз: считаем, что на экзамене будет та же точность на 12 заданиях части 1
    forecast_primary = round(12 * accuracy / 100)

    return StatsYearOut(
        days_total=len(per_day),
        attempts_total=len(attempts),
        correct_total=correct_total,
        accuracy=accuracy,
        minutes_total=round(total_ms / 60000),
        avg_seconds=round(sum(a.time_spent_ms for a in timed) / len(timed) / 1000) if timed else 0,
        best_day={"day": str(best[0]), "solved": best[1]} if best else None,
        quizzes=(
            await session.scalar(
                select(func.count(Quiz.id)).where(
                    Quiz.user_id == user.id, Quiz.finished_at.is_not(None)
                )
            )
        )
        or 0,
        mocks=(
            await session.scalar(
                select(func.count(MockAttempt.id)).where(
                    MockAttempt.user_id == user.id, MockAttempt.finished_at.is_not(None)
                )
            )
        )
        or 0,
        duels=(
            await session.scalar(
                select(func.count(Duel.id)).where(
                    (Duel.challenger_id == user.id) | (Duel.opponent_id == user.id)
                )
            )
        )
        or 0,
        forecast_secondary=secondary_score(forecast_primary),
        months=[
            MonthRow(
                month=key,
                solved=value["solved"],
                correct=value["correct"],
                days_active=len(value["days"]),
            )
            for key, value in sorted(months.items())
        ],
        hours=[HourRow(hour=h, attempts=hours[h]) for h in range(24)],
        by_type=[
            TypeRow(
                number=number,
                title=title,
                total=total,
                correct=correct,
                accuracy=round(100 * correct / total) if total else 0,
                avg_seconds=round((avg_ms or 0) / 1000),
            )
            for number, title, total, correct, avg_ms in rows
        ],
    )


# ------------------------------------------------------------ публичный профиль

class PublicAchievement(BaseModel):
    """Полученное достижение чужого профиля. Прогресс по неполученным не отдаём:
    насколько человек близок к следующему — его дело."""

    code: str
    title: str
    description: str
    rarity: str
    unlocked_at: datetime | None


class PublicProfileOut(BaseModel):
    """Чужой профиль. Только то, чем человек и так хвастается в лидерборде:
    ни контактов, ни кода друга, ни истории ответов."""

    user_id: int
    display_name: str
    rank: str
    rank_color: str
    rating: int
    cosmetics: dict

    solved_total: int
    accuracy: int
    streak_days: int
    streak_record: int
    achievements_unlocked: int
    achievements_total: int
    achievements: list[PublicAchievement]
    duels_played: int
    duels_won: int
    is_friend: bool
    is_you: bool


@router.get("/users/{user_id}", response_model=PublicProfileOut)
async def public_profile(user_id: int, session: DbSession, viewer: PlayerUser) -> PublicProfileOut:
    from app.models import Friendship, FriendshipState

    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "профиль не найден")

    attempts = list(await session.scalars(select(Attempt).where(Attempt.user_id == target.id)))
    solved = len({a.task_id for a in attempts if a.is_correct})
    accuracy = (
        round(100 * sum(a.is_correct for a in attempts) / len(attempts)) if attempts else 0
    )

    days = [a.created_at.astimezone(TZ).date() for a in attempts]
    best_run = run = 0
    for attempt in attempts:
        run = run + 1 if attempt.is_correct else 0
        best_run = max(best_run, run)

    wrong = {a.task_id for a in attempts if not a.is_correct}
    right = {a.task_id for a in attempts if a.is_correct}

    online = list(
        await session.scalars(
            select(Duel).where(
                Duel.kind == DuelKind.ONLINE,
                Duel.state == DuelState.FINISHED,
                (Duel.challenger_id == target.id) | (Duel.opponent_id == target.id),
            )
        )
    )

    counts: dict = {}
    for day in days:
        counts[day] = counts.get(day, 0) + 1

    achievements = _build_achievements(
        solved=solved,
        streak_record=max(_longest_daily_run(days), target.streak_days),
        best_run=best_run,
        perfect=0,
        numbers=0,
        fixed=len(wrong & right),
        accuracy=accuracy,
        attempts=len(attempts),
        duels_played=len(online),
        duel_win_streak=0,
        rating=target.rating,
        fast_correct=sum(1 for a in attempts if a.is_correct and 0 < a.time_spent_ms < 15_000),
        night_attempts=sum(1 for a in attempts if a.created_at.astimezone(TZ).hour < 5),
        best_day=max(counts.values()) if counts else 0,
        came_back=False,
    )

    # Таблица выдачи — главный источник: в ней лежит дата, а часть достижений
    # (идеальный квиз, серия побед) по чужим попыткам заново не пересчитать.
    # Считанные на лету добавляем сверху: у аккаунтов, заведённых до таблицы,
    # она может быть пустой.
    dates = {
        row.code: row.unlocked_at
        for row in await session.scalars(
            select(AchievementUnlock).where(AchievementUnlock.user_id == target.id)
        )
    }
    earned = [a for a in achievements if a.unlocked or a.code in dates]
    earned.sort(key=lambda a: (dates.get(a.code) is None, -(dates[a.code].timestamp() if dates.get(a.code) else 0)))

    friendship = await session.scalar(
        select(Friendship).where(
            Friendship.state == FriendshipState.ACCEPTED,
            ((Friendship.from_user_id == viewer.id) & (Friendship.to_user_id == target.id))
            | ((Friendship.from_user_id == target.id) & (Friendship.to_user_id == viewer.id)),
        )
    )

    return PublicProfileOut(
        user_id=target.id,
        display_name=target.display_name,
        rank=rank_for(target.rating),
        rank_color=rank_color(target.rating),
        rating=target.rating,
        cosmetics=(await cosmetics_of(session, target.id)).model_dump(),
        solved_total=solved,
        accuracy=accuracy,
        streak_days=target.streak_days,
        streak_record=max(_longest_daily_run(days), target.streak_days),
        achievements_unlocked=len(earned),
        achievements_total=len(achievements),
        achievements=[
            PublicAchievement(
                code=a.code,
                title=a.title,
                description=a.description,
                rarity=a.rarity,
                unlocked_at=dates.get(a.code),
            )
            for a in earned
        ],
        duels_played=len(online),
        duels_won=sum(1 for d in online if d.winner_id == target.id),
        is_friend=friendship is not None,
        is_you=target.id == viewer.id,
    )
