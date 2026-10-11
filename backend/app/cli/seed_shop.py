"""Наполняет магазин каталогом.

    docker compose exec backend python -m app.cli.seed_shop

Идемпотентно: товар ищется по коду, всё остальное перезаписывается. Товары,
которых больше нет в каталоге, деактивируются — купленное у людей не пропадает,
просто исчезает с витрины.

**Формат `value`** — его разбирает фронт (web/lib/cosmetics.ts):

  ник:    `#hex` · `gradient:#a,#b` · `rainbow` · `glow:#hex` · `shine:#hex`
  рамка:  `none` · `solid:#hex` · `gradient:#a,#b` · `rotate:#a,#b` · `pulse:#hex`
  фон:    `#hex` · `gradient:#a,#b` · `aurora:#a,#b,#c`
  аватар: `initials` · эмодзи

Экономика и обоснование цен — docs/GAMIFICATION.md.
"""

import asyncio

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import ItemKind, Rarity, ShopItem

C, R, E, L = Rarity.COMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY

CATALOG = [
    # ------------------------------------------------------------ цвет ника
    # палитра разведена по тону: рядом не должно быть двух похожих
    ("nick_slate", ItemKind.NICK_COLOR, "Графит", "#42505e", 0, C),
    ("nick_teal", ItemKind.NICK_COLOR, "Бирюзовый", "#0088b0", 40, C),
    ("nick_green", ItemKind.NICK_COLOR, "Изумруд", "#1f9d55", 60, C),
    ("nick_orange", ItemKind.NICK_COLOR, "Мандарин", "#e8590c", 90, C),
    ("nick_magenta", ItemKind.NICK_COLOR, "Малина", "#d6006c", 140, R),
    ("nick_violet", ItemKind.NICK_COLOR, "Фиалка", "#7c3aed", 180, R),
    ("nick_sky", ItemKind.NICK_COLOR, "Небо", "#2563eb", 180, R),
    # дальше — эффекты, а не просто цвет
    ("nick_sunset", ItemKind.NICK_COLOR, "Закат", "gradient:#ff8a00,#d6006c", 450, E),
    ("nick_ocean", ItemKind.NICK_COLOR, "Океан", "gradient:#0088b0,#7c3aed", 450, E),
    ("nick_glow", ItemKind.NICK_COLOR, "Неон", "glow:#00d5ff", 700, E),
    ("nick_gold", ItemKind.NICK_COLOR, "Золото", "shine:#b8860b", 1200, L),
    ("nick_rainbow", ItemKind.NICK_COLOR, "Радуга", "rainbow", 1800, L),

    # ------------------------------------------------------------ значок
    ("prefix_star", ItemKind.PREFIX, "Звезда", "⭐", 50, C),
    ("prefix_rocket", ItemKind.PREFIX, "Ракета", "🚀", 80, C),
    ("prefix_fire", ItemKind.PREFIX, "Огонь", "🔥", 110, C),
    ("prefix_brain", ItemKind.PREFIX, "Мозг", "🧠", 200, R),
    ("prefix_owl", ItemKind.PREFIX, "Сова", "🦉", 220, R),
    ("prefix_lightning", ItemKind.PREFIX, "Молния", "⚡", 260, R),
    ("prefix_crown", ItemKind.PREFIX, "Корона", "👑", 600, E),
    ("prefix_diamond", ItemKind.PREFIX, "Алмаз", "💎", 800, E),
    ("prefix_dragon", ItemKind.PREFIX, "Дракон", "🐉", 1500, L),

    # ------------------------------------------------------------ рамка
    ("frame_none", ItemKind.FRAME, "Без рамки", "none", 0, C),
    ("frame_teal", ItemKind.FRAME, "Бирюзовая", "solid:#0088b0", 50, C),
    ("frame_green", ItemKind.FRAME, "Изумрудная", "solid:#1f9d55", 70, C),
    ("frame_magenta", ItemKind.FRAME, "Малиновая", "solid:#d6006c", 150, R),
    ("frame_sunset", ItemKind.FRAME, "Закат", "gradient:#ff8a00,#d6006c", 400, E),
    ("frame_pulse", ItemKind.FRAME, "Пульс", "pulse:#00d5ff", 750, E),
    ("frame_aurora", ItemKind.FRAME, "Сияние", "rotate:#7c3aed,#00d5ff", 1400, L),
    ("frame_gold", ItemKind.FRAME, "Золотая", "rotate:#b8860b,#ffe08a", 2000, L),

    # ------------------------------------------------------------ фон профиля
    ("bg_none", ItemKind.CARD_BG, "Обычный", "none", 0, C),
    ("bg_mint", ItemKind.CARD_BG, "Мята", "#e8f6ee", 80, C),
    ("bg_sand", ItemKind.CARD_BG, "Песок", "#fdf3dd", 80, C),
    ("bg_dusk", ItemKind.CARD_BG, "Сумерки", "gradient:#e9f8ff,#efe3ff", 300, R),
    ("bg_sunset", ItemKind.CARD_BG, "Закат", "gradient:#ffe9d6,#ffd9e8", 300, R),
    ("bg_space", ItemKind.CARD_BG, "Космос", "gradient:#1b1f3b,#3b1f5e", 900, E),
    ("bg_aurora", ItemKind.CARD_BG, "Северное сияние", "aurora:#0f2027,#203a43,#2c5364", 1600, L),

    # ------------------------------------------------------------ аватарка
    # Не эмодзи: монограмма на подложке. Смотрится как часть интерфейса,
    # а не как вставленный смайлик, и одинаково выглядит на всех системах.
    ("avatar_letters", ItemKind.AVATAR, "Обычная", "mono:#e9f8ff,#0088b0", 0, C),
    ("avatar_mint", ItemKind.AVATAR, "Мята", "mono:#e8f6ee,#1f9d55", 60, C),
    ("avatar_sand", ItemKind.AVATAR, "Песок", "mono:#fdf3dd,#7a5f00", 60, C),
    ("avatar_rose", ItemKind.AVATAR, "Роза", "mono:#ffe9f0,#d6006c", 90, C),
    ("avatar_sky", ItemKind.AVATAR, "Небо", "grad:#60a5fa,#2563eb", 200, R),
    ("avatar_sunset", ItemKind.AVATAR, "Закат", "grad:#ff8a00,#d6006c", 260, R),
    ("avatar_forest", ItemKind.AVATAR, "Хвоя", "grad:#34d399,#065f46", 260, R),
    ("avatar_violet", ItemKind.AVATAR, "Аметист", "grad:#a78bfa,#5b21b6", 500, E),
    ("avatar_ember", ItemKind.AVATAR, "Уголь", "grad:#f97316,#7c2d12", 500, E),
    ("avatar_holo", ItemKind.AVATAR, "Голограмма", "holo", 1200, L),
    ("avatar_gold", ItemKind.AVATAR, "Золотая", "shineav:#b8860b,#ffe08a", 1400, L),

    # --------------------------------------------------- плита с ником (декор)
    ("plate_none", ItemKind.NAME_PLATE, "Без декора", "none", 0, C),
    ("plate_line", ItemKind.NAME_PLATE, "Полоска", "bar:#0088b0", 120, C),
    ("plate_corner", ItemKind.NAME_PLATE, "Уголки", "corner:#7c3aed", 250, R),
    ("plate_grid", ItemKind.NAME_PLATE, "Тетрадь в клетку", "grid:#0088b0", 500, E),
    ("plate_neon", ItemKind.NAME_PLATE, "Неон", "neon:#00d5ff", 900, E),
    ("plate_stars", ItemKind.NAME_PLATE, "Звёздная пыль", "stars:#7c3aed", 1700, L),
]

