from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.core.config import settings
from app.core.security import SESSION_COOKIE
from app.core.session import set_session_cookie
from app.core.telegram import TelegramAuthError, verify_init_data, verify_login_widget
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserOut(BaseModel):
    id: int
    is_guest: bool
    is_admin: bool
    username: str | None
    display_name: str
    avatar_url: str | None
    rating: int
    coins: int
    streak_days: int
    cosmetics: dict = {}


class InitDataIn(BaseModel):
    init_data: str


def _display_name(profile: dict) -> str:
    name = f"{profile['first_name']} {profile['last_name']}".strip()
    return name or profile.get("username") or f"Ученик {profile['tg_id'] % 10000}"


async def _login(
    session: DbSession, response: Response, profile: dict, guest: User | None = None
) -> User:
    result = await session.execute(select(User).where(User.tg_id == profile["tg_id"]))
    user = result.scalar_one_or_none()

    if user is None and guest is not None and guest.is_guest:
        # гость решал без регистрации — привязываем аккаунт к нему,
        # иначе весь прогресс до входа потеряется
        user = guest
        user.tg_id = profile["tg_id"]
        user.is_guest = False
        user.display_name = _display_name(profile)

    if user is None:
        user = User(
            tg_id=profile["tg_id"],
            is_guest=False,
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

    set_session_cookie(response, user.id)
    return user


def _require_bot_token() -> str:
    if not settings.telegram_bot_token:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "TELEGRAM_BOT_TOKEN не задан — вход через Telegram выключен",
        )
    return settings.telegram_bot_token


@router.post("/telegram/widget", response_model=UserOut)
async def login_widget(
    payload: dict, session: DbSession, response: Response, guest: OptionalUser
) -> User:
    """Вход с сайта: тело — то, что виджет Telegram Login отдал в колбэк."""
    try:
        profile = verify_login_widget(
            {k: str(v) for k, v in payload.items()}, _require_bot_token()
        )
    except TelegramAuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return await _login(session, response, profile, guest)


@router.post("/telegram/miniapp", response_model=UserOut)
async def login_miniapp(
    payload: InitDataIn, session: DbSession, response: Response, guest: OptionalUser
) -> User:
    """Вход из Telegram Mini App: строка initData."""
    try:
        profile = verify_init_data(payload.init_data, _require_bot_token())
    except TelegramAuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return await _login(session, response, profile, guest)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser, session: DbSession) -> UserOut:
    from app.api.shop import cosmetics_of

    return UserOut(
        id=user.id,
        is_guest=user.is_guest,
        is_admin=user.is_admin,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        rating=user.rating,
        coins=user.coins,
        streak_days=user.streak_days,
        cosmetics=(await cosmetics_of(session, user.id)).model_dump(),
    )


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


class DevLoginIn(BaseModel):
    """Вход без Telegram — только для отладки, см. settings.dev_login."""

    tg_id: int = 900001
    display_name: str = "Тестовый ученик"
    is_admin: bool = False


@router.post("/dev-login", response_model=UserOut)
async def dev_login(
    payload: DevLoginIn, session: DbSession, response: Response, guest: OptionalUser
) -> User:
    """Логинит тестовым пользователем, минуя Telegram.

    Нужен, пока у бота нет домена: виджет Telegram не работает с localhost.
    Выключен по умолчанию и включается только переменной DEV_LOGIN=true.
    """
    if not settings.dev_login:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "не найдено")

    user = await _login(
        session,
        response,
        {
            "tg_id": payload.tg_id,
            "username": f"dev{payload.tg_id}",
            "first_name": payload.display_name,
            "last_name": "",
            "photo_url": None,
        },
        guest,
    )
    # Флаг выставляется по запросу, а не «только вверх». Раньше здесь стояло
    # `if payload.is_admin and not user.is_admin`, и снять права было нечем:
    # один заход админом по tg_id ученика — и «Войти учеником» навсегда
    # отдавал аккаунт с админкой и эксклюзивом в магазине.
    if user.is_admin != payload.is_admin:
        user.is_admin = payload.is_admin
        await session.commit()
        await session.refresh(user)
    return user
