"""Недельная лига.

Соревнование с людьми своего уровня, а не с абстрактным топом: неделя, группа
до 20 человек, в конце верхние поднимаются дивизионом выше, нижние опускаются.
Именно это, а не общий лидерборд, заставляет возвращаться — обогнать соседа
по группе реально, обогнать первого в рейтинге нет.

Очки лиги — решённые задачи за неделю, а не рейтинг: иначе тот, кто много
занимается, но играет мало дуэлей, не увидит от занятий ничего.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DbSession, PlayerUser
from app.api.quiz import STREAK_TZ
from app.api.shop import cosmetics_of
from app.models import Attempt, LeagueMember, User

router = APIRouter(prefix="/api/league", tags=["league"])

DIVISIONS = [
    ("bronze", "Бронза", "#a5713b"),
    ("silver", "Серебро", "#7c8a99"),
    ("gold", "Золото", "#c99a06"),
    ("sapphire", "Сапфир", "#2563eb"),
    ("ruby", "Рубин", "#d6006c"),
]

GROUP_SIZE = 20
PROMOTE = 5  # столько поднимается наверх
RELEGATE = 5  # столько опускается вниз


def week_start(moment: datetime | None = None) -> datetime:
    """Понедельник 00:00 по Москве. Неделя — привычный школьнику отрезок,
    и он же совпадает с тем, как считается «решено за неделю» в лидерборде."""
    now = (moment or datetime.now(UTC)).astimezone(STREAK_TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return (start - timedelta(days=start.weekday())).astimezone(UTC)


def division_at(index: int) -> tuple[str, str, str]:
    return DIVISIONS[max(0, min(index, len(DIVISIONS) - 1))]


async def ensure_member(session: DbSession, user: User) -> LeagueMember:
    """Возвращает запись игрока в лиге текущей недели, создавая при первом заходе.

    Дивизион переносится с прошлой недели — так работает повышение и вылет.
    Группа выбирается самая свободная: людей пока мало, дробить их незачем.
    """
    start = week_start()
    member = await session.scalar(
        select(LeagueMember).where(
            LeagueMember.user_id == user.id, LeagueMember.week_start == start
        )
    )
    if member is not None:
        return member

    previous = await session.scalar(
        select(LeagueMember)
        .where(LeagueMember.user_id == user.id)
        .order_by(LeagueMember.week_start.desc())
    )
    division = previous.division if previous else 0

    peers = list(
        await session.scalars(
            select(LeagueMember).where(
                LeagueMember.week_start == start, LeagueMember.division == division
            )
        )
    )
    groups: dict[int, int] = {}
    for peer in peers:
        groups[peer.group_no] = groups.get(peer.group_no, 0) + 1

    group_no = 0
    while groups.get(group_no, 0) >= GROUP_SIZE:
        group_no += 1

    member = LeagueMember(
        user_id=user.id, week_start=start, division=division, group_no=group_no
    )
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


async def _points(session: DbSession, user_id: int, since: datetime) -> int:
    """Разные верно решённые задачи за неделю. Разные — чтобы одну и ту же
    задачу нельзя было решать по кругу."""
    rows = await session.scalars(
        select(Attempt.task_id).where(
            Attempt.user_id == user_id,
            Attempt.is_correct.is_(True),
            Attempt.created_at >= since,
        )
    )
    return len(set(rows))


class LeagueRow(BaseModel):
    place: int
    user_id: int
    display_name: str
    nick_color: str | None
    prefix: str | None
    avatar: str | None
    frame: str | None
    points: int
    is_you: bool
    zone: str  # promote | stay | relegate


class LeagueOut(BaseModel):
    division: str
    division_title: str
    division_color: str
    next_division: str | None
    promote: int
    relegate: int
    days_left: int
    hours_left: int
    your_place: int
    rows: list[LeagueRow]


@router.get("", response_model=LeagueOut)
async def league(session: DbSession, user: PlayerUser) -> LeagueOut:
    member = await ensure_member(session, user)
    start = member.week_start
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)

    peers = list(
        await session.scalars(
            select(LeagueMember).where(
                LeagueMember.week_start == member.week_start,
                LeagueMember.division == member.division,
                LeagueMember.group_no == member.group_no,
            )
        )
    )

    scored = []
    for peer in peers:
        author = await session.get(User, peer.user_id)
        if author is None:
            continue
        scored.append((await _points(session, peer.user_id, start), author))
    scored.sort(key=lambda pair: (-pair[0], pair[1].id))

    last = len(scored)
    rows = []
    for place, (points, author) in enumerate(scored, 1):
        cos = await cosmetics_of(session, author.id)
        if place <= PROMOTE and member.division < len(DIVISIONS) - 1:
            zone = "promote"
        elif place > last - RELEGATE and member.division > 0 and last > PROMOTE:
            zone = "relegate"
        else:
            zone = "stay"

        rows.append(
            LeagueRow(
                place=place,
                user_id=author.id,
                display_name=author.display_name,
                nick_color=cos.nick_color,
                prefix=cos.prefix,
                avatar=cos.avatar,
                frame=cos.frame,
                points=points,
                is_you=author.id == user.id,
                zone=zone,
            )
        )

    code, title, color = division_at(member.division)
    next_code = (
        division_at(member.division + 1)[1] if member.division < len(DIVISIONS) - 1 else None
    )
    ends = start + timedelta(days=7)
    left = ends - datetime.now(UTC)

    return LeagueOut(
        division=code,
        division_title=title,
        division_color=color,
        next_division=next_code,
        promote=PROMOTE if member.division < len(DIVISIONS) - 1 else 0,
        relegate=RELEGATE if member.division > 0 else 0,
        days_left=max(0, left.days),
        hours_left=max(0, int(left.total_seconds() // 3600) % 24),
        your_place=next((r.place for r in rows if r.is_you), 0),
        rows=rows,
    )
