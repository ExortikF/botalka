"""Вечернее напоминание в Telegram: серия сгорит.

    docker compose exec backend python -m app.cli.remind
    docker compose exec backend python -m app.cli.remind --dry-run

Запускать по расписанию около 19:00 по Москве. Пишем только тем, у кого:

* привязан Telegram (у гостя писать некуда),
* есть серия, которую жалко потерять,
* сегодня ещё ничего не решено.

Последнее условие — главное. Напоминание тому, кто уже позанимался, это не
забота, а спам, от которого отписываются, и второго шанса написать не будет.

Домен для этого не нужен: бот отправляет сообщения исходящим запросом к API
Telegram. Нужен только TELEGRAM_BOT_TOKEN в окружении.
"""

import argparse
import asyncio
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select

from app.api.daily import today
from app.api.quiz import STREAK_TZ
from app.core.config import settings
from app.core.db import SessionLocal
from app.models import Attempt, User

API = "https://api.telegram.org/bot{token}/sendMessage"

# Раз в сутки и только вечером: остальное — дело пользователя, а не бота.
MIN_STREAK = 1


def _text(name: str, streak: int, hours_left: int) -> str:
    first = name.split()[0] if name else "Привет"
    return (
        f"{first}, серия {streak} "
        f"{'день' if streak % 10 == 1 and streak != 11 else 'дня' if 2 <= streak % 10 <= 4 and not 12 <= streak <= 14 else 'дней'} "
        f"сгорит через {hours_left} ч.\n\n"
        "Пять задач — и она останется. Задача дня тоже ждёт."
    )


async def main(dry_run: bool = False) -> None:
    if not settings.telegram_bot_token and not dry_run:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан — отправлять нечем")

    now = datetime.now(STREAK_TZ)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    hours_left = max(1, round((midnight - now).total_seconds() / 3600))
    day_start = datetime.combine(today(), datetime.min.time(), STREAK_TZ)

    async with SessionLocal() as session:
        users = list(
            await session.scalars(
                select(User).where(
                    User.tg_id.is_not(None),
                    User.streak_days >= MIN_STREAK,
                )
            )
        )

        targets = []
        for user in users:
            solved_today = await session.scalar(
                select(Attempt.id)
                .where(Attempt.user_id == user.id, Attempt.created_at >= day_start)
                .limit(1)
            )
            if solved_today is None:
                targets.append(user)

    if dry_run:
        for user in targets:
            print(f"→ {user.display_name} (серия {user.streak_days})")
        print(f"Всего к отправке: {len(targets)}")
        return

    sent = failed = 0
    async with httpx.AsyncClient(timeout=10) as client:
        for user in targets:
            try:
                response = await client.post(
                    API.format(token=settings.telegram_bot_token),
                    json={
                        "chat_id": user.tg_id,
                        "text": _text(user.display_name, user.streak_days, hours_left),
                    },
                )
                # 403 — человек не начинал диалог с ботом или заблокировал его.
                # Это нормальная ситуация, а не сбой: просто пропускаем.
                sent += response.status_code == 200
                failed += response.status_code != 200
            except httpx.HTTPError:
                failed += 1

    print(f"Отправлено: {sent}, не доставлено: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="только показать, кому напишем")
    asyncio.run(main(parser.parse_args().dry_run))
