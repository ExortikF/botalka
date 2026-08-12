"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import { api } from "@/lib/api";
import { initials } from "@/lib/format";

type LeaderRow = {
  place: number;
  user_id: number;
  display_name: string;
  rating: number;
  rank: string;
  rank_color: string;
  nick_color: string | null;
  prefix: string | null;
  duels: number;
  wins: number;
  solved_week: number;
  is_you: boolean;
};

type Leaderboard = { board: string; rows: LeaderRow[]; your_place: number | null };

const BOARDS = [
  { key: "rating", label: "Рейтинг дуэлей" },
  { key: "week", label: "Активность за неделю" },
];

export default function RatingPage() {
  const [board, setBoard] = useState("rating");
  const [data, setData] = useState<Leaderboard | null>(null);

  useEffect(() => {
    setData(null);
    api<Leaderboard>(`/api/leaderboard?board=${board}`)
      .then(setData)
      .catch(() => setData(null));
  }, [board]);

  return (
    <div className="space-y-7">
      <header className="flex items-start gap-3">
        <Trophy size={22} style={{ color: "var(--accent-2)" }} />
        <div>
          <h1 className="text-3xl">Лидерборд</h1>
          <p className="muted mt-1 text-sm">
            {board === "rating"
              ? "Рейтинг растёт только в онлайн-матчах — квизы и дуэли по ссылке на него не влияют."
              : "Сколько разных задач решено верно за последние семь дней."}
          </p>
        </div>
      </header>

      <div className="flex flex-wrap gap-2">
        {BOARDS.map((b) => (
          <button
            key={b.key}
            onClick={() => setBoard(b.key)}
            className={`pill ${board === b.key ? "pill-active" : "pill-idle"}`}
            style={{ border: "1px solid var(--divider)" }}
          >
            {b.label}
          </button>
        ))}
      </div>

      {!data ? (
        <p className="muted">Загрузка…</p>
      ) : data.rows.length === 0 ? (
        <section className="card p-8 text-center">
          <p className="text-lg">Таблица пока пустая</p>
          <p className="muted mx-auto mt-2 max-w-md text-sm">
            {board === "rating"
              ? "Сюда попадают те, кто сыграл хотя бы один онлайн-матч. Будь первым."
              : "Как только кто-нибудь начнёт решать, здесь появятся результаты."}
          </p>
          <Link className="btn mt-5" href={board === "rating" ? "/app/duels/online" : "/app/quiz"}>
            {board === "rating" ? "Найти соперника" : "Решать задачи"}
          </Link>
        </section>
      ) : (
        <>
          {data.your_place && (
            <p className="muted text-sm">
              Твоё место: <span className="h text-base">{data.your_place}</span> из{" "}
              {data.rows.length >= 30 ? "топа" : data.rows.length}
            </p>
          )}

          <section className="card overflow-x-auto">
            <table className="w-full text-sm" style={{ minWidth: "34rem" }}>
              <thead>
                <tr
                  className="muted text-left"
                  style={{ borderBottom: "1px solid var(--divider)" }}
                >
                  <th className="px-4 py-3 font-medium">#</th>
                  <th className="px-4 py-3 font-medium">Участник</th>
                  {board === "rating" ? (
                    <>
                      <th className="px-4 py-3 font-medium">Рейтинг</th>
                      <th className="px-4 py-3 font-medium">Матчи</th>
                      <th className="px-4 py-3 font-medium">Победы</th>
                    </>
                  ) : (
                    <>
                      <th className="px-4 py-3 font-medium">Решено за неделю</th>
                      <th className="px-4 py-3 font-medium">Рейтинг</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr
                    key={row.user_id}
                    style={{
                      borderBottom: "1px solid var(--divider)",
                      background: row.is_you ? "var(--accent-100)" : undefined,
                    }}
                  >
                    <td className="px-4 py-3">
                      <span className={row.place <= 3 ? "h text-base" : ""}>{row.place}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-2">
                        <span
                          className="flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-semibold"
                          style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
                        >
                          {initials(row.display_name)}
                        </span>
                        <span style={{ color: row.nick_color ?? undefined }}>
                        {row.prefix && `${row.prefix} `}
                        {row.display_name}
                      </span>
                        {row.is_you && <span className="muted text-xs">— это ты</span>}
                      </span>
                    </td>
                    {board === "rating" ? (
                      <>
                        <td className="px-4 py-3">
                          {row.rating}
                          <span className="muted ml-2 text-xs">{row.rank}</span>
                        </td>
                        <td className="px-4 py-3">{row.duels}</td>
                        <td className="px-4 py-3">{row.wins}</td>
                      </>
                    ) : (
                      <>
                        <td className="px-4 py-3">{row.solved_week}</td>
                        <td className="px-4 py-3 muted">{row.rating}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  );
}
