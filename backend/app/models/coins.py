from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CoinReason(str, enum.Enum):
    TASK_FIRST_SOLVE = "task_first_solve"   # первое верное решение задачи
    QUIZ_PERFECT = "quiz_perfect"           # квиз без единой ошибки
    DAILY_FIRST_QUIZ = "daily_first_quiz"   # первый квиз за день
    STREAK_DAY = "streak_day"               # день серии
    DUEL_WIN = "duel_win"
    DUEL_LOSS = "duel_loss"                 # утешительные: чтобы не боялись играть
    MOCK_FINISHED = "mock_finished"
    PURCHASE = "purchase"                   # трата в магазине
    ADMIN = "admin"                         # ручная правка


class CoinTransaction(Base):
    """История начислений. Без неё невозможно разобрать «у меня пропали монеты»
    и посчитать, сколько всего валюты в обороте."""

    __tablename__ = "coin_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # может быть отрицательным
    reason: Mapped[CoinReason] = mapped_column(Enum(CoinReason, native_enum=False), index=True)
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
