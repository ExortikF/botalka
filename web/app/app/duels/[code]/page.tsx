"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { Check, Copy, Swords } from "lucide-react";
import { getDuel, type Duel, type DuelSide } from "@/lib/api";
import { initials } from "@/lib/format";

export default function DuelPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = use(params);
  const [duel, setDuel] = useState<Duel | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    getDuel(code)
      .then(setDuel)
      .catch((e: Error) => setError(e.message));
  }, [code]);

  useEffect(load, [load]);

  async function copyLink() {
    await navigator.clipboard.writeText(
      `${window.location.origin}/app/duels/${code}`,
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (error)
    return (
      <div className="space-y-4">
        <p style={{ color: "var(--accent-2)" }}>{error}</p>
        <Link className="btn-ghost" href="/app/duels">
          К дуэлям
        </Link>
      </div>
    );

  if (!duel) return <p className="muted">Загрузка…</p>;

  const you = duel.your_side === "opponent" ? duel.opponent : duel.challenger;
  const them = duel.your_side === "opponent" ? duel.challenger : duel.opponent;
  const youWon = duel.winner && duel.winner === duel.your_side;

  return (
    <div className="space-y-7">
      <header className="flex items-center gap-3">
        <Swords size={22} style={{ color: "var(--accent-2)" }} />
        <div>
          <h1 className="text-2xl">Дуэль</h1>
          <p className="muted text-sm">
            {duel.total} раундов · один набор задач на двоих
          </p>
        </div>
      </header>

      <section className="card p-7">
        <div className="flex items-center justify-between gap-6">
          <Player
            side={duel.challenger}
            highlight={duel.winner === "challenger"}
          />

          <div className="text-center">
            <p className="h text-3xl">
              {duel.challenger.score ?? "—"} : {duel.opponent?.score ?? "—"}
            </p>
            <p className="muted mt-1 text-xs uppercase tracking-wide">
              {duel.state === "finished" ? "финал" : "идёт"}
            </p>
          </div>

          {duel.opponent ? (
            <Player
              side={duel.opponent}
              highlight={duel.winner === "opponent"}
              right
            />
          ) : (
            <div className="text-right">
              <span
                className="flex h-11 w-11 items-center justify-center rounded-full text-sm"
                style={{ background: "var(--surface)", color: "var(--n-500)" }}
              >
                ?
              </span>
              <p className="muted mt-1 text-sm">ждём</p>
            </div>
          )}
        </div>

        {duel.state === "finished" && (
          <p
            className="mt-6 rounded-xl p-4 text-center font-medium"
            style={{
              background: youWon ? "var(--accent-100)" : "var(--surface)",
              color: youWon ? "var(--accent-700)" : "var(--text)",
            }}
          >
            {duel.winner === "draw"
              ? "Ничья — одинаковый счёт и одинаковое время"
              : youWon
                ? "Победа"
                : duel.your_side
                  ? "Поражение"
                  : `Победил(а) ${duel.winner === "challenger" ? duel.challenger.name : duel.opponent?.name}`}
            {duel.winner !== "draw" &&
              duel.challenger.score === duel.opponent?.score &&
              " — счёт равный, решило время"}
          </p>
        )}
      </section>

      {duel.can_play && (
        <section className="card space-y-3 p-6">
          <h2 className="text-lg">
            {duel.your_side === "challenger"
              ? "Пройди свою половину"
              : "Тебя вызвали"}
          </h2>
          <p className="muted text-sm leading-relaxed">
            {duel.your_side === "challenger"
              ? "Реши задачи, потом отправь ссылку сопернику. Время учитывается — при равном счёте побеждает тот, кто быстрее."
              : `${duel.challenger.name} вызывает тебя. Задачи те же самые, что решал соперник.`}
          </p>
          <Link
            className="btn btn-accent2"
            href={`/app/quiz/run?duel=${duel.code}`}
          >
            {duel.your_side === "challenger" ? "Начать" : "Принять вызов"}
          </Link>
        </section>
      )}

      {duel.your_side === "challenger" && duel.state !== "finished" && (
        <section className="card space-y-3 p-6">
          <h2 className="text-lg">Ссылка для друга</h2>
          <div className="flex flex-wrap gap-2">
            <input
              className="input flex-1"
              readOnly
              value={
                typeof window === "undefined"
                  ? ""
                  : `${window.location.origin}/app/duels/${code}`
              }
              onFocus={(e) => e.target.select()}
            />
            <button className="btn-ghost" onClick={copyLink}>
              {copied ? <Check size={15} /> : <Copy size={15} />}
              {copied ? "Скопировано" : "Копировать"}
            </button>
          </div>
          <p className="muted text-xs">
            Ссылка живёт двое суток. Принять вызов может только один человек.
          </p>
        </section>
      )}

      {!duel.can_play && duel.state !== "finished" && you?.finished && (
        <p className="muted text-sm">
          Ты свою половину прошёл
          {them ? " — ждём соперника." : ". Отправь ссылку другу."}
        </p>
      )}

      <Link className="muted text-sm hover:underline" href="/app/duels">
        ← Все дуэли
      </Link>
    </div>
  );
}

function Player({
  side,
  highlight,
  right,
}: {
  side: DuelSide;
  highlight?: boolean;
  right?: boolean;
}) {
  return (
    <div className={right ? "text-right" : ""}>
      <span
        className={`flex h-11 w-11 items-center justify-center rounded-full text-sm font-semibold ${
          right ? "ml-auto" : ""
        }`}
        style={{
          background: highlight ? "var(--accent-2-100)" : "var(--accent-100)",
          color: highlight ? "var(--accent-2)" : "var(--accent-700)",
        }}
      >
        {initials(side.name)}
      </span>
      <p className="mt-2 max-w-[8rem] truncate text-sm font-medium">
        {side.name}
      </p>
      <p className="muted text-xs">
        {side.finished
          ? `${Math.round((side.time_ms ?? 0) / 1000)} с`
          : "ещё не проходил"}
      </p>
    </div>
  );
}
