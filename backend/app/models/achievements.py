from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AchievementUnlock(Base):
    """Достижения считаются на лету из попыток, поэтому сам момент получения
    нигде не виден. Эта таблица хранит факт выдачи: по ней понятно, что́ человек
    получил именно сейчас, и её же можно показать датой в профиле."""

    __tablename__ = "achievement_unlocks"
    __table_args__ = (UniqueConstraint("user_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
