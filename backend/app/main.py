from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import (
    admin,
    auth,
    catalog,
    clan_wars,
    clans,
    daily,
    duel_ws,
    duels,
    friends,
    mocks,
    profile,
    quiz,
    shop,
    suggestions,
    tournaments,
)
from app.core.config import settings
from app.core.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.dev_login:
        print(
            "\n"
            "  ВНИМАНИЕ: включён DEV_LOGIN — вход без Telegram доступен всем,\n"
            "  кто откроет сайт. Выключи его перед публикацией.\n"
        )
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    yield

    await duel_ws.shutdown_matches()
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="Botalka API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,  # сессия в httpOnly-куке, без этого не долетит
    allow_methods=["*"],
    allow_headers=["*"],
)

# Картинки к задачам (чертежи, графики) лежат рядом с их YAML в /content и
# монтируются в контейнер только на чтение. В проде эту же папку раздаёт nginx —
# здесь отдаём сами, чтобы всё работало из одного docker compose up.
CONTENT_DIR = Path("/content")
if CONTENT_DIR.is_dir():
    app.mount("/content", StaticFiles(directory=CONTENT_DIR), name="content")

app.include_router(auth.router)
app.include_router(quiz.router)
app.include_router(catalog.router)
app.include_router(clan_wars.router)
app.include_router(clans.router)
app.include_router(daily.router)
app.include_router(profile.router)
app.include_router(admin.router)
app.include_router(duels.router)
app.include_router(friends.router)
app.include_router(duel_ws.router)
app.include_router(mocks.router)
app.include_router(shop.router)
app.include_router(suggestions.router)
app.include_router(tournaments.router)


@app.get("/health")
async def health() -> dict:
    checks: dict[str, str] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("select 1"))
        checks["db"] = "ok"
    except Exception as exc:  # noqa: BLE001 — health-check не должен падать
        checks["db"] = f"error: {exc.__class__.__name__}"

    try:
        await app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc.__class__.__name__}"

    checks["status"] = "ok" if all(v == "ok" for k, v in checks.items()) else "degraded"
    return checks
