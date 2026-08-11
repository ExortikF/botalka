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


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mode: Mapped[QuizMode] = mapped_column(Enum(QuizMode, native_enum=False), default=QuizMode.SOLO)
    task_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))

    score: Mapped[int] = mapped_column(Integer, default=0)
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
    time_spent_ms: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
