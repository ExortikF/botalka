"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { ArrowLeft, Coins, Info, Trophy } from "lucide-react";
import Avatar from "../../Avatar";
import { api } from "@/lib/api";
import { nickStyle } from "@/lib/cosmetics";
import type { Tournament } from "../types";
import { placeLabel } from "../types";
import Countdown from "../Countdown";
import Contest from "./Contest";

export default function TournamentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [data, setData] = useState<Tournament | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api<Tournament>(`/api/tournaments/${id}`)
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);

  if (error)
    return (
      <div className="space-y-4">
        <p style={{ color: "var(--accent-2)" }}>{error}</p>
        <Link className="btn-ghost" href="/app/tournaments">
          К турнирам
        </Link>
      </div>
    );

  if (!data) return <p className="muted">Загрузка…</p>;

  const period = `${formatDate(data.starts_at)} — ${formatDate(data.ends_at)}`;

  return (
    <div className="page">
      <Link
        className="muted flex items-center gap-1.5 text-sm hover:underline"
        href="/app/tournaments"
      >
        <ArrowLeft size={15} /> Все турниры
      </Link>

      <section
        className="relative overflow-hidden text-white"
        style={{
          background: data.color,
          borderRadius: "var(--radius-lg)",
          padding: "30px 32px",
        }}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "repeating-linear-gradient(0deg,rgba(255,255,255,.06) 0 1px,transparent 1px 26px),repeating-linear-gradient(90deg,rgba(255,255,255,.06) 0 1px,transparent 1px 26px)",
          }}
        />
        <div className="relative">
          <span className="flex flex-wrap items-center gap-2.5">
            <span
              className="rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-wider"
              style={{ background: "rgba(255,255,255,.22)" }}
            >
              {data.state}
            </span>
            {data.seconds_left !== null && (
              <span className="text-sm opacity-90">
                осталось{" "}
                <Countdown className="h" seconds={data.seconds_left} />
              </span>
            )}
          </span>

          <h1 className="h mt-3" style={{ fontSize: 30, fontWeight: 800 }}>
            {data.title}
          </h1>
          {data.description && (
            <p className="mt-2 max-w-[620px] text-[14.5px] leading-relaxed opacity-90">
              {data.description}
            </p>
          )}
          <p className="mt-3 text-xs opacity-75">{period}</p>
        </div>
      </section>

      {!data.eligible && (
        <p
          className="flex items-center gap-2 rounded-xl p-4 text-sm"
          style={{ background: "var(--accent-2-100)", color: "var(--accent-2)" }}
        >
          <Info size={16} /> Ты не участвуешь: {data.ineligible_reason}
        </p>
      )}

      <section className="grid gap-3 sm:grid-cols-3">
        <div className="tile">
          <p className="tile-value">{data.your_place ?? "—"}</p>
          <p className="tile-label">твоё место</p>
        </div>
        <div className="tile">
          <p className="tile-value" style={{ color: data.color }}>
            {data.your_points}
          </p>
          <p className="tile-label">
            {data.format === "contest" ? "твоих баллов" : "твоих очков"}
          </p>
        </div>
        <div className="tile">
          <p className="tile-value">
            {data.format === "contest" ? data.your_penalty : data.rows.length}
          </p>
          <p className="tile-label">
            {data.format === "contest" ? "штрафных минут" : "участников в таблице"}
          </p>
        </div>
      </section>

      {data.format === "contest" && <Contest data={data} onReload={load} />}

      {data.format === "marathon" && (
      <section className="card" style={{ padding: "26px 28px" }}>
        <h2 className="section-title">Как считаются очки</h2>
        <ul className="mt-3 flex flex-col gap-2 text-sm">
          {data.rules.map((rule, i) => (
            <li key={i} className="flex flex-wrap items-baseline gap-2">
              <b style={{ color: data.color }}>+{rule.points}</b>
              <span>{rule.title}</span>
              {rule.task_numbers.length > 0 && (
                <span className="muted">
                  · только номера {rule.task_numbers.join(", ")}
                </span>
              )}
              {rule.exclude_hints && (
                <span className="muted">· без подсказок</span>
              )}
              {rule.daily_cap !== null && (
                <span className="muted">· не больше {rule.daily_cap} в день</span>
              )}
            </li>
          ))}
        </ul>
      </section>
      )}

      {data.prizes.length > 0 && (
        <section className="card" style={{ padding: "26px 28px" }}>
          <h2 className="section-title flex items-center gap-2">
            <Trophy size={18} style={{ color: "var(--accent-2)" }} /> Награды
          </h2>
          <ul className="mt-3 flex flex-col gap-2 text-sm">
            {data.prizes.map((prize, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <span className="w-28 shrink-0 font-medium">
                  {placeLabel(prize)}
                </span>
                {prize.coins > 0 && (
                  <span className="flex items-center gap-1">
                    <Coins size={14} style={{ color: "#c98a00" }} />
                    {prize.coins}
                  </span>
                )}
                {prize.item_title && (
                  <span className="muted">· {prize.item_title}</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-3">
        <div className="section-head">
          <h2 className="section-title">
            Таблица
            {data.format === "contest" && data.problems.length > 0 && (
              <span className="muted ml-2 text-sm font-normal">
                колонки — задачи {data.problems[0].letter}…
                {data.problems[data.problems.length - 1].letter}
              </span>
            )}
          </h2>
          {data.state !== "завершён" && (
            <span className="section-note">обновляется на лету</span>
          )}
        </div>

        {data.rows.length === 0 ? (
          <p className="muted text-sm">
            Очков пока ни у кого нет — можно стать первым.
          </p>
        ) : (
          <ul className="space-y-2">
            {data.rows.map((row) => {
              const nick = nickStyle(row.nick_color);
              return (
                <li key={row.user_id}>
                  <article
                    className="row-card"
                    style={{
                      background: row.is_you ? "var(--accent-100)" : undefined,
                      borderLeft:
                        row.prize_coins > 0 || row.prize_item
                          ? `4px solid ${data.color}`
                          : undefined,
                    }}
                  >
                    <span className="h w-7 shrink-0 text-center">{row.place}</span>
                    <Avatar
                      name={row.display_name}
                      avatar={row.avatar}
                      frame={row.frame}
                      size={32}
                      rounded="rounded-full"
                    />
                    <Link
                      className="min-w-0 flex-1 truncate hover:underline"
                      href={row.is_you ? "/app/profile" : `/app/u/${row.user_id}`}
                    >
                      <span className={nick.className} style={nick.style}>
                        {row.prefix && `${row.prefix} `}
                        {row.display_name}
                      </span>
                    </Link>

                    {(row.prize_coins > 0 || row.prize_item) && (
                      <span className="muted flex shrink-0 items-center gap-1 text-xs">
                        <Trophy size={12} style={{ color: "var(--accent-2)" }} />
                        {row.prize_coins > 0 && row.prize_coins}
                        {row.prize_item && " + предмет"}
                      </span>
                    )}

                    {data.format === "contest" &&
                      data.problems.map((problem) => (
                        <span
                          key={problem.letter}
                          className="hidden w-8 shrink-0 text-center text-sm sm:block"
                          style={{
                            color: row.cells[problem.letter]?.startsWith("+")
                              ? "var(--accent)"
                              : "var(--accent-2)",
                          }}
                          title={`Задача ${problem.letter}`}
                        >
                          {row.cells[problem.letter] || "·"}
                        </span>
                      ))}

                    {data.format === "contest" && (
                      <span className="muted w-16 shrink-0 text-right text-xs">
                        {row.penalty} мин
                      </span>
                    )}

                    <span className="h shrink-0">{row.points}</span>
                  </article>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ru", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Moscow",
  });
}
