"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, X } from "lucide-react";
import { api } from "@/lib/api";
import MathText from "../../../Math";

type Suggestion = {
  id: number;
  author: string;
  author_id: number;
  number: number;
  statement: string;
  answer: string;
  solution: string | null;
  source: string | null;
  status: string;
  moderator_note: string | null;
  task_id: number | null;
  created_at: string;
};

export default function SuggestionsPage() {
  const [rows, setRows] = useState<Suggestion[] | null>(null);
  const [onlyPending, setOnlyPending] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api<Suggestion[]>(`/api/admin/suggestions?only_pending=${onlyPending}`)
      .then(setRows)
      .catch(() => setRows([]));
  }, [onlyPending]);

  useEffect(load, [load]);

  async function approve(id: number) {
    setBusy(id);
    setError("");
    try {
      await api(`/api/admin/suggestions/${id}/approve`, { method: "POST" });
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function reject(id: number) {
    const note = window.prompt("Что ответить автору? (можно пусто)") ?? "";
    setBusy(id);
    try {
      await api(`/api/admin/suggestions/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ note: note || null }),
      });
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl">Задачи от учеников</h1>
          <p className="muted mt-1 text-sm">
            Принятая задача попадает в банк <b>черновиком</b> и ждёт публикации из
            карточки — сначала стоит посмотреть, как она выглядит в квизе. Автору
            начисляются монеты.
          </p>
        </div>
        <Link className="btn-ghost" href="/app/admin">
          <ArrowLeft size={15} /> К задачам
        </Link>
      </header>

      <button
        className={`pill ${onlyPending ? "pill-active" : "pill-idle"}`}
        style={{ border: "1px solid var(--divider)" }}
        onClick={() => setOnlyPending((v) => !v)}
      >
        {onlyPending ? "Только новые" : "Все присланные"}
      </button>

      {error && (
        <p className="text-sm" style={{ color: "var(--accent-2)" }}>
          {error}
        </p>
      )}

      {rows === null ? (
        <p className="muted">Загрузка…</p>
      ) : rows.length === 0 ? (
        <p className="muted">Присланных задач пока нет.</p>
      ) : (
        <ul className="space-y-3">
          {rows.map((row) => (
            <li key={row.id}>
              <article className="card space-y-3 p-5">
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <span className="font-medium">
                    №{row.number} · {row.author}
                  </span>
                  <span className="muted text-xs">
                    {row.source && `${row.source} · `}
                    {new Date(row.created_at).toLocaleString("ru", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                <div className="rounded-xl p-3 text-sm" style={{ background: "var(--surface)" }}>
                  <MathText text={row.statement} />
                </div>

                <p className="text-sm">
                  Ответ: <b>{row.answer}</b>
                </p>

                {row.solution && (
                  <details className="text-sm">
                    <summary className="muted cursor-pointer">Решение автора</summary>
                    <div className="mt-2">
                      <MathText text={row.solution} />
                    </div>
                  </details>
                )}

                {row.status === "pending" ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      className="btn text-sm"
                      onClick={() => approve(row.id)}
                      disabled={busy === row.id}
                    >
                      <Check size={15} /> В банк
                    </button>
                    <button
                      className="btn-ghost text-sm"
                      onClick={() => reject(row.id)}
                      disabled={busy === row.id}
                    >
                      <X size={15} /> Отклонить
                    </button>
                  </div>
                ) : (
                  <p className="muted text-sm">
                    {row.status === "approved" ? (
                      <>
                        Взято в банк
                        {row.task_id && (
                          <>
                            {" — "}
                            <Link className="underline" href={`/app/admin?task=${row.task_id}`}>
                              открыть задачу
                            </Link>
                          </>
                        )}
                      </>
                    ) : (
                      `Отклонено${row.moderator_note ? `: ${row.moderator_note}` : ""}`
                    )}
                  </p>
                )}
              </article>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
