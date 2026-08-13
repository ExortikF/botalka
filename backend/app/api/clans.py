"""Кланы: создание, вступление, состав и лидерборд.

Очки клана считаются из попыток участников за неделю, а не хранятся счётчиком:
иначе его пришлось бы обновлять из всех мест, где решаются задачи.

Главное правило таблицы — **среднее на активного участника**, а не сумма.
С суммой клан из двадцати человек всегда бьёт клан из трёх, и маленьким
командам нет смысла соревноваться вообще.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, PlayerUser
from app.api.shop import cosmetics_of
from app.models import (
    Attempt,
    Clan,
    ClanMember,
    ClanRequest,
    ClanRole,
    JoinPolicy,
    User,
)

router = APIRouter(prefix="/api/clans", tags=["clans"])

TAG_RE = re.compile(r"^[A-ZА-Я0-9]{2,5}$")
MIN_FOR_BOARD = 3  # клан меньшего размера в таблицу не попадает
LEAVE_COOLDOWN = timedelta(hours=24)

# Названия школьники придумывают всякие; полноценная модерация — в админке,
# здесь только очевидное.
BANNED = ("хуй", "пизд", "ебан", "бляд", "сука", "fuck", "shit", "nazi", "гитлер")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _check_words(*values: str) -> None:
    lowered = " ".join(values).lower()
    if any(word in lowered for word in BANNED):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "в названии есть запрещённое слово — придумай другое",
        )


class MemberOut(BaseModel):
    user_id: int
    display_name: str
    role: str
    nick_color: str | None
    prefix: str | None
    avatar: str | None
    frame: str | None
    solved_week: int
    is_you: bool


class ClanOut(BaseModel):
    id: int
    name: str
    tag: str
    description: str | None
    color: str
    join_policy: str
    max_members: int
    coins: int
    members_count: int
    max_size: int
    points_week: int          # сумма решённых за неделю
    average_week: int         # среднее на активного — по нему считается место
    active_week: int
    your_role: str | None
    can_join: bool
    requested: bool
    members: list[MemberOut]
    requests: list[MemberOut]


class ClanRow(BaseModel):
    place: int
    id: int
    name: str
    tag: str
    color: str
    members_count: int
    average_week: int
    points_week: int
    coins: int
    is_yours: bool


def week_start() -> datetime:
    now = datetime.now(UTC)
    return (now - timedelta(days=7)).replace(microsecond=0)


async def _solved_week(session: DbSession, user_ids: list[int]) -> dict[int, int]:
    """Разные задачи, решённые верно за последние семь дней."""
    if not user_ids:
        return {}

    rows = (
        await session.execute(
            select(Attempt.user_id, Attempt.task_id).where(
                Attempt.user_id.in_(user_ids),
                Attempt.is_correct.is_(True),
                Attempt.created_at >= week_start(),
            )
        )
    ).all()

    seen: dict[int, set[int]] = {}
    for user_id, task_id in rows:
        seen.setdefault(user_id, set()).add(task_id)
    return {user_id: len(tasks) for user_id, tasks in seen.items()}


async def _membership(session: DbSession, user_id: int) -> ClanMember | None:
    return await session.scalar(select(ClanMember).where(ClanMember.user_id == user_id))


async def _load(session: DbSession, clan_id: int) -> Clan:
    # populate_existing: без него после добавления участника возвращается
    # состав из кэша сессии, и свежевступивший не виден в том же ответе.
    clan = await session.scalar(
        select(Clan)
        .where(Clan.id == clan_id)
        .options(selectinload(Clan.members))
        .execution_options(populate_existing=True)
    )
    if clan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "клан не найден")
    return clan


async def _out(session: DbSession, clan: Clan, user: User) -> ClanOut:
    ids = [m.user_id for m in clan.members]
    solved = await _solved_week(session, ids)
    mine = next((m for m in clan.members if m.user_id == user.id), None)

    members: list[MemberOut] = []
    for member in sorted(
        clan.members, key=lambda m: (-solved.get(m.user_id, 0), m.joined_at)
    ):
        author = await session.get(User, member.user_id)
        if author is None:
            continue
        cos = await cosmetics_of(session, author.id)
        members.append(
            MemberOut(
                user_id=author.id,
                display_name=author.display_name,
                role=member.role.value,
                nick_color=cos.nick_color,
                prefix=cos.prefix,
                avatar=cos.avatar,
                frame=cos.frame,
                solved_week=solved.get(author.id, 0),
                is_you=author.id == user.id,
            )
        )

    # Заявки видит только руководство: остальным они ни к чему.
    requests: list[MemberOut] = []
    if mine is not None and mine.role in (ClanRole.LEADER, ClanRole.OFFICER):
        rows = await session.scalars(
            select(ClanRequest).where(
                ClanRequest.clan_id == clan.id, ClanRequest.handled.is_(False)
            )
        )
        for row in rows:
            author = await session.get(User, row.user_id)
            if author is None:
                continue
            cos = await cosmetics_of(session, author.id)
            requests.append(
                MemberOut(
                    user_id=author.id,
                    display_name=author.display_name,
                    role="заявка",
                    nick_color=cos.nick_color,
                    prefix=cos.prefix,
                    avatar=cos.avatar,
                    frame=cos.frame,
                    solved_week=0,
                    is_you=False,
                )
            )

    active = [value for value in solved.values() if value > 0]
    total = sum(solved.values())
    requested = await session.scalar(
        select(ClanRequest.id).where(
            ClanRequest.clan_id == clan.id,
            ClanRequest.user_id == user.id,
            ClanRequest.handled.is_(False),
        )
    )

    return ClanOut(
        id=clan.id,
        name=clan.name,
        tag=clan.tag,
        description=clan.description,
        color=clan.color,
        join_policy=clan.join_policy.value,
        max_members=clan.max_members,
        coins=clan.coins,
        members_count=len(clan.members),
        max_size=clan.max_members,
        points_week=total,
        average_week=round(total / len(active)) if active else 0,
        active_week=len(active),
        your_role=mine.role.value if mine else None,
        can_join=(
            mine is None
            and await _membership(session, user.id) is None
            and len(clan.members) < clan.max_members
            and clan.join_policy is not JoinPolicy.CLOSED
        ),
        requested=requested is not None,
        members=members,
        requests=requests,
    )


@router.get("", response_model=list[ClanRow])
async def leaderboard(session: DbSession, user: PlayerUser) -> list[ClanRow]:
    """Таблица кланов по среднему на активного участника."""
    mine = await _membership(session, user.id)
    clans = list(await session.scalars(select(Clan).options(selectinload(Clan.members))))

    rows = []
    for clan in clans:
        ids = [m.user_id for m in clan.members]
        solved = await _solved_week(session, ids)
        active = [value for value in solved.values() if value > 0]
        total = sum(solved.values())
        rows.append(
            {
                "clan": clan,
                "average": round(total / len(active)) if active else 0,
                "total": total,
                "ranked": len(clan.members) >= MIN_FOR_BOARD,
            }
        )

    # Маленькие кланы показываем в конце: клан из одного человека не должен
    # висеть на первом месте только потому, что этот один много решает.
    rows.sort(key=lambda row: (not row["ranked"], -row["average"], -row["total"]))

    return [
        ClanRow(
            place=i + 1,
            id=row["clan"].id,
            name=row["clan"].name,
            tag=row["clan"].tag,
            color=row["clan"].color,
            members_count=len(row["clan"].members),
            average_week=row["average"],
            points_week=row["total"],
            coins=row["clan"].coins,
            is_yours=mine is not None and mine.clan_id == row["clan"].id,
        )
        for i, row in enumerate(rows)
    ]


@router.get("/my", response_model=ClanOut | None)
async def my_clan(session: DbSession, user: PlayerUser) -> ClanOut | None:
    mine = await _membership(session, user.id)
    if mine is None:
        return None
    return await _out(session, await _load(session, mine.clan_id), user)


@router.get("/{clan_id}", response_model=ClanOut)
async def clan(clan_id: int, session: DbSession, user: PlayerUser) -> ClanOut:
    return await _out(session, await _load(session, clan_id), user)


class ClanIn(BaseModel):
    name: str = Field(min_length=3, max_length=40)
    tag: str = Field(min_length=2, max_length=5)
    description: str | None = Field(default=None, max_length=500)
    color: str = "#0088b0"
    join_policy: JoinPolicy = JoinPolicy.OPEN


@router.post("", response_model=ClanOut, status_code=status.HTTP_201_CREATED)
async def create(payload: ClanIn, session: DbSession, user: PlayerUser) -> ClanOut:
    if await _membership(session, user.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "ты уже в клане")
    if user.is_guest:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "войди через Telegram — гостю клан не создать"
        )

    name = _clean(payload.name)
    tag = _clean(payload.tag).upper()
    _check_words(name, tag, payload.description or "")

    if not TAG_RE.match(tag):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "тег — 2–5 букв или цифр, без пробелов"
        )
    if await session.scalar(select(Clan.id).where(Clan.tag == tag)):
        raise HTTPException(status.HTTP_409_CONFLICT, "такой тег уже занят")
    if await session.scalar(select(Clan.id).where(Clan.name == name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "такое название уже занято")

    clan = Clan(
        name=name,
        tag=tag,
        description=_clean(payload.description or "") or None,
        color=payload.color,
        join_policy=payload.join_policy,
        owner_id=user.id,
    )
    session.add(clan)
    await session.flush()
    session.add(ClanMember(clan_id=clan.id, user_id=user.id, role=ClanRole.LEADER))
    await session.commit()

    return await _out(session, await _load(session, clan.id), user)


@router.post("/{clan_id}/join", response_model=ClanOut)
async def join(clan_id: int, session: DbSession, user: PlayerUser) -> ClanOut:
    if await _membership(session, user.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "ты уже в клане")

    clan = await _load(session, clan_id)
    if len(clan.members) >= clan.max_members:
        raise HTTPException(status.HTTP_409_CONFLICT, "в клане нет мест")

    if clan.join_policy is JoinPolicy.CLOSED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "клан закрыт")

    if clan.join_policy is JoinPolicy.REQUEST:
        exists = await session.scalar(
            select(ClanRequest).where(
                ClanRequest.clan_id == clan.id,
                ClanRequest.user_id == user.id,
                ClanRequest.handled.is_(False),
            )
        )
        if exists is None:
            session.add(ClanRequest(clan_id=clan.id, user_id=user.id))
            await session.commit()
        return await _out(session, await _load(session, clan.id), user)

    session.add(ClanMember(clan_id=clan.id, user_id=user.id))
    await session.commit()
    return await _out(session, await _load(session, clan.id), user)


@router.post("/{clan_id}/requests/{user_id}/{action}", response_model=ClanOut)
async def handle_request(
    clan_id: int, user_id: int, action: str, session: DbSession, user: PlayerUser
) -> ClanOut:
    if action not in ("accept", "decline"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "действие не поддерживается")

    clan = await _load(session, clan_id)
    await _require_officer(session, clan, user)

    request = await session.scalar(
        select(ClanRequest).where(
            ClanRequest.clan_id == clan.id, ClanRequest.user_id == user_id
        )
    )
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "заявки нет")

    request.handled = True
    if action == "accept":
        if len(clan.members) >= clan.max_members:
            raise HTTPException(status.HTTP_409_CONFLICT, "в клане нет мест")
        if await _membership(session, user_id) is None:
            session.add(ClanMember(clan_id=clan.id, user_id=user_id))

    await session.commit()
    return await _out(session, await _load(session, clan.id), user)


async def _require_officer(session: DbSession, clan: Clan, user: User) -> ClanMember:
    mine = next((m for m in clan.members if m.user_id == user.id), None)
    if mine is None or mine.role is ClanRole.MEMBER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "нужны права офицера")
    return mine


@router.post("/leave")
async def leave(session: DbSession, user: PlayerUser) -> dict:
    """Выход из клана.

    Сутки после вступления уйти нельзя: иначе перед подведением итогов недели
    люди прыгали бы в клан-лидер и обратно.
    """
    mine = await _membership(session, user.id)
    if mine is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "ты не в клане")

    if mine.role is ClanRole.LEADER:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "сначала передай руководство другому участнику или распусти клан",
        )

    joined = mine.joined_at.replace(tzinfo=UTC)
    if datetime.now(UTC) - joined < LEAVE_COOLDOWN:
        hours = round((LEAVE_COOLDOWN - (datetime.now(UTC) - joined)).total_seconds() / 3600)
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"выйти можно через {max(1, hours)} ч после вступления"
        )

    await session.delete(mine)
    await session.commit()
    return {"ok": True}


@router.post("/{clan_id}/kick/{user_id}", response_model=ClanOut)
async def kick(
    clan_id: int, user_id: int, session: DbSession, user: PlayerUser
) -> ClanOut:
    clan = await _load(session, clan_id)
    mine = await _require_officer(session, clan, user)

    target = next((m for m in clan.members if m.user_id == user_id), None)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "он не в клане")
    if target.role is ClanRole.LEADER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "главу исключить нельзя")
    if target.role is ClanRole.OFFICER and mine.role is not ClanRole.LEADER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "офицера исключает только глава")

    await session.delete(target)
    await session.commit()
    return await _out(session, await _load(session, clan.id), user)


class RoleIn(BaseModel):
    role: ClanRole


@router.post("/{clan_id}/role/{user_id}", response_model=ClanOut)
async def set_role(
    clan_id: int, user_id: int, payload: RoleIn, session: DbSession, user: PlayerUser
) -> ClanOut:
    """Назначение офицера и передача руководства. Только глава."""
    clan = await _load(session, clan_id)
    mine = next((m for m in clan.members if m.user_id == user.id), None)
    if mine is None or mine.role is not ClanRole.LEADER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "только глава клана")

    target = next((m for m in clan.members if m.user_id == user_id), None)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "он не в клане")

    target.role = payload.role
    if payload.role is ClanRole.LEADER:
        # Глав двое не бывает: передавая руководство, сам становишься офицером.
        mine.role = ClanRole.OFFICER
        clan.owner_id = user_id

    await session.commit()
    return await _out(session, await _load(session, clan.id), user)


@router.delete("/{clan_id}")
async def disband(clan_id: int, session: DbSession, user: PlayerUser) -> dict:
    clan = await _load(session, clan_id)
    mine = next((m for m in clan.members if m.user_id == user.id), None)
    if mine is None or mine.role is not ClanRole.LEADER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "только глава клана")

    await session.delete(clan)
    await session.commit()
    return {"ok": True}
