"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Eye, EyeOff, Flag, Plus, Trash2, Trophy } from "lucide-react";
import { api } from "@/lib/api";
import TournamentForm from "./TournamentForm";

type Row = {
  id: number;
  title: string;
  status: string;
  state: string;
  starts_at: string;
  ends_at: string;
  participants: number;
  rules: number;
  awarded: boolean;
};

const STATUS_LABEL: Record<string, string> = {
  draft: "черновик",
  published: "опубликован",
  finished: "завершён",
};

export default function AdminTournamentsPage() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const load = useCallback(() => {
    api<Row[]>("/api/admin/tournaments")
      .then(setRows)
      .catch(() => setRows([]));
  }, []);

  useEffect(load, [load]);

  async function act(id: number, path: string, confirmText?: string) {
    if (confirmText && !confirm(confirmText)) return;
    setBusy(id);
    setError("");
    setNote("");
    try {
      const res = await api<{ winners?: number; coins_total?: number; items_total?: number }>(
        `/api/admin/tournaments/${id}/${path}`,
        { method: "POST" },
      );
      if (path === "finish") {
        setNote(
          `Итоги подведены: участников ${res.winners}, выдано ${res.coins_total} монет и предметов ${res.items_total}.`,
        );
      }
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function remove(id: number) {
    if (!confirm("Удалить турнир? Настройки не восстановить.")) return;
    setBusy(id);
    try {
      await api(`/api/admin/tournaments/${id}`, { method: "DELETE" });
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (editing !== null)
    return (
      <TournamentForm
        id={editing === "new" ? null : editing}
        onClose={() => {
          setEditing(null);
          load();
        }}
      />
    );

  return (
    <div className="page">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Flag size={22} style={{ color: "var(--accent-2)" }} />
          <div>
            <h1 className="page-title">Турниры</h1>
            <p className="page-subtitle">
              Правила задаются здесь: событие, очки и потолок в день. Очки считаются
              из уже накопленных данных, поэтому таблица видна сразу после настройки
              — ещё до публикации.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link className="btn-ghost" href="/app/admin">
            <ArrowLeft size={15} /> К задачам
          </Link>
          <button className="btn" onClick={() => setEditing("new")}>
            <Plus size={16} /> Новый турнир
          </button>
        </div>
      </header>

      {error && (
        <p className="text-sm" style={{ color: "var(--accent-2)" }}>
          {error}
        </p>
      )}
      {note && (
        <p
          className="rounded-xl p-3 text-sm"
          style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
        >
          {note}
        </p>
      )}

      {rows === null ? (
        <p className="muted">Загрузка…</p>
      ) : rows.length === 0 ? (
        <p className="muted">Турниров пока нет.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((row) => (
            <li key={row.id}>
              <article className="card flex flex-wrap items-center gap-4 p-4">
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <b>{row.title}</b>
                    <span
                      className="rounded-full px-2 py-0.5 text-[0.6875rem] font-semibold"
                      style={{
                        background:
                          row.status === "published"
                            ? "var(--accent-100)"
                            : "var(--surface)",
                        color:
                          row.status === "published"
                            ? "var(--accent-700)"
                            : "var(--n-700)",
                      }}
                    >
                      {STATUS_LABEL[row.status] ?? row.status}
                    </span>
                    <span className="muted text-xs">{row.state}</span>
                  </span>
                  <span className="muted mt-0.5 block text-sm">
                    {formatDate(row.starts_at)} — {formatDate(row.ends_at)} МСК · позиций{" "}
                    {row.rules} · участников {row.participants}
                  </span>
                </span>

                <span className="flex flex-wrap gap-2">
                  <Link
                    className="btn-ghost text-sm"
                    href={`/app/tournaments/${row.id}`}
                  >
                    Как видит ученик
                  </Link>

                  {!row.awarded && (
                    <button
                      className="btn-ghost text-sm"
                      onClick={() => setEditing(row.id)}
                    >
                      Настроить
                    </button>
                  )}

                  {row.status === "draft" ? (
                    <button
                      className="btn text-sm"
                      onClick={() => act(row.id, "publish")}
                      disabled={busy === row.id}
                    >
                      <Eye size={14} /> Опубликовать
                    </button>
                  ) : row.status === "published" ? (
                    <>
                      <button
                        className="btn-ghost text-sm"
                        onClick={() => act(row.id, "hide")}
                        disabled={busy === row.id}
                      >
                        <EyeOff size={14} /> Скрыть
                      </button>
                      <button
                        className="btn btn-accent2 text-sm"
                        onClick={() =>
                          act(
                            row.id,
                            "finish",
                            "Подвести итоги и выдать награды? Отменить нельзя.",
                          )
                        }
                        disabled={busy === row.id}
                      >
                        <Trophy size={14} /> Итоги и награды
                      </button>
                    </>
                  ) : null}

                  {!row.awarded && (
                    <button
                      className="muted p-2"
                      title="Удалить"
                      onClick={() => remove(row.id)}
                      disabled={busy === row.id}
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </span>
              </article>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ru", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Moscow",
  });
}
