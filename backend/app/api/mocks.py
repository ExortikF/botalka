"""Пробники: полный вариант на время, с подсчётом баллов в конце.

Отличия от квиза принципиальные:
* ответы **не проверяются по ходу** — как на настоящем экзамене, результат в конце;
* идёт общий таймер на весь вариант, дедлайн хранится на сервере;
* можно свободно перескакивать между заданиями и менять ответы до сдачи.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import DbSession, PlayerUser
from app.core.answers import check_answer
from app.models import Attempt, MockAttempt, MockExam, MockStatus, Task, TaskType

router = APIRouter(prefix="/api/mocks", tags=["mocks"])


class MockCard(BaseModel):
    id: int
    title: str
    description: str | None
    tasks_count: int
    duration_minutes: int
    best_score: int | None
    attempts: int
    active_attempt_id: int | None


class MockTaskOut(BaseModel):
    id: int
    number: int
    title: str
    statement: str
    image_url: str | None
    answer_type: str
    source: str | None


class MockRunOut(BaseModel):
    attempt_id: int
    title: str
    seconds_left: int
    duration_minutes: int
    tasks: list[MockTaskOut]
    answers: dict[str, str]


class ResultItem(BaseModel):
    task_id: int
    number: int
    statement: str
    your_answer: str
    correct_answer: str
    is_correct: bool
    solution: str | None


class MockResultOut(BaseModel):
    attempt_id: int
    title: str
    score: int
    total: int
    percent: int
    spent_minutes: int
    timed_out: bool
    by_number: list[dict]
    items: list[ResultItem]


@router.get("", response_model=list[MockCard])
async def list_mocks(session: DbSession, user: PlayerUser) -> list[MockCard]:
    exams = list(
        await session.scalars(
            select(MockExam).where(MockExam.status == MockStatus.LIVE).order_by(MockExam.id)
        )
    )

    cards: list[MockCard] = []
    for exam in exams:
        attempts = list(
            await session.scalars(
                select(MockAttempt).where(
                    MockAttempt.exam_id == exam.id, MockAttempt.user_id == user.id
                )
            )
        )
        finished = [a for a in attempts if a.finished_at is not None]
        active = next((a for a in attempts if a.finished_at is None), None)
        cards.append(
            MockCard(
                id=exam.id,
                title=exam.title,
                description=exam.description,
                tasks_count=len(exam.task_ids),
                duration_minutes=exam.duration_minutes,
                best_score=max((a.score or 0 for a in finished), default=None),
                attempts=len(finished),
                active_attempt_id=active.id if active else None,
            )
        )
    return cards


async def _tasks_of(session: DbSession, exam: MockExam) -> list[Task]:
    tasks = []
    for task_id in exam.task_ids:
        task = await session.get(Task, task_id)
        if task is None:
            continue
        await session.refresh(task, ["task_type"])
        tasks.append(task)
    return tasks


def _source_label(task: Task) -> str | None:
    from app.api.quiz import _source_label as label

    return label(task)


@router.post("/{exam_id}/start", response_model=MockRunOut)
async def start_mock(exam_id: int, session: DbSession, user: PlayerUser) -> MockRunOut:
    exam = await session.get(MockExam, exam_id)
    if exam is None or exam.status is not MockStatus.LIVE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "пробник не найден")

    attempt = await session.scalar(
        select(MockAttempt).where(
            MockAttempt.exam_id == exam.id,
            MockAttempt.user_id == user.id,
            MockAttempt.finished_at.is_(None),
        )
    )
    if attempt is None:
        attempt = MockAttempt(
            exam_id=exam.id,
            user_id=user.id,
            answers={},
            total=len(exam.task_ids),
            deadline_at=datetime.now(UTC) + timedelta(minutes=exam.duration_minutes),
        )
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)

    return await _run_payload(session, exam, attempt)


async def _run_payload(session: DbSession, exam: MockExam, attempt: MockAttempt) -> MockRunOut:
    tasks = await _tasks_of(session, exam)
    left = int((attempt.deadline_at - datetime.now(UTC)).total_seconds())
    return MockRunOut(
        attempt_id=attempt.id,
        title=exam.title,
        seconds_left=max(0, left),
        duration_minutes=exam.duration_minutes,
        answers={str(k): v for k, v in (attempt.answers or {}).items()},
        tasks=[
            MockTaskOut(
                id=t.id,
                number=t.task_type.number,
                title=t.task_type.title,
                statement=t.statement,
                image_url=t.image_url,
                answer_type=t.answer_type.value,
                source=_source_label(t),
            )
            for t in tasks
        ],
    )


@router.get("/attempt/{attempt_id}", response_model=MockRunOut)
async def resume(attempt_id: int, session: DbSession, user: PlayerUser) -> MockRunOut:
    attempt = await _own_attempt(session, attempt_id, user.id)
    if attempt.finished_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "пробник уже сдан")
    exam = await session.get(MockExam, attempt.exam_id)
    return await _run_payload(session, exam, attempt)


async def _own_attempt(session: DbSession, attempt_id: int, user_id: int) -> MockAttempt:
    attempt = await session.get(MockAttempt, attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "попытка не найдена")
    return attempt


class SaveAnswerIn(BaseModel):
    task_id: int
    answer: str = Field(default="", max_length=512)


@router.post("/attempt/{attempt_id}/answer")
async def save_answer(
    attempt_id: int, payload: SaveAnswerIn, session: DbSession, user: PlayerUser
) -> dict:
    """Просто складывает ответ в черновик. Проверка — только при сдаче."""
    attempt = await _own_attempt(session, attempt_id, user.id)
    if attempt.finished_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "пробник уже сдан")

    answers = dict(attempt.answers or {})
    if payload.answer.strip():
        answers[str(payload.task_id)] = payload.answer
    else:
        answers.pop(str(payload.task_id), None)
    attempt.answers = answers
    await session.commit()
    return {"saved": len(answers)}


@router.post("/attempt/{attempt_id}/finish", response_model=MockResultOut)
async def finish(attempt_id: int, session: DbSession, user: PlayerUser) -> MockResultOut:
    attempt = await _own_attempt(session, attempt_id, user.id)
    exam = await session.get(MockExam, attempt.exam_id)

    if attempt.finished_at is None:
        timed_out = datetime.now(UTC) > attempt.deadline_at
        tasks = await _tasks_of(session, exam)
        answers = attempt.answers or {}

        score = 0
        for task in tasks:
            given = answers.get(str(task.id), "")
            correct = bool(given) and check_answer(
                task.answer_type, task.answer_payload, given
            )
            score += int(correct)
            # пишем в общую статистику: пробник тоже тренировка
            session.add(
                Attempt(
                    user_id=user.id,
                    task_id=task.id,
                    quiz_id=None,
                    answer_raw=given[:512],
                    is_correct=correct,
                    time_spent_ms=0,
                )
            )

        attempt.score = score
        attempt.timed_out = timed_out
        attempt.finished_at = datetime.now(UTC)
        await session.commit()

    return await _result_payload(session, exam, attempt)


@router.get("/attempt/{attempt_id}/result", response_model=MockResultOut)
async def result(attempt_id: int, session: DbSession, user: PlayerUser) -> MockResultOut:
    attempt = await _own_attempt(session, attempt_id, user.id)
    if attempt.finished_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "пробник ещё не сдан")
    exam = await session.get(MockExam, attempt.exam_id)
    return await _result_payload(session, exam, attempt)


async def _result_payload(
    session: DbSession, exam: MockExam, attempt: MockAttempt
) -> MockResultOut:
    tasks = await _tasks_of(session, exam)
    answers = attempt.answers or {}

    items: list[ResultItem] = []
    per_number: dict[int, dict] = {}
    for task in tasks:
        given = answers.get(str(task.id), "")
        correct = bool(given) and check_answer(task.answer_type, task.answer_payload, given)
        number = task.task_type.number
        entry = per_number.setdefault(number, {"number": number, "total": 0, "correct": 0})
        entry["total"] += 1
        entry["correct"] += int(correct)

        items.append(
            ResultItem(
                task_id=task.id,
                number=number,
                statement=task.statement,
                your_answer=given,
                correct_answer=str((task.answer_payload or {}).get("value", "")),
                is_correct=correct,
                solution=task.solution,
            )
        )

    spent = int(((attempt.finished_at or datetime.now(UTC)) - attempt.started_at).total_seconds() / 60)
    total = len(tasks)
    return MockResultOut(
        attempt_id=attempt.id,
        title=exam.title,
        score=attempt.score or 0,
        total=total,
        percent=round(100 * (attempt.score or 0) / total) if total else 0,
        spent_minutes=spent,
        timed_out=attempt.timed_out,
        by_number=sorted(per_number.values(), key=lambda r: r["number"]),
        items=items,
    )
