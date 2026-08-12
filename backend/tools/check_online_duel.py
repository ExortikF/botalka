"""Сквозная проверка живого матча: два игрока, подбор, раунды, рейтинг.

Запускать внутри контейнера бэкенда:
    docker compose exec -T backend python tools/check_online_duel.py
"""

from __future__ import annotations

import asyncio
import json

import httpx
import websockets

API = "http://localhost:8000"
WS = "ws://localhost:8000/ws/duel"


async def login(tg_id: int, name: str) -> str:
    async with httpx.AsyncClient(base_url=API) as client:
        r = await client.post(
            "/api/auth/dev-login", json={"tg_id": tg_id, "display_name": name}
        )
        r.raise_for_status()
        return r.cookies["botalka_session"]


async def answers_for(task_ids: list[int]) -> dict[int, str]:
    from sqlalchemy import select

    from app.core.db import SessionLocal
    from app.models import Task

    async with SessionLocal() as session:
        rows = await session.scalars(select(Task).where(Task.id.in_(task_ids)))
        return {t.id: str((t.answer_payload or {}).get("value", "")) for t in rows}


class Bot:
    """Игрок-скрипт. `smart` — отвечает верно, иначе всегда мимо."""

    def __init__(self, name: str, cookie: str, smart: bool, delay: float):
        self.name, self.cookie, self.smart, self.delay = name, cookie, smart, delay
        self.log: list[dict] = []
        self.final: dict | None = None

    async def run(self) -> None:
        from sqlalchemy import select

        from app.core.db import SessionLocal
        from app.models import Task

        headers = {"Cookie": f"botalka_session={self.cookie}"}
        async with websockets.connect(WS, additional_headers=headers) as ws:
            await ws.send(json.dumps({"type": "queue"}))
            while True:
                message = json.loads(await ws.recv())
                self.log.append(message)
                kind = message["type"]

                if kind == "round":
                    await asyncio.sleep(self.delay)
                    answer = "-999"
                    if self.smart:
                        # ищем задачу по тексту условия — клиент правильного ответа не знает
                        async with SessionLocal() as session:
                            task = await session.scalar(
                                select(Task).where(
                                    Task.statement == message["task"]["statement"]
                                )
                            )
                            if task:
                                answer = str((task.answer_payload or {}).get("value", ""))
                    await ws.send(json.dumps({"type": "answer", "value": answer}))

                elif kind == "match_over":
                    self.final = message
                    return

                elif kind == "error":
                    print(f"  [{self.name}] ошибка: {message['message']}")
                    return


async def main() -> None:
    cookie_a = await login(940001, "Быстрый")
    cookie_b = await login(940002, "Медленный")

    fast = Bot("Быстрый", cookie_a, smart=True, delay=0.2)
    slow = Bot("Медленный", cookie_b, smart=True, delay=1.2)

    print("— оба встают в очередь")
    await asyncio.gather(fast.run(), slow.run())

    for bot in (fast, slow):
        rounds = [m for m in bot.log if m["type"] == "round"]
        results = [m for m in bot.log if m["type"] == "round_result"]
        leaked = any("correct_answer" in m for m in rounds)
        print(f"\n[{bot.name}] раундов получено: {len(rounds)}, результатов: {len(results)}")
        print(f"  правильный ответ приходил вместе с вопросом: {leaked}")
        assert not leaked, "ПРОВАЛ: правильный ответ утёк на клиент до конца раунда"
        assert bot.final, "матч не завершился"
        f = bot.final
        print(f"  итог: {f['result']} {f['score']['you']}:{f['score']['them']} "
              f"| рейтинг {f['rating_delta']:+d} → {f['rating']}")

    assert fast.final["result"] == "win", "оба отвечали верно, победить должен быстрый"
    assert slow.final["result"] == "loss"
    assert fast.final["rating_delta"] > 0 > slow.final["rating_delta"], "рейтинг не сошёлся"
    print("\nОба отвечали верно — победил тот, кто быстрее. Рейтинг пересчитан.")


if __name__ == "__main__":
    asyncio.run(main())
