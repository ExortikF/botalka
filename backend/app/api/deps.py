from __future__ import annotations

import random
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import SESSION_COOKIE, read_session_token
from app.core.session import set_session_cookie
from app.models import User

DbSession = Annotated[AsyncSession, Depends(get_session)]
SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]

GUEST_NAMES = ["Аноним", "Ботаник", "Абитуриент", "Стобалльник", "Новичок"]


async def _user_from_cookie(session: AsyncSession, token: str | None) -> User | None:
    user_id = read_session_token(token) if token else None
    if user_id is None:
        return None
    return await session.get(User, user_id)


async def get_current_user(
    session: DbSession,
    botalka_session: SessionCookie = None,
) -> User:
    user = await _user_from_cookie(session, botalka_session)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "не авторизован")
    return user


async def get_optional_user(
    session: DbSession,
    botalka_session: SessionCookie = None,
) -> User | None:
    return await _user_from_cookie(session, botalka_session)


async def get_or_create_user(
    session: DbSession,
    response: Response,
    botalka_session: SessionCookie = None,
) -> User:
    """Решать можно без регистрации: если сессии нет — заводим гостя.

    Прогресс копится сразу, а вход через Telegram потом привязывается к тому же
    пользователю (см. api/auth.py). Так онбординг не упирается в форму входа.
    """
    user = await _user_from_cookie(session, botalka_session)
    if user is not None:
        return user

    user = User(display_name=f"{random.choice(GUEST_NAMES)} {random.randint(100, 999)}")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    set_session_cookie(response, user.id)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
PlayerUser = Annotated[User, Depends(get_or_create_user)]
