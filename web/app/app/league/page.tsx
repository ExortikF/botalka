"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Shield } from "lucide-react";
import Avatar from "../Avatar";
import { api } from "@/lib/api";
import { nickStyle } from "@/lib/cosmetics";
import { plural } from "@/lib/exam";

type Row = {
  place: number;
  user_id: number;
  display_name: string;
  nick_color: string | null;
  prefix: string | null;
  avatar: string | null;
  frame: string | null;
  points: number;
  is_you: boolean;
  zone: "promote" | "stay" | "relegate";
};

type League = {
  division: string;
  division_title: string;
  division_color: string;
  next_division: string | null;
  promote: number;
  relegate: number;
  days_left: number;
  hours_left: number;
  your_place: number;
  rows: Row[];
};

export default function LeaguePage() {
  const [league, setLeague] = useState<League | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<League>("/api/league")
      .then(setLeague)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <p style={{ color: "var(--accent-2)" }}>{error}</p>;
  if (!league) return <p className="muted">Загрузка…</p>;

  return (
    <div className="space-y-6">
      <header className="flex items-start gap-3">
        <Shield size={22} style={{ color: league.division_color }} />
        <div>
          <h1 className="text-3xl">Лига · {league.division_title}</h1>
          <p className="muted mt-1 text-sm leading-relaxed">
            Очко за каждую новую верно решённую задачу за неделю. В конце недели{" "}
            {league.promote > 0 && league.next_division ? (
              <>
                верхние {league.promote} переходят в дивизион «{league.next_division}»
              </>
            ) : (
              <>верхние остаются на месте — выше дивизиона нет</>
            )}
            {league.relegate > 0 && <>, нижние {league.relegate} опускаются</>}.
          </p>
        </div>
      </header>

      <section
        className="card flex flex-wrap items-center justify-between gap-4 p-6"
        style={{ borderColor: `${league.division_color}55` }}
      >
        <div>
          <p className="eyebrow">Твоё место</p>
          <p className="h text-3xl" style={{ color: league.division_color }}>
            {league.your_place || "—"}
            <span className="muted text-base"> из {league.rows.length}</span>
          </p>
        </div>
        <div className="text-right">
          <p className="eyebrow">До конца недели</p>
          <p className="h text-3xl">
            {league.days_left > 0
              ? `${league.days_left} ${plural(league.days_left, "день", "дня", "дней")}`
              : `${league.hours_left} ${plural(league.hours_left, "час", "часа", "часов")}`}
          </p>
        </div>
      </section>

      {league.rows.length === 1 && (
        <p className="muted text-sm">
          Пока ты один в группе. Как только придут другие, они попадут сюда же — группы
          набираются по 20 человек.
        </p>
      )}

      <ul className="space-y-2">
        {league.rows.map((row, i) => {
          const nick = nickStyle(row.nick_color);
          const border =
            row.zone === "promote"
              ? "var(--accent)"
              : row.zone === "relegate"
                ? "var(--accent-2)"
                : "transparent";
          const previous = league.rows[i - 1];
          const zoneChanged = previous && previous.zone !== row.zone;

          return (
            <li key={row.user_id}>
              {zoneChanged && (
                <p className="eyebrow mb-2 mt-4 flex items-center gap-1.5">
                  {row.zone === "relegate" ? (
                    <>
                      <ChevronDown size={13} style={{ color: "var(--accent-2)" }} /> зона вылета
                    </>
                  ) : (
                    "остаются в дивизионе"
                  )}
                </p>
              )}

              <article
                className="card flex items-center gap-3 p-3"
                style={{
                  borderLeft: `4px solid ${border}`,
                  background: row.is_you ? "var(--accent-100)" : undefined,
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
                {row.zone === "promote" && (
                  <ChevronUp size={15} style={{ color: "var(--accent)" }} />
                )}
                <span className="h shrink-0">{row.points}</span>
              </article>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
