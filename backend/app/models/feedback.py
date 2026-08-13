from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class IdeaStatus(str, enum.Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class Idea(Base):
    """«Есть идеи по улучшению сайта?» — предложения от пользователей."""

    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(String(2000))
    page: Mapped[str | None] = mapped_column(String(200))  # откуда отправили

    status: Mapped[IdeaStatus] = mapped_column(
        Enum(IdeaStatus, native_enum=False), default=IdeaStatus.NEW, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SuggestionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TaskSuggestion(Base):
    """Задача, присланная учеником. В банк попадает только после проверки:
    иначе одна ошибка в ответе испортит статистику всем, кто её решит."""

    __tablename__ = "task_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    number: Mapped[int] = mapped_column(Integer)  # номер в КИМ
    statement: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(String(200))
    solution: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(256))  # откуда задача

    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, native_enum=False), default=SuggestionStatus.PENDING, index=True
    )
    moderator_note: Mapped[str | None] = mapped_column(String(500))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))  # что создали

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
