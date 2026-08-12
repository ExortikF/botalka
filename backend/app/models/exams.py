from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# Профильная математика: часть 1 — по одному первичному баллу за задание.
# Перевод первичных баллов во вторичные делается по официальной шкале, которая
# меняется по годам, — поэтому её здесь нет, показываем первичные.
DEFAULT_DURATION_MINUTES = 235  # 3 часа 55 минут


class MockStatus(str, enum.Enum):
    DRAFT = "draft"
    LIVE = "live"
    HIDDEN = "hidden"


class MockExam(Base):
    """Готовый пробник: фиксированный набор задач и время на решение."""

    __tablename__ = "mock_exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    subject_slug: Mapped[str] = mapped_column(String(32), default="math_prof", index=True)

    task_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=DEFAULT_DURATION_MINUTES)

    status: Mapped[MockStatus] = mapped_column(
        Enum(MockStatus, native_enum=False), default=MockStatus.DRAFT, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MockAttempt(Base):
    """Одно прохождение пробника. Ответы храним целиком: пробник — это снимок работы."""

    __tablename__ = "mock_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("mock_exams.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    answers: Mapped[dict] = mapped_column(JSON, default=dict)  # {task_id: "ответ"}
    score: Mapped[int | None] = mapped_column(Integer)         # первичные баллы
    total: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)


class ReportStatus(str, enum.Enum):
    NEW = "new"
    RESOLVED = "resolved"
    DECLINED = "declined"


class TaskReport(Base):
    """Жалоба на задачу: «нашли ошибку?». Самый дешёвый способ чинить банк —
    руками тех, кто эти задачи решает."""

    __tablename__ = "task_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    message: Mapped[str] = mapped_column(String(1000))
    given_answer: Mapped[str | None] = mapped_column(String(512))  # что человек вводил

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, native_enum=False), default=ReportStatus.NEW, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
