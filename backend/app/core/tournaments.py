"""Подсчёт очков турнира.

Очки нигде не хранятся, а считаются из попыток, квизов, дуэлей и пробников за
период турнира. Так сделано намеренно: правила можно поправить прямо во время
турнира и сразу увидеть, что получилось, а хранимый счётчик пришлось бы
обновлять из всех мест, где решаются задачи, — и одна пропущенная точка тихо
испортила бы таблицу.

Дневной потолок в правиле считается по московским суткам: турнир объявляется
людям в «по дням», а не «по UTC».
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.quiz import STREAK_TZ
from app.models import (
    Attempt,
    ContestProblem,
    ContestSubmission,
    Duel,
    DuelKind,
    DuelState,
    MockAttempt,
    Quiz,
    RuleEvent,
    Task,
    TaskType,
    Tournament,
    TournamentFormat,
    TournamentRule,
)


@dataclass
class Standing:
    user_id: int
    points: int = 0
    by_event: dict[str, int] = field(default_factory=dict)

    # Только для контеста: штрафное время в минутах и разбор по задачам.
    penalty: int = 0
    solved: int = 0
    problems: dict[int, "ProblemResult"] = field(default_factory=dict)


@dataclass
class ProblemResult:
    """Как участник прошёл одну задачу контеста."""

    solved: bool = False
    wrong: int = 0            # неверных попыток до верной
    minute: int | None = None  # минута контеста, когда сдал
    points: int = 0


def _day_of(moment: datetime) -> date:
    return moment.astimezone(STREAK_TZ).date()


class _Counter:
    """Начисление с учётом дневного потолка."""

    def __init__(self) -> None:
        self._used: dict[tuple[int, int, date], int] = defaultdict(int)

    def take(self, rule: TournamentRule, user_id: int, moment: datetime) -> int:
        if rule.daily_cap is None:
            return rule.points

        key = (rule.id, user_id, _day_of(moment))
        if self._used[key] >= rule.daily_cap:
            return 0

        self._used[key] += 1
        return rule.points


def _task_matches(rule: TournamentRule, task: Task, number: int) -> bool:
    if rule.task_numbers and number not in rule.task_numbers:
        return False
    if rule.min_difficulty is not None and task.difficulty < rule.min_difficulty:
        return False
    if rule.max_difficulty is not None and task.difficulty > rule.max_difficulty:
        return False
    return True


async def contest_standings(
    session: AsyncSession, tournament: Tournament
) -> list[Standing]:
    """Таблица контеста: баллы за решённые задачи, при равенстве — штрафное время.

    Штраф начисляется только по задачам, которые в итоге решены: наказывать за
    брошенную задачу не за что, иначе выгоднее не пробовать вовсе. Считается как
    минута сдачи плюс `penalty_minutes` за каждую неверную попытку до неё —
    так же, как на школьных олимпиадах и Codeforces.
    """
    problems = {p.task_id: p for p in tournament.problems}
    if not problems:
        return []

    subs = list(
        await session.scalars(
            select(ContestSubmission)
            .where(
                ContestSubmission.tournament_id == tournament.id,
                ContestSubmission.upsolve.is_(False),
            )
            .order_by(ContestSubmission.id)
        )
    )

    return score_contest(
        problems=problems,
        submissions=subs,
        starts_at=tournament.starts_at,
        penalty_minutes=tournament.penalty_minutes,
    )


def score_contest(
    problems: dict[int, "ContestProblem"],
    submissions: list["ContestSubmission"],
    starts_at: datetime,
    penalty_minutes: int,
) -> list[Standing]:
    """Чистый подсчёт: попытки уже отобраны, порядок — по возрастанию id.

    Вынесено из работы с базой, чтобы формулу штрафа можно было проверить
    тестами: именно она ломается незаметно.
    """
    rows: dict[int, Standing] = {}

    for sub in submissions:
        problem = problems.get(sub.task_id)
        if problem is None:
            continue

        row = rows.setdefault(sub.user_id, Standing(user_id=sub.user_id))
        result = row.problems.setdefault(sub.task_id, ProblemResult())
        if result.solved:
            continue  # после верного ответа задача закрыта

        if not sub.is_correct:
            result.wrong += 1
            continue

        minute = max(
            0,
            int((sub.created_at.replace(tzinfo=UTC) - starts_at).total_seconds() // 60),
        )
        result.solved = True
        result.minute = minute
        result.points = problem.points

        row.points += problem.points
        row.solved += 1
        row.penalty += minute + result.wrong * penalty_minutes

    ranked = [row for row in rows.values() if row.solved > 0]
    ranked.sort(key=lambda row: (-row.points, row.penalty, row.user_id))
    return ranked


async def standings(
    session: AsyncSession, tournament: Tournament
) -> list[Standing]:
    """Таблица турнира, отсортированная по очкам. Пустые участники не попадают."""
    if tournament.format is TournamentFormat.CONTEST:
        return await contest_standings(session, tournament)

    rules = list(tournament.rules)
    if not rules:
        return []

    start, end = tournament.starts_at, tournament.ends_at
    counter = _Counter()
    totals: dict[int, Standing] = {}

    def add(user_id: int, event: RuleEvent, amount: int) -> None:
        if amount == 0:
            return
        row = totals.setdefault(user_id, Standing(user_id=user_id))
        row.points += amount
        row.by_event[event.value] = row.by_event.get(event.value, 0) + amount

    # ---------------------------------------------------------------- задачи
    task_rules = [r for r in rules if r.event in (RuleEvent.TASK_SOLVED, RuleEvent.DAILY_SOLVED)]
    if task_rules:
        rows = (
            await session.execute(
                select(Attempt, Task, TaskType.number)
                .join(Task, Task.id == Attempt.task_id)
                .join(TaskType, TaskType.id == Task.task_type_id)
                .where(
                    Attempt.created_at >= start,
                    Attempt.created_at <= end,
                    Attempt.is_correct.is_(True),
                )
                .order_by(Attempt.id)
            )
        ).all()

        # только первое верное решение задачи — иначе одну задачу решают по кругу
        seen: set[tuple[int, int]] = set()
        for attempt, task, number in rows:
            key = (attempt.user_id, attempt.task_id)
            if key in seen:
                continue
            seen.add(key)

            for rule in task_rules:
                if rule.event is RuleEvent.DAILY_SOLVED and attempt.quiz_id is not None:
                    continue  # задача дня решается вне квиза
                if rule.exclude_hints and attempt.used_hint:
                    continue
                if not _task_matches(rule, task, number):
                    continue
                add(attempt.user_id, rule.event, counter.take(rule, attempt.user_id, attempt.created_at))

    # ---------------------------------------------------------------- квизы
    quiz_rules = [r for r in rules if r.event in (RuleEvent.QUIZ_FINISHED, RuleEvent.QUIZ_PERFECT)]
    if quiz_rules:
        quizzes = list(
            await session.scalars(
                select(Quiz).where(
                    Quiz.finished_at.is_not(None),
                    Quiz.finished_at >= start,
                    Quiz.finished_at <= end,
                )
            )
        )
        for quiz in quizzes:
            perfect = quiz.score == len(quiz.task_ids)
            for rule in quiz_rules:
                if rule.event is RuleEvent.QUIZ_PERFECT and not perfect:
                    continue
                add(quiz.user_id, rule.event, counter.take(rule, quiz.user_id, quiz.finished_at))

    # ---------------------------------------------------------------- дуэли
    duel_rules = [r for r in rules if r.event in (RuleEvent.DUEL_WIN, RuleEvent.DUEL_PLAYED)]
    if duel_rules:
        duels = list(
            await session.scalars(
                select(Duel).where(
                    Duel.kind == DuelKind.ONLINE,
                    Duel.state == DuelState.FINISHED,
                    Duel.finished_at >= start,
                    Duel.finished_at <= end,
                )
            )
        )
        for duel in duels:
            for user_id in (duel.challenger_id, duel.opponent_id):
                if user_id is None:
                    continue
                for rule in duel_rules:
                    if rule.event is RuleEvent.DUEL_WIN and duel.winner_id != user_id:
                        continue
                    add(user_id, rule.event, counter.take(rule, user_id, duel.finished_at))

    # ------------------------------------------------------------- пробники
    mock_rules = [r for r in rules if r.event is RuleEvent.MOCK_FINISHED]
    if mock_rules:
        attempts = list(
            await session.scalars(
                select(MockAttempt).where(
                    MockAttempt.finished_at.is_not(None),
                    MockAttempt.finished_at >= start,
                    MockAttempt.finished_at <= end,
                )
            )
        )
        for attempt in attempts:
            for rule in mock_rules:
                add(attempt.user_id, rule.event, counter.take(rule, attempt.user_id, attempt.finished_at))

    ranked = [row for row in totals.values() if row.points > 0]
    ranked.sort(key=lambda row: (-row.points, row.user_id))
    return ranked
