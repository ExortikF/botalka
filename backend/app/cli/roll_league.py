"""Закрывает прошедшую неделю лиги: кто поднялся, кто вылетел.

    docker compose exec backend python -m app.cli.roll_league

Запускать раз в неделю (в понедельник утром). Идемпотентно: записи новой недели
создаются один раз, повторный запуск ничего не меняет.

Отдельной командой, а не фоновой задачей внутри приложения, намеренно: пока
процесс один, планировщик внутри него — лишняя точка отказа, а результат должен
быть виден и проверяем глазами.
"""

import asyncio
from datetime import timedelta

from sqlalchemy import select

from app.api.league import DIVISIONS, PROMOTE, RELEGATE, _points, week_start
from app.core.db import SessionLocal
from app.models import LeagueMember


async def main() -> None:
    async with SessionLocal() as session:
        current = week_start()
        previous = current - timedelta(days=7)

        members = list(
            await session.scalars(
                select(LeagueMember).where(LeagueMember.week_start == previous)
            )
        )
        if not members:
            print("За прошлую неделю участников нет — нечего закрывать")
            return

        groups: dict[tuple[int, int], list[LeagueMember]] = {}
        for member in members:
            groups.setdefault((member.division, member.group_no), []).append(member)

        moved_up = moved_down = stayed = 0
        for (division, _), group in groups.items():
            scored = [(await _points(session, m.user_id, previous), m) for m in group]
            scored.sort(key=lambda pair: (-pair[0], pair[1].user_id))

            for place, (points, member) in enumerate(scored, 1):
                new_division = division
                if place <= PROMOTE and division < len(DIVISIONS) - 1:
                    new_division = division + 1
                    moved_up += 1
                elif (
                    place > len(scored) - RELEGATE
                    and division > 0
                    and len(scored) > PROMOTE
                    # ноль очков — это не «слабее всех», а «не заходил»:
                    # выкидывать за неучастие в самый низ незачем
                    and points > 0
                ):
                    new_division = division - 1
                    moved_down += 1
                else:
                    stayed += 1

                exists = await session.scalar(
                    select(LeagueMember).where(
                        LeagueMember.user_id == member.user_id,
                        LeagueMember.week_start == current,
                    )
                )
                if exists is None:
                    session.add(
                        LeagueMember(
                            user_id=member.user_id,
                            week_start=current,
                            division=new_division,
                            group_no=0,
                        )
                    )

        await session.commit()
        print(f"Готово: {moved_up} поднялись, {moved_down} опустились, {stayed} остались")


if __name__ == "__main__":
    asyncio.run(main())
