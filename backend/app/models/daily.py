from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DailyStart(Base):
    """Когда человек открыл условие задачи дня.

    Хранится на сервере, а не в браузере, по двум причинам: вкладку
    переключают и перезагружают — время не должно начинаться заново, — и
    время решения определяет место в таблице, а такому клиент верить нельзя.
    """

    __tablename__ = "daily_starts"
    __table_args__ = (UniqueConstraint("user_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
