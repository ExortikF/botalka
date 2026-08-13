"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Swords, X } from "lucide-react";
import MathText from "../../../Math";
import { checkAchievements } from "@/lib/achievements";

/** Тот же хост, что и сайт, если стоит прокси; в разработке — порт бэкенда. */
function socketUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  if (explicit) return explicit;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/duel`;
}

type Phase = "idle" | "queued" | "playing" | "over";

type RoundMsg = {
  index: number;
  total: number;
  seconds: number;
  task: { statement: string; number: number; title: string };
  score: { you: number; them: number };
};

type RoundResult = {
  correct_answer: string;
  you: { correct: boolean; time_ms: number; point: boolean };
  them: { correct: boolean; time_ms: number; point: boolean };
  score: { you: number; them: number };
};

type Over = {
  result: "win" | "loss" | "draw";
  forfeit: boolean;
  score: { you: number; them: number };
  time_ms: { you: number; them: number };
  rating_delta: number;
  rating: number;
};

export default function OnlineDuelPage() {
  const ws = useRef<WebSocket | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState("");
  const [opponent, setOpponent] = useState<{
    name: string;
    rating: number;
  } | null>(null);
  const [round, setRound] = useState<RoundMsg | null>(null);
  const [result, setResult] = useState<RoundResult | null>(null);
  const [over, setOver] = useState<Over | null>(null);
  const [answer, setAnswer] = useState("");
  const [sent, setSent] = useState(false);
  const [opponentAnswered, setOpponentAnswered] = useState(false);
  const [left, setLeft] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);

  // Таймер только рисует: результат раунда считает сервер по своим часам.
  useEffect(() => {
    if (!round || result) return;
    setLeft(round.seconds);
    const id = setInterval(() => setLeft((v) => Math.max(0, v - 1)), 1000);
    return () => clearInterval(id);
  }, [round, result]);

  useEffect(() => {
    if (round && !result) inputRef.current?.focus();
  }, [round, result]);

  const connect = useCallback(() => {
    setError("");
    const socket = new WebSocket(socketUrl());
    ws.current = socket;

    socket.onopen = () => socket.send(JSON.stringify({ type: "queue" }));

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      switch (msg.type) {
        case "queued":
          setPhase("queued");
          break;
        case "match_found":
          setOpponent(msg.opponent);
          setPhase("playing");
          break;
        case "round":
          setRound(msg);
          setResult(null);
          setAnswer("");
          setSent(false);
          setOpponentAnswered(false);
          break;
        case "opponent_answered":
          setOpponentAnswered(true);
          break;
        case "round_result":
          setResult(msg);
          break;
        case "match_over":
          setOver(msg);
          setPhase("over");
          checkAchievements();
          socket.close();
          break;
        case "error":
          setError(msg.message);
          setPhase("idle");
          socket.close();
          break;
      }
    };

    socket.onerror = () => setError("не удалось подключиться к серверу матчей");
    socket.onclose = () => {
      ws.current = null;
      setPhase((p) => (p === "over" ? p : p === "idle" ? p : "idle"));
    };
  }, []);

  useEffect(() => () => ws.current?.close(), []);

  function submit() {
    if (!ws.current || sent || !answer.trim()) return;
    ws.current.send(JSON.stringify({ type: "answer", value: answer }));
    setSent(true);
  }

  function cancel() {
    ws.current?.close();
    setPhase("idle");
  }

  function reset() {
    // Link на ту же страницу ничего не перезагружает — состояние надо сбросить руками
    ws.current?.close();
    ws.current = null;
    setOver(null);
    setRound(null);
    setResult(null);
    setOpponent(null);
    setAnswer("");
    setSent(false);
    setOpponentAnswered(false);
    setPhase("idle");
  }

  if (phase === "over" && over)
    return (
      <Result
        over={over}
        opponent={opponent}
        onAgain={() => {
          reset();
          connect();
        }}
      />
    );

  if (phase === "playing" && round)
    return (
      <div className="space-y-6">
        <div className="card flex items-center justify-between gap-6 p-5">
          <Side
            name="Ты"
            score={round.score.you}
            highlight={result?.you.point}
          />
          <div className="text-center">
            <p className="h text-2xl">
              {result ? result.score.you : round.score.you} :{" "}
              {result ? result.score.them : round.score.them}
            </p>
            <p className="muted text-xs uppercase tracking-wide">
              раунд {round.index} из {round.total}
            </p>
          </div>
          <Side
            name={opponent?.name ?? "Соперник"}
            score={round.score.them}
            highlight={result?.them.point}
            right
          />
        </div>

        <div className="text-center">
          <p
            className="h text-3xl"
            style={{ color: left <= 10 ? "var(--accent-2)" : undefined }}
          >
            {result ? "—" : left}
          </p>
          <p className="muted text-xs">секунд до конца раунда</p>
        </div>

        <article className="card space-y-5 p-7">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="rounded-full px-3 py-1 text-xs font-medium"
              style={{
                background: "var(--accent-100)",
                color: "var(--accent-700)",
              }}
            >
              Задание № {round.task.number}
            </span>
            <span className="muted text-sm">{round.task.title}</span>
          </div>

          <MathText
            className="block text-lg leading-relaxed"
            text={round.task.statement}
          />

          {result ? (
            <div
              className="rounded-xl p-4"
              style={{
                background: result.you.point
                  ? "var(--accent-100)"
                  : "var(--accent-2-100)",
              }}
            >
              <p className="font-semibold">
                {result.you.point
                  ? "Очко твоё"
                  : result.them.point
                    ? "Очко у соперника"
                    : "Раунд без очка — оба ошиблись"}
              </p>
              <p className="muted mt-1 text-sm">
                Правильный ответ: {result.correct_answer} · ты{" "}
                {result.you.correct ? "верно" : "мимо"} за{" "}
                {(result.you.time_ms / 1000).toFixed(1)} с, соперник{" "}
                {result.them.correct ? "верно" : "мимо"} за{" "}
                {(result.them.time_ms / 1000).toFixed(1)} с
              </p>
            </div>
          ) : (
            <>
              <form
                className="flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  submit();
                }}
              >
                <input
                  ref={inputRef}
                  className="input"
                  placeholder="Ответ"
                  value={answer}
                  disabled={sent}
                  onChange={(e) => setAnswer(e.target.value)}
                />
                <button
                  className="btn"
                  type="submit"
                  disabled={sent || !answer.trim()}
                >
                  Ответить
                </button>
              </form>
              <p className="muted text-sm">
                {sent && "Ответ принят, ждём соперника. "}
                {opponentAnswered && "Соперник уже ответил."}
              </p>
            </>
          )}
        </article>
      </div>
    );

  return (
    <div className="space-y-7">
      <header>
        <h1 className="text-3xl">Онлайн-дуэль</h1>
        <p className="muted mt-2">
          Семь раундов, вопрос приходит обоим одновременно. Очко забирает тот,
          кто ответил верно и раньше. Рейтинг меняется только здесь.
        </p>
      </header>

      {phase === "queued" ? (
        <section className="card flex flex-col items-center gap-4 p-10 text-center">
          <Loader2
            className="animate-spin"
            style={{ color: "var(--accent)" }}
          />
          <p className="text-lg">Ищем соперника…</p>
          <p className="muted text-sm">
            Игроков пока мало — если никого нет, позови друга, чтобы он тоже
            встал в очередь.
          </p>
          <button className="btn-ghost" onClick={cancel}>
            <X size={15} /> Отменить
          </button>
        </section>
      ) : (
        <section className="card space-y-4 p-7">
          <div className="flex items-center gap-3">
            <Swords size={20} style={{ color: "var(--accent-2)" }} />
            <h2 className="text-xl">Найти соперника</h2>
          </div>
          <p className="muted text-sm leading-relaxed">
            Подбор идёт среди всех, кто сейчас в очереди. Победа над более
            сильным игроком даёт больше рейтинга.
          </p>
          <button className="btn btn-accent2" onClick={connect}>
            Найти соперника
          </button>
          {error && (
            <p className="text-sm" style={{ color: "var(--accent-2)" }}>
              {error}
            </p>
          )}
        </section>
      )}

      <Link className="muted text-sm hover:underline" href="/app/duels">
        ← Дуэли по ссылке
      </Link>
    </div>
  );
}

function Side({
  name,
  score,
  highlight,
  right,
}: {
  name: string;
  score: number;
  highlight?: boolean;
  right?: boolean;
}) {
  return (
    <div className={right ? "text-right" : ""}>
      <p className="font-medium">{name}</p>
      <p
        className="muted text-sm"
        style={{ color: highlight ? "var(--accent)" : undefined }}
      >
        {score} {highlight && "+1"}
      </p>
    </div>
  );
}

function Result({
  over,
  opponent,
  onAgain,
}: {
  over: Over;
  opponent: { name: string } | null;
  onAgain: () => void;
}) {
  const label =
    over.result === "win"
      ? "Победа"
      : over.result === "loss"
        ? "Поражение"
        : "Ничья";

  return (
    <div className="space-y-6">
      <section className="card p-8 text-center">
        <p className="h text-4xl">{label}</p>
        <p className="h mt-4 text-5xl">
          {over.score.you} : {over.score.them}
        </p>
        <p className="muted mt-2">
          против {opponent?.name ?? "соперника"} · твоё время{" "}
          {(over.time_ms.you / 1000).toFixed(0)} с против{" "}
          {(over.time_ms.them / 1000).toFixed(0)} с
        </p>

        {over.forfeit && (
          <p className="muted mt-2 text-sm">
            Соперник отключился — победа присуждена.
          </p>
        )}

        <p
          className="mt-5 inline-block rounded-xl px-4 py-2 font-semibold"
          style={{
            background:
              over.rating_delta >= 0
                ? "var(--accent-100)"
                : "var(--accent-2-100)",
            color:
              over.rating_delta >= 0 ? "var(--accent-700)" : "var(--accent-2)",
          }}
        >
          рейтинг {over.rating_delta >= 0 ? "+" : ""}
          {over.rating_delta} → {over.rating}
        </p>
      </section>

      <div className="flex gap-3">
        <button className="btn" onClick={onAgain}>
          Ещё матч
        </button>
        <Link className="btn-ghost" href="/app/duels">
          К дуэлям
        </Link>
      </div>
    </div>
  );
}
