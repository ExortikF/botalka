"""Начисление монет.

Правило, ради которого всё это устроено именно так: **монеты даются за результат,
а не за время в приложении**. Поэтому за задачу платим только при первом верном
решении — иначе одну лёгкую задачу можно перерешивать бесконечно.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Attempt, CoinReason, CoinTransaction, User

REWARDS = {
    CoinReason.TASK_FIRST_SOLVE: 1,
    CoinReason.QUIZ_PERFECT: 10,
    CoinReason.DAILY_FIRST_QUIZ: 5,
    CoinReason.DUEL_WIN: 15,
    CoinReason.DUEL_LOSS: 3,
    CoinReason.MOCK_FINISHED: 30,
    CoinReason.SUGGESTION_APPROVED: 50,
}

MAX_STREAK_BONUS = 7  # дальше не растёт, иначе длинная серия даёт слишком много


async def award(
    session: AsyncSession,
    user: User,
    reason: CoinReason,
    amount: int | None = None,
    note: str | None = None,
) -> int:
    """Начисляет монеты и пишет транзакцию. Возвращает начисленное."""
    value = REWARDS.get(reason, 0) if amount is None else amount
    if value == 0:
        return 0

    user.coins = max(0, user.coins + value)
    session.add(CoinTransaction(user_id=user.id, amount=value, reason=reason, note=note))
    return value


async def is_first_correct(session: AsyncSession, user_id: int, task_id: int) -> bool:
    """Решал ли пользователь эту задачу верно раньше.

    Вызывать **до** записи текущей попытки, иначе она сама себя посчитает.
    """
    earlier = await session.scalar(
        select(func.count(Attempt.id)).where(
            Attempt.user_id == user_id,
            Attempt.task_id == task_id,
            Attempt.is_correct.is_(True),
        )
    )
    return not earlier
