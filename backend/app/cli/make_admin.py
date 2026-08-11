"""Выдать права администратора.

    docker compose exec backend python -m app.cli.make_admin 123456789
"""

import asyncio
import sys

from sqlalchemy import or_, select

from app.core.db import SessionLocal
from app.models import User


async def main(ident: str) -> int:
    async with SessionLocal() as session:
        try:
            number = int(ident)
        except ValueError:
            user = await session.scalar(select(User).where(User.username == ident.lstrip("@")))
        else:
            user = await session.scalar(
                select(User).where(or_(User.tg_id == number, User.id == number))
            )

        if user is None:
            print(f"Пользователь «{ident}» не найден. Сначала войди на сайте через Telegram.")
            return 1

        user.is_admin = True
        await session.commit()
        print(f"Готово: {user.display_name} (id={user.id}, tg_id={user.tg_id}) теперь администратор")
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(asyncio.run(main(sys.argv[1])))
