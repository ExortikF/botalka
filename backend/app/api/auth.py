from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import SESSION_COOKIE, create_session_token
from app.core.telegram import TelegramAuthError, verify_init_data, verify_login_widget
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserOut(BaseModel):
    id: int
    username: str | None
    display_name: str
    avatar_url: str | None
    rating: int
    streak_days: int


class InitDataIn(BaseModel):
    init_data: str


def _display_name(profile: dict) -> str:
    name = f"{profile['first_name']} {profile['last_name']}".strip()
    return name or profile.get("username") or f"Ученик {profile['tg_id'] % 10000}"


async def _login(session: DbSession, response: Response, profile: dict) -> User:
    result = await session.execute(select(User).where(User.tg_id == profile["tg_id"]))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            tg_id=profile["tg_id"],
            username=profile["username"],
            display_name=_display_name(profile),
            avatar_url=profile["photo_url"],
        )
        session.add(user)
    else:
        # профиль в Telegram мог поменяться — подтягиваем актуальный
        user.username = profile["username"]
        user.avatar_url = profile["photo_url"]
        user.last_seen_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(user)

    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id),
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=not settings.cors_origins.startswith("http://localhost"),
    )
    return user


def _require_bot_token() -> str:
    if not settings.telegram_bot_token:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "TELEGRAM_BOT_TOKEN не задан — вход через Telegram выключен",
        )
    return settings.telegram_bot_token


@router.post("/telegram/widget", response_model=UserOut)
async def login_widget(payload: dict, session: DbSession, response: Response) -> User:
    """Вход с сайта: тело — то, что виджет Telegram Login отдал в колбэк."""
    try:
        profile = verify_login_widget(
            {k: str(v) for k, v in payload.items()}, _require_bot_token()
        )
    except TelegramAuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return await _login(session, response, profile)


@router.post("/telegram/miniapp", response_model=UserOut)
async def login_miniapp(payload: InitDataIn, session: DbSession, response: Response) -> User:
    """Вход из Telegram Mini App: строка initData."""
    try:
        profile = verify_init_data(payload.init_data, _require_bot_token())
    except TelegramAuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return await _login(session, response, profile)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}
