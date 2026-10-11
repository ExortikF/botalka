"use client";

import { useEffect, useState } from "react";
import { Check, Clock, Lightbulb, X } from "lucide-react";
import { api } from "@/lib/api";
import MathText from "../../Math";

type Suggestion = {
  id: number;
  number: number;
  statement: string;
  answer: string;
  status: "pending" | "approved" | "rejected";
  moderator_note: string | null;
  created_at: string;
};

const STATUS = {
  pending: { label: "на проверке", color: "var(--n-700)", icon: Clock },
  approved: { label: "взяли в банк", color: "var(--accent-700)", icon: Check },
  rejected: { label: "не подошла", color: "var(--accent-2)", icon: X },
};

const REWARD = 50;

export default function SuggestPage() {
  const [mine, setMine] = useState<Suggestion[]>([]);
  const [number, setNumber] = useState(1);
  const [statement, setStatement] = useState("");
  const [answer, setAnswer] = useState("");
  const [solution, setSolution] = useState("");
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  function load() {
    api<Suggestion[]>("/api/suggestions")
      .then(setMine)
      .catch(() => setMine([]));
  }

  useEffect(load, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api<Suggestion>("/api/suggestions", {
        method: "POST",
        body: JSON.stringify({
          number,
          statement,
          answer,
          solution: solution || null,
          source: source || null,
        }),
      });
      setStatement("");
      setAnswer("");
      setSolution("");
      setSource("");
      setSent(true);
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <header className="flex items-start gap-3">
        <Lightbulb size={22} style={{ color: "var(--accent-2)" }} />
        <div>
          <h1 className="page-title">Предложить свою задачу</h1>
          <p className="page-subtitle">
            Встретил хорошую задачу в варианте или придумал сам — пришли сюда. Мы
            проверим ответ и добавим в банк, а за принятую задачу начислим {REWARD} монет.
          </p>
        </div>
      </header>

      <form className="card space-y-5 p-7" onSubmit={submit} noValidate>
        <label className="block">
          <span className="eyebrow">Номер задания</span>
          <input
            className="input mt-1.5"
            style={{ width: "6rem" }}
            type="number"
            min={1}
            max={19}
            value={number}
            onChange={(e) => setNumber(Number(e.target.value))}
            required
          />
        </label>

        <label className="block">
          <span className="eyebrow">Условие</span>
          <textarea
            className="input mt-1.5 min-h-32 w-full"
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            placeholder="Формулы можно писать в TeX: $\frac{3}{4}$"
            required
          />
        </label>

        {statement.length > 0 && (
          <div className="rounded-xl p-4" style={{ background: "var(--surface)" }}>
            <p className="eyebrow mb-2">Как это увидит решающий</p>
            <MathText text={statement} />
          </div>
        )}

        <div className="grid gap-5 sm:grid-cols-2">
          <label className="block">
            <span className="eyebrow">Ответ</span>
            <input
              className="input mt-1.5 w-full"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="число, как в бланке"
              required
            />
          </label>

          <label className="block">
            <span className="eyebrow">Откуда задача</span>
            <input
              className="input mt-1.5 w-full"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="например: ЕГЭ 2024, вариант 12"
            />
          </label>
        </div>

        <label className="block">
          <span className="eyebrow">Решение (не обязательно)</span>
          <textarea
            className="input mt-1.5 min-h-24 w-full"
            value={solution}
            onChange={(e) => setSolution(e.target.value)}
            placeholder="Как решать — так задачу примут быстрее"
          />
        </label>

        <div className="flex flex-wrap items-center gap-4">
          <button className="btn" disabled={busy}>
            {busy ? "Отправляем…" : "Отправить на проверку"}
          </button>
          {sent && !error && (
            <span className="text-sm" style={{ color: "var(--accent-700)" }}>
              Отправлено — задача ушла на проверку
            </span>
          )}
          {error && (
            <span className="text-sm" style={{ color: "var(--accent-2)" }}>
              {error}
            </span>
          )}
        </div>
      </form>

      {mine.length > 0 && (
        <section className="space-y-3">
          <h2 className="section-title">Что я присылал</h2>
          <ul className="space-y-2">
            {mine.map((row) => {
              const state = STATUS[row.status];
              const Icon = state.icon;
              return (
                <li key={row.id} className="card flex items-start gap-3 p-4">
                  <Icon size={16} className="mt-1 shrink-0" style={{ color: state.color }} />
                  <span className="min-w-0 flex-1">
                    <span className="muted text-xs">№{row.number}</span>
                    <span className="mt-0.5 block truncate">{row.statement}</span>
                    {row.moderator_note && (
                      <span className="muted mt-1 block text-sm">{row.moderator_note}</span>
                    )}
                  </span>
                  <span className="shrink-0 text-sm" style={{ color: state.color }}>
                    {state.label}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
