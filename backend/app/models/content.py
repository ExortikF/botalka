from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class AnswerType(str, enum.Enum):
    NUMBER = "number"
    NUMBER_TOLERANCE = "number_tolerance"
    STRING = "string"
    DIGITS = "digits"
    MULTI = "multi"


class SourceKind(str, enum.Enum):
    """Откуда задача. Показывается ученику мелким шрифтом под условием."""

    OWN = "own"          # собственная
    FIPI_BANK = "fipi"   # открытый банк ФИПИ
    EXAM = "exam"        # реальный вариант прошлых лет
    DEMO = "demo"        # демоверсия ФИПИ
    BOOK = "book"        # сборник, учебник
    OTHER = "other"


class TaskStatus(str, enum.Enum):
    DRAFT = "draft"
    LIVE = "live"
    BROKEN = "broken"


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))

    task_types: Mapped[list[TaskType]] = relationship(back_populates="subject")


class TaskType(Base):
    """Тип задания = номер в КИМ. Нумерация меняется по годам, поэтому year_spec."""

    __tablename__ = "task_types"
    __table_args__ = (UniqueConstraint("subject_id", "number", "year_spec"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    year_spec: Mapped[int] = mapped_column(Integer, default=2026)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)

    subject: Mapped[Subject] = relationship(back_populates="task_types")
    tasks: Mapped[list[Task]] = relationship(back_populates="task_type")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    task_type_id: Mapped[int] = mapped_column(ForeignKey("task_types.id"), index=True)

    statement: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(512))

    answer_type: Mapped[AnswerType] = mapped_column(Enum(AnswerType, native_enum=False))
    # хранится строкой/структурой в зависимости от типа: см. app/core/answers.py
    answer_payload: Mapped[dict] = mapped_column(JSON)

    solution: Mapped[str | None] = mapped_column(Text)
    hints: Mapped[list] = mapped_column(JSON, default=list)

    difficulty: Mapped[int] = mapped_column(Integer, default=3)

    # Источник задачи. Ученику важно видеть, что задача не выдумана, а реально была.
    source: Mapped[str | None] = mapped_column(String(256))  # человекочитаемая подпись
    source_kind: Mapped[SourceKind] = mapped_column(
        Enum(SourceKind, native_enum=False), default=SourceKind.OWN
    )
    source_year: Mapped[int | None] = mapped_column(Integer)
    source_ref: Mapped[str | None] = mapped_column(String(128))  # номер в источнике
    source_url: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False), default=TaskStatus.DRAFT, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task_type: Mapped[TaskType] = relationship(back_populates="tasks")
