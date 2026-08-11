from __future__ import annotations

from fastapi import Response

from app.core.config import settings
from app.core.security import SESSION_COOKIE, create_session_token


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user_id),
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