# Эксклюзив: обычному пользователю этих товаров не видно вообще.
ADMIN_ONLY = [
    ("nick_admin", ItemKind.NICK_COLOR, "Код Боталки", "matrix", 0),
    ("frame_admin", ItemKind.FRAME, "Ядро", "rotate:#00ffa3,#00d5ff", 0),
    ("avatar_admin", ItemKind.AVATAR, "Админ", "admin", 0),
    ("prefix_admin", ItemKind.PREFIX, "Молот", "🛠", 0),
    ("plate_admin", ItemKind.NAME_PLATE, "Панель управления", "matrixplate", 0),
    ("bg_admin", ItemKind.CARD_BG, "Терминал", "gradient:#05130d,#0b3d2e", 0),
]


async def main() -> None:
    async with SessionLocal() as session:
        catalog = [(*row, False) for row in CATALOG] + [
            (code, kind, title, value, price, Rarity.MYTHIC, True)
            for code, kind, title, value, price in ADMIN_ONLY
        ]
        codes = {row[0] for row in catalog}
        created = updated = retired = 0

        for order, (code, kind, title, value, price, rarity, admin_only) in enumerate(catalog):
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
            item.admin_only = admin_only

        # то, что убрали из каталога, прячем с витрины, но не удаляем:
        # у кого-то это уже куплено и надето
        for item in await session.scalars(select(ShopItem).where(ShopItem.active.is_(True))):
            if item.code not in codes:
                item.active = False
                retired += 1

        await session.commit()
        print(
            f"Готово: {created} создано, {updated} обновлено, "
            f"{retired} снято с витрины. Всего в каталоге {len(catalog)}"
        )


if __name__ == "__main__":
    asyncio.run(main())
