from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ClanRole(str, enum.Enum):
    LEADER = "leader"
    OFFICER = "officer"
    MEMBER = "member"


class JoinPolicy(str, enum.Enum):
    OPEN = "open"        # вступают сразу
    REQUEST = "request"  # по заявке
    CLOSED = "closed"    # только по приглашению главы


class Clan(Base):
    """Команда игроков.

    Тег показывается рядом с ником — это главное, ради чего в клан вступают,
    поэтому он короткий, уникальный и в верхнем регистре.
    """

    __tablename__ = "clans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    tag: Mapped[str] = mapped_column(String(5), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(16), default="#0088b0")

    join_policy: Mapped[JoinPolicy] = mapped_column(
        Enum(JoinPolicy, native_enum=False), default=JoinPolicy.OPEN
    )
    max_members: Mapped[int] = mapped_column(Integer, default=20)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    members: Mapped[list[ClanMember]] = relationship(
        back_populates="clan", cascade="all, delete-orphan"
    )


class ClanMember(Base):
    """Участие в клане. Одно на человека — иначе принадлежность ничего не значит."""

    __tablename__ = "clan_members"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    clan_id: Mapped[int] = mapped_column(
        ForeignKey("clans.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    role: Mapped[ClanRole] = mapped_column(
        Enum(ClanRole, native_enum=False), default=ClanRole.MEMBER
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    clan: Mapped[Clan] = relationship(back_populates="members")


class ClanRequest(Base):
    """Заявка на вступление в клан с политикой «по заявке»."""

    __tablename__ = "clan_requests"
    __table_args__ = (UniqueConstraint("clan_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    clan_id: Mapped[int] = mapped_column(
        ForeignKey("clans.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    handled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
