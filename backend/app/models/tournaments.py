from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class TournamentStatus(str, enum.Enum):
    DRAFT = "draft"          # виден только в админке
    PUBLISHED = "published"  # виден всем; идёт или ещё не начался
    FINISHED = "finished"    # итоги подведены, награды выданы


class TournamentScope(str, enum.Enum):
    USER = "user"
    CLAN = "clan"  # клановые войны — тот же турнир, только зачёт командный


class RuleEvent(str, enum.Enum):
    """За что начисляются очки. Список закрытый: каждое событие нужно уметь
    посчитать из уже существующих таблиц, произвольные правила писать негде."""

    TASK_SOLVED = "task_solved"          # первое верное решение задачи
    QUIZ_FINISHED = "quiz_finished"
    QUIZ_PERFECT = "quiz_perfect"
    DUEL_WIN = "duel_win"
    DUEL_PLAYED = "duel_played"
    MOCK_FINISHED = "mock_finished"
    DAILY_SOLVED = "daily_solved"


class Tournament(Base):
    """Соревнование с настраиваемыми правилами.

    Смысл сущности в том, чтобы новый турнир заводился из админки, а не кодом:
    «марафон планиметрии на выходные» и «неделя дуэлей» отличаются только
    набором правил и периодом.
    """

    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(16), default="#0088b0")

    scope: Mapped[TournamentScope] = mapped_column(
        Enum(TournamentScope, native_enum=False), default=TournamentScope.USER
    )
    status: Mapped[TournamentStatus] = mapped_column(
        Enum(TournamentStatus, native_enum=False),
        default=TournamentStatus.DRAFT,
        index=True,
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # Условия входа. Пусто — участвуют все.
    min_rating: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rules: Mapped[list[TournamentRule]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
    prizes: Mapped[list[TournamentPrize]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )


class TournamentRule(Base):
    """Одно правило начисления: событие, фильтры, очки и дневной потолок.

    Потолок обязателен по смыслу, а не по коду: турнир — единственное место,
    где выгодно долбить одно и то же действие, и без ограничения победит тот,
    кто просидел сутки на самом дешёвом номере.
    """

    __tablename__ = "tournament_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )

    event: Mapped[RuleEvent] = mapped_column(Enum(RuleEvent, native_enum=False))
    points: Mapped[int] = mapped_column(Integer, default=1)
    daily_cap: Mapped[int | None] = mapped_column(Integer)  # событий в день, None — без потолка

    # Фильтры. Пустой список — без ограничения.
    task_numbers: Mapped[list] = mapped_column(JSON, default=list)  # номера КИМ
    min_difficulty: Mapped[int | None] = mapped_column(Integer)
    max_difficulty: Mapped[int | None] = mapped_column(Integer)
    exclude_hints: Mapped[bool] = mapped_column(Boolean, default=False)

    tournament: Mapped[Tournament] = relationship(back_populates="rules")


class TournamentPrize(Base):
    """Награда за диапазон мест: с place_from по place_to включительно."""

    __tablename__ = "tournament_prizes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )

    place_from: Mapped[int] = mapped_column(Integer, default=1)
    place_to: Mapped[int] = mapped_column(Integer, default=1)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    item_code: Mapped[str | None] = mapped_column(String(64))  # код из магазина

    tournament: Mapped[Tournament] = relationship(back_populates="prizes")


class TournamentResult(Base):
    """Снимок итогов. Таблица считается на лету, но после завершения её нужно
    зафиксировать: правила могут поменять, а призёры должны остаться те же."""

    __tablename__ = "tournament_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    clan_id: Mapped[int | None] = mapped_column(Integer, index=True)  # для клановых войн

    place: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0)
    item_awarded: Mapped[str | None] = mapped_column(String(64))
