"""Магазин косметики.

Правило, которое нельзя нарушать: **купленное не влияет на учёбу и рейтинг**.
Как только за монеты можно будет получить подсказку или очки, рейтинг перестанет
что-либо значить, а тренажёр превратится в игру про фарм.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, PlayerUser
from app.core.coins import award
from app.models import CoinReason, ItemKind, ShopItem, User, UserItem

router = APIRouter(prefix="/api/shop", tags=["shop"])

KIND_TITLES = {
    ItemKind.NICK_COLOR: "Цвет ника",
    ItemKind.PREFIX: "Значок перед ником",
    ItemKind.FRAME: "Рамка аватара",
    ItemKind.AVATAR: "Аватарка",
    ItemKind.CARD_BG: "Фон профиля",
    ItemKind.NAME_PLATE: "Декор плиты",
}


class ItemOut(BaseModel):
    code: str
    kind: str
    kind_title: str
    title: str
    value: str
    price: int
    rarity: str
    owned: bool
    equipped: bool


class ShopOut(BaseModel):
    coins: int
    items: list[ItemOut]


class Cosmetics(BaseModel):
    """Что надето — в таком виде это удобно рисовать на клиенте."""

    nick_color: str | None = None
    prefix: str | None = None
    frame: str | None = None
    avatar: str | None = None
    card_bg: str | None = None
    name_plate: str | None = None


async def cosmetics_of(session: DbSession, user_id: int) -> Cosmetics:
    rows = (
        await session.execute(
            select(ShopItem)
            .join(UserItem, UserItem.item_id == ShopItem.id)
            .where(UserItem.user_id == user_id, UserItem.equipped.is_(True))
        )
    ).scalars()

    result = Cosmetics()
    for item in rows:
        if item.kind is ItemKind.NICK_COLOR:
            result.nick_color = item.value
        elif item.kind is ItemKind.PREFIX:
            result.prefix = item.value
        elif item.kind is ItemKind.FRAME:
            result.frame = item.value
        elif item.kind is ItemKind.AVATAR:
            result.avatar = item.value
        elif item.kind is ItemKind.CARD_BG:
            result.card_bg = item.value
        elif item.kind is ItemKind.NAME_PLATE:
            result.name_plate = item.value
    return result


@router.get("", response_model=ShopOut)
async def list_items(session: DbSession, user: PlayerUser) -> ShopOut:
    stmt = select(ShopItem).where(ShopItem.active.is_(True))
    if not user.is_admin:
        # эксклюзив не просто нельзя купить — его не должно быть видно
        stmt = stmt.where(ShopItem.admin_only.is_(False))

    items = list(
        await session.scalars(stmt.order_by(ShopItem.kind, ShopItem.sort_order, ShopItem.price))
    )
    owned = {
        row.item_id: row
        for row in (
            await session.scalars(select(UserItem).where(UserItem.user_id == user.id))
        )
    }

    return ShopOut(
        coins=user.coins,
        items=[
            ItemOut(
                code=item.code,
                kind=item.kind.value,
                kind_title=KIND_TITLES.get(item.kind, item.kind.value),
                title=item.title,
                value=item.value,
                price=item.price,
                rarity=item.rarity.value,
                owned=item.id in owned,
                equipped=bool(owned.get(item.id) and owned[item.id].equipped),
            )
            for item in items
        ],
    )


async def _item(session: DbSession, code: str, user: User) -> ShopItem:
    """Товар по коду. Эксклюзив для обычного пользователя не существует:
    отвечаем 404, а не 403, чтобы по коду ответа нельзя было выяснить каталог."""
    item = await session.scalar(select(ShopItem).where(ShopItem.code == code))
    if item is None or not item.active or (item.admin_only and not user.is_admin):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "товар не найден")
    return item


@router.post("/{code}/buy", response_model=ShopOut)
async def buy(code: str, session: DbSession, user: PlayerUser) -> ShopOut:
    item = await _item(session, code, user)

    already = await session.scalar(
        select(UserItem).where(UserItem.user_id == user.id, UserItem.item_id == item.id)
    )
    if already is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "уже куплено")

    # проверка баланса только на сервере: клиенту здесь верить нельзя
    if user.coins < item.price:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"не хватает монет: нужно {item.price}, у тебя {user.coins}",
        )

    await award(session, user, CoinReason.PURCHASE, amount=-item.price, note=item.code)
    session.add(UserItem(user_id=user.id, item_id=item.id))
    await session.commit()
    await session.refresh(user)
    return await list_items(session, user)


@router.post("/{code}/equip", response_model=ShopOut)
async def equip(code: str, session: DbSession, user: PlayerUser) -> ShopOut:
    """Надеть или снять. В каждом виде косметики надета максимум одна вещь."""
    item = await _item(session, code, user)

    mine = await session.scalar(
        select(UserItem).where(UserItem.user_id == user.id, UserItem.item_id == item.id)
    )
    if mine is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "сначала купи")

    if mine.equipped:
        mine.equipped = False
    else:
        same_kind = (
            await session.execute(
                select(UserItem)
                .join(ShopItem, ShopItem.id == UserItem.item_id)
                .where(
                    UserItem.user_id == user.id,
                    UserItem.equipped.is_(True),
                    ShopItem.kind == item.kind,
                )
            )
        ).scalars()
        for row in same_kind:
            row.equipped = False
        mine.equipped = True

    await session.commit()
    return await list_items(session, user)
