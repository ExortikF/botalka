"""Профиль: статистика, активность по дням и достижения.

Достижения считаются из попыток на лету, а не хранятся отдельной таблицей.
Пока их немного, это проще и не рассинхронизируется с данными; когда появится
всплывающее уведомление «получено», понадобится хранить факт и дату выдачи.
"""

from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import DbSession, PlayerUser
from app.models import Attempt, Quiz, Task, TaskStatus, TaskType, User

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


class ProfileOut(BaseModel):
    display_name: str
    is_guest: bool
    avatar_url: str | None
    rating: int | None  # None пока нет дуэлей — рейтинг считается только по ним

    solved_total: int
    correct_total: int
    accuracy: int
    streak_days: int
    streak_record: int
    best_correct_run: int
    perfect_quizzes: int
    numbers_covered: int

    tasks_total: int
    unsolved: int

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


def _build_achievements(
    solved: int,
    streak_record: int,
    best_run: int,
    perfect: int,
    numbers: int,
    fixed_mistakes: int,
) -> list[Achievement]:
    raw = [
        ("first_blood", "Первая задача", "Решить одну задачу", "bronze", min(solved, 1), 1),
        ("solved_50", "Полсотни", "Решить 50 задач", "bronze", min(solved, 50), 50),
        ("solved_100", "Сотня", "Решить 100 задач", "silver", min(solved, 100), 100),
        ("solved_500", "Пятьсот", "Решить 500 задач", "gold", min(solved, 500), 500),
        ("week_streak", "Неделя без пропусков", "7 дней подряд", "silver",
         min(streak_record, 7), 7),
        ("two_weeks", "Две недели без пропусков", "14 дней подряд", "gold",
         min(streak_record, 14), 14),
        ("run_10", "Десять подряд", "10 верных ответов подряд", "silver",
         min(best_run, 10), 10),
        ("perfect_quiz", "Без единой ошибки", "Пройти квиз целиком без ошибок", "silver",
         min(perfect, 1), 1),
        ("all_numbers", "Полный охват", "Решить хотя бы по одной задаче каждого номера",
         "gold", numbers, 12),
        ("fix_10", "Работа над ошибками", "Исправить 10 задач, где ошибался", "silver",
         min(fixed_mistakes, 10), 10),
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

    # исправленные ошибки: сначала ошибся, потом на этой же задаче ответил верно
    wrong_tasks = {a.task_id for a in attempts if not a.is_correct}
    fixed = sum(
        1
        for task_id in wrong_tasks
        if any(a.task_id == task_id and a.is_correct for a in attempts)
    )

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

    return ProfileOut(
        display_name=user.display_name,
        is_guest=user.is_guest,
        avatar_url=user.avatar_url,
        rating=None,
        solved_total=solved_total,
        correct_total=correct_total,
        accuracy=accuracy,
        streak_days=user.streak_days,
        streak_record=streak_record,
        best_correct_run=best_run,
        perfect_quizzes=perfect,
        numbers_covered=numbers_covered,
        tasks_total=tasks_total,
        unsolved=max(0, tasks_total - correct_total),
        activity=activity,
        achievements=_build_achievements(
            solved_total, streak_record, best_run, perfect, numbers_covered, fixed
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
