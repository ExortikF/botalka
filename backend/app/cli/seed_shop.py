"""Наполняет магазин стартовым каталогом.

    docker compose exec backend python -m app.cli.seed_shop

Идемпотентно: товар ищется по коду, цены и названия обновляются.
Цены подобраны под текущую экономику: обычный квиз без ошибок даёт ~16 монет,
поэтому дешёвая вещь — это пара занятий, легендарная — месяц регулярной работы.
"""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import ItemKind, Rarity, ShopItem

CATALOG = [
    # цвет ника — палитра фиксированная, чтобы ник оставался читаемым
    ("nick_teal", ItemKind.NICK_COLOR, "Бирюзовый", "#0088b0", 0, Rarity.COMMON),
    ("nick_green", ItemKind.NICK_COLOR, "Зелёный", "#1f9d55", 60, Rarity.COMMON),
    ("nick_amber", ItemKind.NICK_COLOR, "Янтарный", "#c98a00", 120, Rarity.RARE),
    ("nick_magenta", ItemKind.NICK_COLOR, "Малиновый", "#d6006c", 200, Rarity.RARE),
    ("nick_violet", ItemKind.NICK_COLOR, "Фиолетовый", "#7c3aed", 350, Rarity.EPIC),
    ("nick_gold", ItemKind.NICK_COLOR, "Золотой", "#b8860b", 800, Rarity.LEGENDARY),

    # значок перед ником
    ("prefix_rocket", ItemKind.PREFIX, "Ракета", "🚀", 80, Rarity.COMMON),
    ("prefix_fire", ItemKind.PREFIX, "Огонь", "🔥", 120, Rarity.COMMON),
    ("prefix_brain", ItemKind.PREFIX, "Мозг", "🧠", 200, Rarity.RARE),
    ("prefix_crown", ItemKind.PREFIX, "Корона", "👑", 500, Rarity.EPIC),
    ("prefix_dragon", ItemKind.PREFIX, "Дракон", "🐉", 900, Rarity.LEGENDARY),

    # рамка аватара
    ("frame_none", ItemKind.FRAME, "Без рамки", "none", 0, Rarity.COMMON),
    ("frame_teal", ItemKind.FRAME, "Бирюзовая", "#0088b0", 70, Rarity.COMMON),
    ("frame_magenta", ItemKind.FRAME, "Малиновая", "#d6006c", 150, Rarity.RARE),
    ("frame_gradient", ItemKind.FRAME, "Градиент", "gradient", 400, Rarity.EPIC),
    ("frame_gold", ItemKind.FRAME, "Золотая", "#b8860b", 900, Rarity.LEGENDARY),

    # аватарка
    ("avatar_letters", ItemKind.AVATAR, "Инициалы", "initials", 0, Rarity.COMMON),
    ("avatar_owl", ItemKind.AVATAR, "Сова", "🦉", 100, Rarity.COMMON),
    ("avatar_cat", ItemKind.AVATAR, "Кот", "🐱", 100, Rarity.COMMON),
    ("avatar_fox", ItemKind.AVATAR, "Лис", "🦊", 180, Rarity.RARE),
    ("avatar_alien", ItemKind.AVATAR, "Пришелец", "👽", 300, Rarity.EPIC),
    ("avatar_unicorn", ItemKind.AVATAR, "Единорог", "🦄", 700, Rarity.LEGENDARY),
]


async def main() -> None:
    async with SessionLocal() as session:
        created = updated = 0
        for order, (code, kind, title, value, price, rarity) in enumerate(CATALOG):
            item = await session.scalar(select(ShopItem).where(ShopItem.code == code))
            if item is None:
                item = ShopItem(code=code)
                session.add(item)
                created += 1
            else:
                updated += 1

            item.kind = kind
            item.title = title
            item.value = value
            item.price = price
            item.rarity = rarity
            item.sort_order = order
            item.active = True

        await session.commit()
        print(f"Готово: {created} создано, {updated} обновлено, всего {len(CATALOG)}")


if __name__ == "__main__":
    asyncio.run(main())
