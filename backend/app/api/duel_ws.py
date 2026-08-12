"""Живой матч 1×1 на WebSocket.

Правила: 7 раундов, вопрос приходит обоим одновременно. Очко забирает тот, кто ответил
верно и раньше соперника. Если верно ответили оба — очко у более быстрого. Ничья по
очкам решается суммарным временем.

**Что здесь важно и легко сломать:**

* Правильный ответ не уходит на клиент до конца раунда — иначе матч бессмысленен.
* Время считает сервер. Клиентский таймер только рисует, на результат не влияет.
* Состояние матча живёт в памяти процесса. Это осознанное упрощение: соединения
  всё равно привязаны к процессу, а бэкенд у нас однопроцессный. При переходе на
  несколько воркеров понадобится Redis pub/sub — см. docs/ARCHITECTURE.md.
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select

from app.core.answers import check_answer
from app.core.db import SessionLocal
from app.core.security import SESSION_COOKIE, read_session_token
from app.models import Duel, DuelKind, DuelState, Task, TaskStatus, TaskType, User

router = APIRouter()

ROUNDS = 7
ROUND_SECONDS = 45

# Баланс рейтинга. Подробности и обоснование — docs/RATING.md
START_RATING = 1000
RATING_FLOOR = 100          # ниже не падаем: бесконечное дно демотивирует
PROVISIONAL_MATCHES = 5     # первые матчи двигают рейтинг сильнее, чтобы быстрее найти свой уровень
K_PROVISIONAL = 40
K_NORMAL = 24
K_TOP = 16                  # наверху шаг мельче, иначе рейтинг скачет от одной случайности
TOP_THRESHOLD = 1600


@dataclass
class Player:
    user_id: int
    name: str
    rating: int
    ws: WebSocket
    score: int = 0
    total_time_ms: int = 0
    answer: str | None = None
    answered_at: float | None = None

    async def send(self, payload: dict) -> None:
        try:
            await self.ws.send_json(payload)
        except Exception:  # noqa: BLE001 — соперник мог отвалиться, матч продолжаем
            pass


@dataclass
class Match:
    code: str
    tasks: list[dict]
    a: Player
    b: Player
    round_index: int = 0
    round_started: float = 0.0
    timer: asyncio.Task | None = None
    finished: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def other(self, player: Player) -> Player:
        return self.b if player is self.a else self.a


# очередь ожидания и активные матчи — оба в памяти процесса
_queue: list[Player] = []
_matches: dict[int, Match] = {}  # user_id → матч
_queue_lock = asyncio.Lock()


async def _authenticate(ws: WebSocket) -> User | None:
    token = ws.cookies.get(SESSION_COOKIE)
    user_id = read_session_token(token) if token else None
    if user_id is None:
        return None
    async with SessionLocal() as session:
        return await session.get(User, user_id)


async def _pick_tasks(count: int) -> list[dict]:
    async with SessionLocal() as session:
        tasks = list(
            await session.scalars(
                select(Task)
                .join(TaskType, TaskType.id == Task.task_type_id)
                .where(Task.status == TaskStatus.LIVE)
                .order_by(func.random())
                .limit(count)
            )
        )
        out = []
        for task in tasks:
            await session.refresh(task, ["task_type"])
            out.append(
                {
                    "id": task.id,
                    "statement": task.statement,
                    "number": task.task_type.number,
                    "title": task.task_type.title,
                    "answer_type": task.answer_type,
                    "answer_payload": task.answer_payload,
                    "correct": str((task.answer_payload or {}).get("value", "")),
                }
            )
        return out


def _k_factor(rating: int, matches_played: int) -> int:
    if matches_played < PROVISIONAL_MATCHES:
        return K_PROVISIONAL
    return K_TOP if rating >= TOP_THRESHOLD else K_NORMAL


def _elo(rating_a: int, rating_b: int, score_a: float, k: int) -> int:
    """На сколько изменится рейтинг игрока A. score_a: 1 победа, 0.5 ничья, 0 поражение."""
    expected = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    return round(k * (score_a - expected))


async def _online_matches(session, user_id: int) -> int:
    return (
        await session.scalar(
            select(func.count(Duel.id)).where(
                Duel.kind == DuelKind.ONLINE,
                (Duel.challenger_id == user_id) | (Duel.opponent_id == user_id),
            )
        )
    ) or 0


async def _start_match(a: Player, b: Player) -> None:
    tasks = await _pick_tasks(ROUNDS)
    if len(tasks) < 3:
        for player in (a, b):
            await player.send({"type": "error", "message": "в банке мало задач для матча"})
        return

    code = "".join(secrets.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(7))
    match = Match(code=code, tasks=tasks, a=a, b=b)
    _matches[a.user_id] = match
    _matches[b.user_id] = match

    for player in (a, b):
        opponent = match.other(player)
        await player.send(
            {
                "type": "match_found",
                "code": code,
                "rounds": len(tasks),
                "opponent": {"name": opponent.name, "rating": opponent.rating},
            }
        )

    await asyncio.sleep(1.5)  # пауза, чтобы игрок успел прочитать, с кем играет
    await _send_round(match)


async def _send_round(match: Match) -> None:
    task = match.tasks[match.round_index]
    match.round_started = asyncio.get_event_loop().time()
    match.a.answer = match.b.answer = None
    match.a.answered_at = match.b.answered_at = None

    for player in (match.a, match.b):
        await player.send(
            {
                "type": "round",
                "index": match.round_index + 1,
                "total": len(match.tasks),
                "seconds": ROUND_SECONDS,
                "task": {
                    "statement": task["statement"],
                    "number": task["number"],
                    "title": task["title"],
                },
                "score": {"you": player.score, "them": match.other(player).score},
            }
        )

    if match.timer:
        match.timer.cancel()
    match.timer = asyncio.create_task(_round_timeout(match, match.round_index))


async def _round_timeout(match: Match, index: int) -> None:
    await asyncio.sleep(ROUND_SECONDS)
    async with match.lock:
        if match.finished or match.round_index != index:
            return
        await _finish_round(match)


async def _finish_round(match: Match) -> None:
    """Считает очко раунда. Вызывается под match.lock."""
    if match.timer:
        match.timer.cancel()
        match.timer = None

    task = match.tasks[match.round_index]
    results = {}
    for player in (match.a, match.b):
        correct = bool(
            player.answer is not None
            and check_answer(task["answer_type"], task["answer_payload"], player.answer)
        )
        spent = (
            int((player.answered_at - match.round_started) * 1000)
            if player.answered_at
            else ROUND_SECONDS * 1000
        )
        player.total_time_ms += spent
        results[player.user_id] = {"correct": correct, "time_ms": spent}

    a_res, b_res = results[match.a.user_id], results[match.b.user_id]

    # очко тому, кто ответил верно; если верно оба — тому, кто быстрее
    winner: Player | None = None
    if a_res["correct"] and b_res["correct"]:
        winner = match.a if a_res["time_ms"] <= b_res["time_ms"] else match.b
    elif a_res["correct"]:
        winner = match.a
    elif b_res["correct"]:
        winner = match.b
    if winner:
        winner.score += 1

    for player in (match.a, match.b):
        mine, theirs = results[player.user_id], results[match.other(player).user_id]
        await player.send(
            {
                "type": "round_result",
                "correct_answer": task["correct"],
                "you": {**mine, "point": winner is player},
                "them": {**theirs, "point": winner is match.other(player)},
                "score": {"you": player.score, "them": match.other(player).score},
            }
        )

    match.round_index += 1
    if match.round_index >= len(match.tasks):
        await _finish_match(match)
    else:
        await asyncio.sleep(2.5)  # время посмотреть правильный ответ
        await _send_round(match)


async def _finish_match(match: Match, forfeit: Player | None = None) -> None:
    if match.finished:
        return
    match.finished = True
    if match.timer:
        match.timer.cancel()

    a, b = match.a, match.b
    if forfeit is not None:
        outcome_a = 0.0 if forfeit is a else 1.0
    elif a.score != b.score:
        outcome_a = 1.0 if a.score > b.score else 0.0
    elif a.total_time_ms != b.total_time_ms:
        outcome_a = 1.0 if a.total_time_ms < b.total_time_ms else 0.0
    else:
        outcome_a = 0.5

    async with SessionLocal() as session:
        played_a = await _online_matches(session, a.user_id)
        played_b = await _online_matches(session, b.user_id)
        delta_a = _elo(a.rating, b.rating, outcome_a, _k_factor(a.rating, played_a))
        delta_b = _elo(b.rating, a.rating, 1 - outcome_a, _k_factor(b.rating, played_b))

        user_a = await session.get(User, a.user_id)
        user_b = await session.get(User, b.user_id)
        if user_a and user_b:
            user_a.rating = max(RATING_FLOOR, user_a.rating + delta_a)
            user_b.rating = max(RATING_FLOOR, user_b.rating + delta_b)

        winner_id = None
        if outcome_a == 1.0:
            winner_id = a.user_id
        elif outcome_a == 0.0:
            winner_id = b.user_id

        session.add(
            Duel(
                code=match.code,
                kind=DuelKind.ONLINE,
                task_ids=[t["id"] for t in match.tasks],
                challenger_id=a.user_id,
                opponent_id=b.user_id,
                challenger_score=a.score,
                opponent_score=b.score,
                challenger_time_ms=a.total_time_ms,
                opponent_time_ms=b.total_time_ms,
                challenger_rating_delta=delta_a,
                opponent_rating_delta=delta_b,
                winner_id=winner_id,
                state=DuelState.FINISHED,
                finished_at=datetime.now(UTC),
            )
        )
        await session.commit()

    for player, delta in ((a, delta_a), (b, delta_b)):
        opponent = match.other(player)
        if outcome_a == 0.5:
            result = "draw"
        elif winner_id == player.user_id:
            result = "win"
        else:
            result = "loss"
        await player.send(
            {
                "type": "match_over",
                "result": result,
                "forfeit": forfeit is not None,
                "score": {"you": player.score, "them": opponent.score},
                "time_ms": {"you": player.total_time_ms, "them": opponent.total_time_ms},
                "rating_delta": delta,
                "rating": player.rating + delta,
            }
        )

    _matches.pop(a.user_id, None)
    _matches.pop(b.user_id, None)


def _drop_from_queue(user_id: int) -> None:
    """Убирает игрока из очереди. Вызывать **под уже взятым** _queue_lock:
    asyncio.Lock не реентрантный, попытка взять его повторно вешает процесс."""
    for i, waiting in enumerate(_queue):
        if waiting.user_id == user_id:
            _queue.pop(i)
            return


async def shutdown_matches() -> None:
    """Гасит таймеры раундов при остановке сервера.

    Без этого uvicorn ждёт, пока досчитают все `asyncio.sleep(ROUND_SECONDS)`,
    и перезапуск подвисает на десятки секунд.
    """
    for match in set(_matches.values()):
        if match.timer:
            match.timer.cancel()
        match.finished = True
        for player in (match.a, match.b):
            await player.send(
                {"type": "error", "message": "сервер перезапускается, матч прерван"}
            )
    _matches.clear()
    _queue.clear()


async def _leave_queue(user_id: int) -> None:
    async with _queue_lock:
        _drop_from_queue(user_id)


@router.websocket("/ws/duel")
async def duel_socket(ws: WebSocket) -> None:
    await ws.accept()

    user = await _authenticate(ws)
    if user is None:
        await ws.send_json({"type": "error", "message": "не авторизован"})
        await ws.close()
        return

    player = Player(user_id=user.id, name=user.display_name, rating=user.rating, ws=ws)

    try:
        while True:
            message = await ws.receive_json()
            kind = message.get("type")

            if kind == "queue":
                if user.id in _matches:
                    await player.send({"type": "error", "message": "матч уже идёт"})
                    continue

                opponent: Player | None = None
                async with _queue_lock:
                    # не сводим игрока с самим собой из другой вкладки
                    for i, waiting in enumerate(_queue):
                        if waiting.user_id != user.id:
                            opponent = _queue.pop(i)
                            break
                    if opponent is None:
                        # блокировка уже взята — убираем прошлое соединение напрямую
                        _drop_from_queue(user.id)
                        _queue.append(player)

                if opponent is None:
                    await player.send({"type": "queued", "waiting": len(_queue)})
                else:
                    await _start_match(opponent, player)

            elif kind == "answer":
                match = _matches.get(user.id)
                if match is None or match.finished:
                    continue
                async with match.lock:
                    me = match.a if match.a.user_id == user.id else match.b
                    if me.answer is not None:
                        continue  # ответ уже принят, менять его нельзя
                    me.answer = str(message.get("value", ""))[:512]
                    me.answered_at = asyncio.get_event_loop().time()

                    await match.other(me).send({"type": "opponent_answered"})
                    if match.a.answer is not None and match.b.answer is not None:
                        await _finish_round(match)

            elif kind == "leave":
                await _leave_queue(user.id)
                await player.send({"type": "left"})

    except WebSocketDisconnect:
        pass
    finally:
        await _leave_queue(user.id)
        match = _matches.get(user.id)
        if match and not match.finished:
            me = match.a if match.a.user_id == user.id else match.b
            async with match.lock:
                await _finish_match(match, forfeit=me)
