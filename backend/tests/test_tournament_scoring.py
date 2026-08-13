"""Две тонкие части подсчёта турнира: дневной потолок и фильтры правила.

Оба места легко сломать незаметно — потолок перестанет считаться по московским
суткам, а фильтр начнёт пропускать не те задачи, — и увидеть это можно будет
только по кривой таблице уже во время турнира.
"""

from datetime import UTC, datetime

from app.core.tournaments import _Counter, _task_matches
from app.models import RuleEvent, Task, TournamentRule


def rule(**kwargs) -> TournamentRule:
    defaults = dict(
        id=1,
        event=RuleEvent.TASK_SOLVED,
        points=5,
        daily_cap=None,
        task_numbers=[],
        min_difficulty=None,
        max_difficulty=None,
        exclude_hints=False,
    )
    return TournamentRule(**{**defaults, **kwargs})


def moment(hour: int, day: int = 13) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=UTC)


def test_without_cap_every_event_counts():
    counter = _Counter()
    one = rule()
    assert [counter.take(one, 1, moment(h)) for h in range(5)] == [5] * 5


def test_cap_stops_after_limit():
    counter = _Counter()
    one = rule(daily_cap=2)
    assert [counter.take(one, 1, moment(h)) for h in range(4)] == [5, 5, 0, 0]


def test_cap_resets_next_day():
    counter = _Counter()
    one = rule(daily_cap=1)
    assert counter.take(one, 1, moment(10, day=13)) == 5
    assert counter.take(one, 1, moment(10, day=13)) == 0
    assert counter.take(one, 1, moment(10, day=14)) == 5


def test_cap_is_per_user():
    counter = _Counter()
    one = rule(daily_cap=1)
    assert counter.take(one, 1, moment(10)) == 5
    assert counter.take(one, 2, moment(10)) == 5


def test_cap_uses_moscow_day():
    """21:30 UTC — это уже следующие сутки в Москве, значит потолок сброшен."""
    counter = _Counter()
    one = rule(daily_cap=1)
    assert counter.take(one, 1, datetime(2026, 8, 13, 20, 0, tzinfo=UTC)) == 5
    assert counter.take(one, 1, datetime(2026, 8, 13, 20, 30, tzinfo=UTC)) == 0
    assert counter.take(one, 1, datetime(2026, 8, 13, 21, 30, tzinfo=UTC)) == 5


def task(difficulty: int = 3) -> Task:
    return Task(difficulty=difficulty)


def test_no_filters_matches_everything():
    assert _task_matches(rule(), task(), 7)


def test_number_filter():
    one = rule(task_numbers=[1, 2])
    assert _task_matches(one, task(), 1)
    assert not _task_matches(one, task(), 7)


def test_difficulty_range():
    one = rule(min_difficulty=3, max_difficulty=4)
    assert _task_matches(one, task(3), 1)
    assert _task_matches(one, task(4), 1)
    assert not _task_matches(one, task(2), 1)
    assert not _task_matches(one, task(5), 1)


# --------------------------------------------------------------- контест


from datetime import timedelta

from app.core.tournaments import score_contest
from app.models import ContestProblem, ContestSubmission

START = datetime(2026, 8, 13, 15, 0, tzinfo=UTC)


def problems(*weights: int) -> dict[int, ContestProblem]:
    return {
        i: ContestProblem(task_id=i, points=points, position=i - 1)
        for i, points in enumerate(weights, 1)
    }


def sub(user: int, task: int, minute: int, correct: bool) -> ContestSubmission:
    return ContestSubmission(
        user_id=user,
        task_id=task,
        is_correct=correct,
        answer_raw="x",
        created_at=START + timedelta(minutes=minute),
    )


def score(subs, weights=(100, 250), penalty=10):
    return score_contest(problems(*weights), subs, START, penalty)


def test_clean_solve_costs_only_time():
    [row] = score([sub(1, 1, 12, True)])
    assert (row.points, row.solved, row.penalty) == (100, 1, 12)


def test_wrong_attempts_add_penalty():
    """Две неверные и верная на 20-й: 20 + 2×10."""
    [row] = score([sub(1, 1, 5, False), sub(1, 1, 9, False), sub(1, 1, 20, True)])
    assert row.penalty == 40


def test_wrong_attempts_on_unsolved_are_free():
    """За брошенную задачу не штрафуем, иначе выгоднее не пробовать вовсе."""
    [row] = score([sub(1, 1, 3, True), sub(1, 2, 8, False), sub(1, 2, 9, False)])
    assert (row.points, row.penalty) == (100, 3)


def test_more_points_wins_even_with_bigger_penalty():
    table = score([sub(1, 2, 90, True), sub(2, 1, 2, True)])
    assert [row.user_id for row in table] == [1, 2]


def test_penalty_breaks_the_tie():
    table = score([sub(1, 1, 40, True), sub(2, 1, 5, True)])
    assert [row.user_id for row in table] == [2, 1]


def test_submissions_after_solve_are_ignored():
    [row] = score([sub(1, 1, 4, True), sub(1, 1, 30, False)])
    assert row.penalty == 4


def test_unknown_task_is_skipped():
    assert score([sub(1, 99, 5, True)]) == []
