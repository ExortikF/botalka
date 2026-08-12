from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
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
