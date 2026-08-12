from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FriendshipState(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"


class Friendship(Base):
    """Дружба хранится одной строкой на пару.

    `from_user_id` — тот, кто отправил заявку. Пара уникальна в одну сторону;
    обратную заявку от того же человека ловим отдельной проверкой в API.
    """

    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("from_user_id", "to_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    state: Mapped[FriendshipState] = mapped_column(
        Enum(FriendshipState, native_enum=False), default=FriendshipState.PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
