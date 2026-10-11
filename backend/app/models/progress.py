from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class QuizMode(str, enum.Enum):
    SOLO = "solo"
    DUEL = "duel"
    DAILY = "daily"
    CHALLENGE = "challenge"


class DuelKind(str, enum.Enum):
    LINK = "link"        # асинхронная: каждый решает в своё время
    ONLINE = "online"    # живой матч: вопрос приходит обоим одновременно


class DuelState(str, enum.Enum):
    WAITING = "waiting"      # вызов создан, соперник ещё не прошёл
    FINISHED = "finished"    # прошли оба
    EXPIRED = "expired"
    DECLINED = "declined"    # адресный вызов, от которого отказались


class Duel(Base):
    """Асинхронная дуэль: оба игрока решают один и тот же набор задач.

    Реалтайма здесь нет намеренно — вызов по ссылке работает, даже когда соперник
    не в сети, а это единственный сценарий, пока игроков мало.
    """

    __tablename__ = "duels"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    kind: Mapped[DuelKind] = mapped_column(
        Enum(DuelKind, native_enum=False), default=DuelKind.LINK, index=True
    )
    task_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))

    challenger_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    opponent_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    challenger_quiz_id: Mapped[int | None] = mapped_column(Integer)
    opponent_quiz_id: Mapped[int | None] = mapped_column(Integer)

    challenger_score: Mapped[int | None] = mapped_column(Integer)
    opponent_score: Mapped[int | None] = mapped_column(Integer)
    challenger_time_ms: Mapped[int | None] = mapped_column(Integer)
    opponent_time_ms: Mapped[int | None] = mapped_column(Integer)

    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    # рейтинг меняется только в живых матчах
    challenger_rating_delta: Mapped[int | None] = mapped_column(Integer)
    opponent_rating_delta: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[DuelState] = mapped_column(
        Enum(DuelState, native_enum=False), default=DuelState.WAITING, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mode: Mapped[QuizMode] = mapped_column(Enum(QuizMode, native_enum=False), default=QuizMode.SOLO)
    task_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    duel_id: Mapped[int | None] = mapped_column(ForeignKey("duels.id"), index=True)

    score: Mapped[int] = mapped_column(Integer, default=0)
    coins_earned: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Attempt(Base):
    """Каждая попытка ответа. Основа статистики, повторений и персонального плана —
    поэтому пишем всегда, даже когда кажется, что запись «лишняя»."""

    __tablename__ = "attempts"
    __table_args__ = (
        Index("ix_attempts_user_created", "user_id", "created_at"),
        Index("ix_attempts_task", "task_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    quiz_id: Mapped[int | None] = mapped_column(ForeignKey("quizzes.id"), index=True)

    answer_raw: Mapped[str] = mapped_column(String(512))
    is_correct: Mapped[bool] = mapped_column(Boolean)
    # подсказка не отменяет зачёт, но задача помечается «решено с подсказкой»
    used_hint: Mapped[bool] = mapped_column(Boolean, default=False)
    time_spent_ms: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
