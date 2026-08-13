"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Coins, Flag, Trophy } from "lucide-react";
import { api } from "@/lib/api";
import type { Tournament } from "./types";
import { STATE_COLOR, formatLeft } from "./types";

export default function TournamentsPage() {
  const [rows, setRows] = useState<Tournament[] | null>(null);

  useEffect(() => {
    api<Tournament[]>("/api/tournaments")
      .then(setRows)
      .catch(() => setRows([]));
  }, []);

  if (rows === null) return <p className="muted">Загрузка…</p>;

  return (
    <div className="page">
      <header className="flex items-start gap-3">
        <Flag size={22} style={{ color: "var(--accent-2)" }} />
        <div>
          <h1 className="page-title">Турниры</h1>
          <p className="page-subtitle">
            Соревнования с призами: у каждого свои правила начисления очков и свой
            срок. Очки считаются автоматически — отдельно записываться не нужно.
          </p>
        </div>
      </header>

      {rows.length === 0 ? (
        <section className="card p-8 text-center">
          <p className="text-lg">Сейчас турниров нет</p>
          <p className="muted mx-auto mt-2 max-w-md text-sm">
            Как только объявим новый, он появится здесь — и очки начнут считаться
            с первой же решённой задачи.
          </p>
        </section>
      ) : (
        <ul className="space-y-3">
          {rows.map((row) => (
            <li key={row.id}>
              <Link
                href={`/app/tournaments/${row.id}`}
                className="card block overflow-hidden transition hover:shadow-[var(--shadow-sm)]"
              >
                <div
                  style={{
                    background: row.color,
                    color: "#fff",
                    padding: "20px 24px",
                  }}
                >
                  <span className="flex flex-wrap items-center gap-2.5">
                    <span
                      className="rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider"
                      style={{ background: "rgba(255,255,255,.22)" }}
                    >
                      {row.state}
                    </span>
                    {row.seconds_left !== null && (
                      <span className="text-xs opacity-90">
                        осталось {formatLeft(row.seconds_left)}
                      </span>
                    )}
                  </span>
                  <p className="h mt-2 text-2xl">{row.title}</p>
                  {row.description && (
                    <p className="mt-1 text-sm opacity-90">{row.description}</p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-x-6 gap-y-2 p-5 text-sm">
                  <span>
                    <span className="muted">Твоё место: </span>
                    <b>{row.your_place ?? "—"}</b>
                    <span className="muted"> · {row.your_points} очк.</span>
                  </span>

                  {row.prizes.length > 0 && (
                    <span className="flex items-center gap-1.5">
                      <Trophy size={14} style={{ color: "var(--accent-2)" }} />
                      <span className="muted">За первое место:</span>
                      <b>{row.prizes[0].coins}</b>
                      <Coins size={13} style={{ color: "#c98a00" }} />
                      {row.prizes[0].item_title && <b>+ {row.prizes[0].item_title}</b>}
                    </span>
                  )}

                  <span
                    className="ml-auto text-xs font-semibold"
                    style={{ color: STATE_COLOR[row.state] ?? "var(--n-600)" }}
                  >
                    подробнее →
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
