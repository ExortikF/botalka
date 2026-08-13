"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import { api } from "@/lib/api";
import { nickStyle } from "@/lib/cosmetics";
import Avatar from "../Avatar";

type LeaderRow = {
  place: number;
  user_id: number;
  display_name: string;
  rating: number;
  rank: string;
  rank_color: string;
  nick_color: string | null;
  avatar: string | null;
  frame: string | null;
  prefix: string | null;
  duels: number;
  wins: number;
  solved_week: number;
  is_you: boolean;
};

type Leaderboard = {
  board: string;
  rows: LeaderRow[];
  your_place: number | null;
};

const BOARDS = [
  { key: "rating", label: "Рейтинг дуэлей" },
  { key: "week", label: "Активность за неделю" },
];

function NickName({ row }: { row: LeaderRow }) {
  const nick = nickStyle(row.nick_color);
  return (
    <span className={nick.className} style={nick.style}>
      {row.prefix && `${row.prefix} `}
      {row.display_name}
    </span>
  );
}

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
    <div className="page">
      <header className="flex items-start gap-3">
        <Trophy size={22} style={{ color: "var(--accent-2)" }} />
        <div>
          <h1 className="page-title">Лидерборд</h1>
          <p className="page-subtitle">
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
          <Link
            className="btn mt-5"
            href={board === "rating" ? "/app/duels/online" : "/app/quiz"}
          >
            {board === "rating" ? "Найти соперника" : "Решать задачи"}
          </Link>
        </section>
      ) : (
        <>
          {data.your_place && (
            <p className="muted text-sm">
              Твоё место: <span className="h text-base">{data.your_place}</span>{" "}
              из {data.rows.length >= 30 ? "топа" : data.rows.length}
            </p>
          )}

          {data.rows.length >= 3 && <Podium rows={data.rows} />}

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
                      <th className="px-4 py-3 font-medium">
                        Решено за неделю
                      </th>
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
                      <span className={row.place <= 3 ? "h text-base" : ""}>
                        {row.place}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        className="flex items-center gap-2 hover:underline"
                        href={
                          row.is_you ? "/app/profile" : `/app/u/${row.user_id}`
                        }
                      >
                        <Avatar
                          name={row.display_name}
                          avatar={row.avatar}
                          frame={row.frame}
                          size={28}
                          rounded="rounded-full"
                        />
                        <NickName row={row} />
                        {row.is_you && (
                          <span className="muted text-xs">— это ты</span>
                        )}
                      </Link>
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

/** Тройка лидеров отдельно: в таблице первое место ничем не выделено,
    а именно оно должно быть целью. */
function Podium({ rows }: { rows: LeaderRow[] }) {
  const [first, second, third] = rows;
  const places = [
    { row: second, size: 52, pad: "20px 14px", value: 22, border: "var(--divider)" },
    { row: first, size: 64, pad: "26px 14px", value: 27, border: "#b8860b" },
    { row: third, size: 48, pad: "18px 14px", value: 20, border: "var(--divider)" },
  ];

  return (
    <section className="grid items-end gap-3.5 sm:grid-cols-[1fr_1.2fr_1fr]">
      {places.map(({ row, size, pad, value, border }) => (
        <Link
          key={row.user_id}
          href={row.is_you ? "/app/profile" : `/app/u/${row.user_id}`}
          className="text-center"
          style={{
            background: "var(--card)",
            border: `${border === "#b8860b" ? 2 : 1}px solid ${border}`,
            borderRadius: 18,
            padding: pad,
            boxShadow: border === "#b8860b" ? "0 8px 22px rgba(184,134,11,.16)" : undefined,
          }}
        >
          <span className="mx-auto mb-2 block w-fit">
            <Avatar
              name={row.display_name}
              avatar={row.avatar}
              frame={row.frame}
              size={size}
              rounded="rounded-full"
            />
          </span>
          <span className="h muted block text-[13.5px]">
            #{row.place} {row.display_name}
            {row.is_you && " · ты"}
          </span>
          <span className="h mt-1 block" style={{ fontSize: value, fontWeight: 800 }}>
            {row.rating}
          </span>
        </Link>
      ))}
    </section>
  );
}
