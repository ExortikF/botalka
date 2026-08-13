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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ItemKind(str, enum.Enum):
    NICK_COLOR = "nick_color"   # подсветка ника
    PREFIX = "prefix"           # значок-приставка перед ником
    FRAME = "frame"             # рамка вокруг аватарки
    AVATAR = "avatar"           # сама аватарка
    CARD_BG = "card_bg"         # фон карточки профиля
    NAME_PLATE = "name_plate"   # декор плиты с ником


class Rarity(str, enum.Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"     # только для админов, за монеты не купить


class ShopItem(Base):
    """Товар магазина. Только косметика — на учёбу и рейтинг не влияет никогда."""

    __tablename__ = "shop_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    kind: Mapped[ItemKind] = mapped_column(Enum(ItemKind, native_enum=False), index=True)
    title: Mapped[str] = mapped_column(String(80))
    # что именно применяем: hex-цвет, эмодзи, код рамки
    value: Mapped[str] = mapped_column(String(64))
    price: Mapped[int] = mapped_column(Integer, default=0)
    rarity: Mapped[Rarity] = mapped_column(Enum(Rarity, native_enum=False), default=Rarity.COMMON)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # эксклюзив: в витрине обычных пользователей такого товара нет вообще
    admin_only: Mapped[bool] = mapped_column(Boolean, default=False)


class UserItem(Base):
    __tablename__ = "user_items"
    __table_args__ = (UniqueConstraint("user_id", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("shop_items.id"), index=True)
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)
    bought_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
