"""Друзья: код для добавления, заявки, список.

Добавление идёт по короткому коду, а не по нику: у гостей ника нет, а ссылку с кодом
можно просто скинуть в чат. Поиска по всем пользователям намеренно нет — иначе любой
сможет перебирать чужие профили.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.api.deps import DbSession, PlayerUser
from app.api.shop import cosmetics_of
from app.models import Attempt, Friendship, FriendshipState, User

router = APIRouter(prefix="/api/friends", tags=["friends"])

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


async def ensure_code(session: DbSession, user: User) -> str:
    """Код выдаётся при первом обращении, а не всем подряд заранее."""
    if user.friend_code:
        return user.friend_code
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if not await session.scalar(select(User.id).where(User.friend_code == code)):
            user.friend_code = code
            await session.commit()
            return code
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "не удалось выдать код")


class FriendOut(BaseModel):
    id: int
    display_name: str
    streak_days: int
    solved: int
    friendship_id: int
    cosmetics: dict = {}


class RequestOut(BaseModel):
    friendship_id: int
    user_id: int
    display_name: str
    direction: str  # incoming | outgoing


class FriendsPageOut(BaseModel):
    my_code: str
    friends: list[FriendOut]
    requests: list[RequestOut]


async def _solved(session: DbSession, user_id: int) -> int:
    return (
        await session.scalar(
            select(func.count(func.distinct(Attempt.task_id))).where(
                Attempt.user_id == user_id, Attempt.is_correct.is_(True)
            )
        )
    ) or 0


@router.get("", response_model=FriendsPageOut)
async def my_friends(session: DbSession, user: PlayerUser) -> FriendsPageOut:
    code = await ensure_code(session, user)

    rows = list(
        await session.scalars(
            select(Friendship).where(
                or_(Friendship.from_user_id == user.id, Friendship.to_user_id == user.id)
            )
        )
    )

    friends: list[FriendOut] = []
    requests: list[RequestOut] = []

    for row in rows:
        other_id = row.to_user_id if row.from_user_id == user.id else row.from_user_id
        other = await session.get(User, other_id)
        if other is None:
            continue

        if row.state is FriendshipState.ACCEPTED:
            friends.append(
                FriendOut(
                    id=other.id,
                    display_name=other.display_name,
                    streak_days=other.streak_days,
                    solved=await _solved(session, other.id),
                    friendship_id=row.id,
                    cosmetics=(await cosmetics_of(session, other.id)).model_dump(),
                )
            )
        else:
            requests.append(
                RequestOut(
                    friendship_id=row.id,
                    user_id=other.id,
                    display_name=other.display_name,
                    direction="outgoing" if row.from_user_id == user.id else "incoming",
                )
            )

    friends.sort(key=lambda f: -f.solved)
    return FriendsPageOut(my_code=code, friends=friends, requests=requests)


class AddFriendIn(BaseModel):
    code: str


@router.post("/request", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
async def add_friend(payload: AddFriendIn, session: DbSession, user: PlayerUser) -> RequestOut:
    await ensure_code(session, user)
    code = payload.code.strip().upper()

    target = await session.scalar(select(User).where(User.friend_code == code))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "код не найден")
    if target.id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "это твой собственный код")

    existing = await session.scalar(
        select(Friendship).where(
            or_(
                (Friendship.from_user_id == user.id) & (Friendship.to_user_id == target.id),
                (Friendship.from_user_id == target.id) & (Friendship.to_user_id == user.id),
            )
        )
    )
    if existing is not None:
        if existing.state is FriendshipState.ACCEPTED:
            raise HTTPException(status.HTTP_409_CONFLICT, "вы уже друзья")
        # встречная заявка — сразу принимаем, ждать второго подтверждения незачем
        if existing.from_user_id == target.id:
            existing.state = FriendshipState.ACCEPTED
            existing.accepted_at = datetime.now(UTC)
            await session.commit()
            return RequestOut(
                friendship_id=existing.id,
                user_id=target.id,
                display_name=target.display_name,
                direction="incoming",
            )
        raise HTTPException(status.HTTP_409_CONFLICT, "заявка уже отправлена")

    friendship = Friendship(from_user_id=user.id, to_user_id=target.id)
    session.add(friendship)
    await session.commit()
    await session.refresh(friendship)

    return RequestOut(
        friendship_id=friendship.id,
        user_id=target.id,
        display_name=target.display_name,
        direction="outgoing",
    )


async def _load_own(session: DbSession, friendship_id: int, user: User) -> Friendship:
    friendship = await session.get(Friendship, friendship_id)
    if friendship is None or user.id not in (friendship.from_user_id, friendship.to_user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "заявка не найдена")
    return friendship


@router.post("/{friendship_id}/accept")
async def accept(friendship_id: int, session: DbSession, user: PlayerUser) -> dict:
    friendship = await _load_own(session, friendship_id, user)
    if friendship.to_user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "принять может только получатель заявки")

    friendship.state = FriendshipState.ACCEPTED
    friendship.accepted_at = datetime.now(UTC)
    await session.commit()
    return {"ok": True}


@router.delete("/{friendship_id}")
async def remove(friendship_id: int, session: DbSession, user: PlayerUser) -> dict:
    """Отклонить заявку или удалить из друзей — действие одно и то же."""
    friendship = await _load_own(session, friendship_id, user)
    await session.delete(friendship)
    await session.commit()
    return {"ok": True}
