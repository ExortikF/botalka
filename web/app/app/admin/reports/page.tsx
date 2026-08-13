"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, X } from "lucide-react";
import MathText from "../../../Math";
import { api } from "@/lib/api";

type Report = {
  id: number;
  task_id: number;
  task_number: number;
  statement: string;
  correct_answer: string;
  message: string;
  given_answer: string | null;
  status: string;
  created_at: string;
};

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[] | null>(null);
  const [onlyNew, setOnlyNew] = useState(true);

  const load = useCallback(() => {
    api<Report[]>(`/api/admin/reports?only_new=${onlyNew}`)
      .then(setReports)
      .catch(() => setReports([]));
  }, [onlyNew]);

  useEffect(load, [load]);

  async function act(id: number, action: "resolve" | "decline") {
    await api(`/api/admin/reports/${id}/${action}`, { method: "POST" });
    load();
  }

  return (
    <div className="page">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Жалобы на задачи</h1>
          <p className="muted mt-1 text-sm">
            Приходят из кнопки «Нашли ошибку?» под условием. Задача при этом
            остаётся в выдаче — снимать её решаешь ты.
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
        {onlyNew ? "Только новые" : "Все жалобы"}
      </button>

      {reports === null ? (
        <p className="muted">Загрузка…</p>
      ) : reports.length === 0 ? (
        <p className="muted">Жалоб нет.</p>
      ) : (
        <ul className="space-y-3">
          {reports.map((report) => (
            <li key={report.id}>
              <article className="card space-y-3 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <span
                    className="rounded-lg px-2.5 py-1 text-xs font-medium"
                    style={{
                      background: "var(--accent-100)",
                      color: "var(--accent-700)",
                    }}
                  >
                    № {report.task_number}
                  </span>
                  <span className="muted text-xs">
                    {new Date(report.created_at).toLocaleString("ru", {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                <MathText
                  className="block text-sm leading-relaxed"
                  text={report.statement}
                />

                <p
                  className="rounded-xl p-3 text-sm"
                  style={{ background: "var(--accent-2-100)" }}
                >
                  {report.message}
                </p>

                <p className="muted text-xs">
                  Верный ответ в банке: {report.correct_answer}
                  {report.given_answer &&
                    ` · ученик вводил: ${report.given_answer}`}
                </p>

                {report.status === "new" ? (
                  <div className="flex gap-2">
                    <Link
                      className="btn-ghost text-sm"
                      href={`/app/admin?task=${report.task_id}`}
                    >
                      Открыть задачу
                    </Link>
                    <button
                      className="btn text-sm"
                      onClick={() => act(report.id, "resolve")}
                    >
                      <Check size={15} /> Исправлено
                    </button>
                    <button
                      className="btn-ghost text-sm"
                      onClick={() => act(report.id, "decline")}
                    >
                      <X size={15} /> Отклонить
                    </button>
                  </div>
                ) : (
                  <p className="muted text-sm">
                    {report.status === "resolved" ? "Исправлено" : "Отклонено"}
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
