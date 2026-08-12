from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

STARTING_RATING = 1000


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # решать можно без регистрации: у гостя tg_id пуст, прогресс уже копится.
    # Вход через Telegram потом привязывается к этому же пользователю.
    tg_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    username: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(128))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    # короткий код, по которому тебя добавляют в друзья. Работает и у гостей,
    # у которых нет username в Telegram
    friend_code: Mapped[str | None] = mapped_column(String(12), unique=True, index=True)

    rating: Mapped[int] = mapped_column(Integer, default=STARTING_RATING)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    streak_last_date: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
