from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LeagueMember(Base):
    """Участие игрока в лиге конкретной недели.

    Очки здесь не храним — они считаются из попыток за неделю. Иначе пришлось бы
    поддерживать счётчик в актуальном состоянии из всех мест, где решаются задачи,
    и любая пропущенная точка молча ломала бы таблицу.
    """

    __tablename__ = "league_members"
    __table_args__ = (UniqueConstraint("user_id", "week_start"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    week_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    division: Mapped[int] = mapped_column(Integer, default=0)  # индекс в DIVISIONS
    group_no: Mapped[int] = mapped_column(Integer, default=0)
