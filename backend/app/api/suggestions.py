"""«Предложи свою задачу» — приём задач от учеников и их проверка.

Присланное **не попадает в банк автоматически**: одна ошибка в ответе испортит
статистику всем, кто эту задачу решит, а разбираться потом будет некому. Поэтому
задача живёт отдельной сущностью, пока её не подтвердят руками, и только тогда
превращается в обычную запись банка.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DbSession, PlayerUser
from app.core.coins import award
from app.models import (
    AnswerType,
    CoinReason,
    SourceKind,
    SuggestionStatus,
    Task,
    TaskStatus,
    TaskSuggestion,
    TaskType,
    User,
)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])

DAILY_LIMIT = 5  # чтобы одним махом не завалили модерацию


class SuggestionIn(BaseModel):
    number: int = Field(ge=1, le=19)
    statement: str = Field(min_length=20, max_length=4000)
    answer: str = Field(min_length=1, max_length=200)
    solution: str | None = Field(default=None, max_length=4000)
    source: str | None = Field(default=None, max_length=256)


class SuggestionOut(BaseModel):
    id: int
    number: int
    statement: str
    answer: str
    status: str
    moderator_note: str | None
    created_at: datetime


def _out(row: TaskSuggestion) -> SuggestionOut:
    return SuggestionOut(
        id=row.id,
        number=row.number,
        statement=row.statement,
        answer=row.answer,
        status=row.status.value,
        moderator_note=row.moderator_note,
        created_at=row.created_at,
    )


@router.post("", response_model=SuggestionOut, status_code=status.HTTP_201_CREATED)
async def suggest(payload: SuggestionIn, session: DbSession, user: PlayerUser) -> SuggestionOut:
    today = datetime.now(UTC).date()
    mine = list(
        await session.scalars(
            select(TaskSuggestion).where(TaskSuggestion.user_id == user.id)
        )
    )
    if sum(1 for s in mine if s.created_at.date() == today) >= DAILY_LIMIT:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"больше {DAILY_LIMIT} задач в день не принимаем — присылай остальные завтра",
        )

    row = TaskSuggestion(
        user_id=user.id,
        number=payload.number,
        statement=payload.statement.strip(),
        answer=payload.answer.strip(),
        solution=(payload.solution or "").strip() or None,
        source=(payload.source or "").strip() or None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _out(row)


@router.get("", response_model=list[SuggestionOut])
async def my_suggestions(session: DbSession, user: PlayerUser) -> list[SuggestionOut]:
    rows = await session.scalars(
        select(TaskSuggestion)
        .where(TaskSuggestion.user_id == user.id)
        .order_by(TaskSuggestion.id.desc())
        .limit(50)
    )
    return [_out(row) for row in rows]


# --------------------------------------------------------------------- модерация


class ReviewIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    subject_slug: str = "math_prof"


async def approve_suggestion(
    session: DbSession, row: TaskSuggestion, subject_slug: str
) -> Task:
    """Превращает присланное в обычную задачу банка.

    Задача создаётся черновиком: даже проверенный текст стоит один раз увидеть
    в предпросмотре, прежде чем он уйдёт людям.
    """
    task_type = await session.scalar(
        select(TaskType)
        .join(TaskType.subject)
        .where(TaskType.number == row.number)
        .order_by(TaskType.year_spec.desc())
    )
    if task_type is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"нет типа задания с номером {row.number}"
        )

    author = await session.get(User, row.user_id)
    task = Task(
        slug=f"user-{row.id}",
        task_type_id=task_type.id,
        statement=row.statement,
        answer_type=AnswerType.NUMBER,
        answer_payload={"value": row.answer},
        solution=row.solution,
        source=row.source or f"прислал {author.display_name if author else 'ученик'}",
        source_kind=SourceKind.OWN,
        status=TaskStatus.DRAFT,
    )
    session.add(task)
    await session.flush()

    row.status = SuggestionStatus.APPROVED
    row.task_id = task.id
    row.reviewed_at = datetime.now(UTC)

    if author is not None:
        await award(session, author, CoinReason.SUGGESTION_APPROVED, note=f"задача #{row.id}")

    await session.commit()
    return task
