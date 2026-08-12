"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, X } from "lucide-react";
import { api } from "@/lib/api";

type Idea = {
  id: number;
  message: string;
  page: string | null;
  author: string;
  status: string;
  created_at: string;
};

export default function IdeasPage() {
  const [ideas, setIdeas] = useState<Idea[] | null>(null);
  const [onlyNew, setOnlyNew] = useState(true);

  const load = useCallback(() => {
    api<Idea[]>(`/api/admin/ideas?only_new=${onlyNew}`)
      .then(setIdeas)
      .catch(() => setIdeas([]));
  }, [onlyNew]);

  useEffect(load, [load]);

  async function act(id: number, action: "accept" | "decline") {
    await api(`/api/admin/ideas/${id}/${action}`, { method: "POST" });
    load();
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl">Идеи пользователей</h1>
          <p className="muted mt-1 text-sm">
            Приходят из кнопки «Есть идеи по улучшению сайта?» в боковом меню.
          </p>
        </div>
        <Link className="btn-ghost" href="/app/admin">
          <ArrowLeft size={15} /> К задачам
        </Link>
      </header>

      <button
        className={`pill ${onlyNew ? "pill-active" : "pill-idle"}`}
        style={{ border: "1px solid var(--divider)" }}
        onClick={() => setOnlyNew((v) => !v)}
      >
        {onlyNew ? "Только новые" : "Все идеи"}
      </button>

      {ideas === null ? (
        <p className="muted">Загрузка…</p>
      ) : ideas.length === 0 ? (
        <p className="muted">Идей пока нет.</p>
      ) : (
        <ul className="space-y-3">
          {ideas.map((idea) => (
            <li key={idea.id}>
              <article className="card space-y-3 p-5">
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <span className="font-medium">{idea.author}</span>
                  <span className="muted text-xs">
                    {idea.page && `${idea.page} · `}
                    {new Date(idea.created_at).toLocaleString("ru", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                <p className="rounded-xl p-3 text-sm" style={{ background: "var(--surface)" }}>
                  {idea.message}
                </p>

                {idea.status === "new" ? (
                  <div className="flex gap-2">
                    <button className="btn text-sm" onClick={() => act(idea.id, "accept")}>
                      <Check size={15} /> В работу
                    </button>
                    <button className="btn-ghost text-sm" onClick={() => act(idea.id, "decline")}>
                      <X size={15} /> Не берём
                    </button>
                  </div>
                ) : (
                  <p className="muted text-sm">
                    {idea.status === "accepted" ? "Взято в работу" : "Отклонено"}
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
