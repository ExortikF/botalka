"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, Check, Layers, Lock, Target } from "lucide-react";
import {
  getStats,
  getSubjects,
  getTaskTypes,
  type StatsRow,
  type Subject,
  type TaskType,
} from "@/lib/api";

const LENGTHS = [5, 10, 15, 20];

export default function QuizBuilder() {
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subject, setSubject] = useState<string>("math_prof");
  const [types, setTypes] = useState<TaskType[]>([]);
  const [stats, setStats] = useState<StatsRow[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [length, setLength] = useState(10);

  useEffect(() => {
    getSubjects().then(setSubjects).catch(() => setSubjects([]));
    getStats().then(setStats).catch(() => setStats([]));
  }, []);

  useEffect(() => {
    setSelected([]);
    getTaskTypes(subject).then(setTypes).catch(() => setTypes([]));
  }, [subject]);

  const statsByNumber = new Map(stats.map((s) => [s.task_type_number, s]));
  const available = types.filter((t) => t.tasks_count > 0);
  const pool = types
    .filter((t) => selected.length === 0 || selected.includes(t.id))
    .reduce((sum, t) => sum + t.tasks_count, 0);

  function toggle(id: number) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function start(params: { preset?: "weak" | "mistakes" } = {}) {
    const query = new URLSearchParams({ subject, length: String(length) });
    if (params.preset) query.set("preset", params.preset);
    else if (selected.length) query.set("types", selected.join(","));
    router.push(`/app/quiz/run?${query}`);
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl">Квизы</h1>
        <p className="muted mt-2">
          Выбери предмет, отметь номера заданий — или собери квиз из нескольких сразу.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="eyebrow">Предмет</h2>
        <ul className="grid gap-3 sm:grid-cols-3">
          {subjects.map((s) => {
            const active = s.slug === subject;
            return (
              <li key={s.slug}>
                <button
                  disabled={!s.available}
                  onClick={() => s.available && setSubject(s.slug)}
                  className="card w-full p-5 text-left transition disabled:cursor-default"
                  style={{
                    borderColor: active ? "var(--accent)" : "var(--divider)",
                    background: active ? "var(--accent-100)" : "var(--card)",
                    opacity: s.available ? 1 : 0.55,
                  }}
                >
                  <span className="flex items-center justify-between">
                    <span className="font-medium">{s.title}</span>
                    {active ? (
                      <Check size={16} style={{ color: "var(--accent)" }} />
                    ) : !s.available ? (
                      <Lock size={14} className="muted" />
                    ) : null}
                  </span>
                  <span className="muted mt-2 block text-sm">
                    {s.available
                      ? `${s.tasks_count} задач · ${s.types_count} номеров${
                          s.solved ? ` · решено ${s.solved}` : ""
                        }`
                      : "скоро"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="eyebrow">Быстрый старт</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <Preset
            icon={<Layers size={18} />}
            title="Вся часть 1"
            text="Случайные задачи из всех номеров"
            onClick={() => {
              setSelected([]);
              start();
            }}
          />
          <Preset
            icon={<AlertTriangle size={18} />}
            title="Слабые темы"
            text="Номера, где процент ниже всего"
            accent
            onClick={() => start({ preset: "weak" })}
          />
          <Preset
            icon={<Target size={18} />}
            title="Работа над ошибками"
            text="Задачи, где ты ошибался и ещё не решил"
            accent
            onClick={() => start({ preset: "mistakes" })}
          />
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="eyebrow">Собрать свой квиз</h2>
          <span className="muted text-sm">
            {selected.length === 0
              ? "ничего не отмечено — возьмём все номера"
              : `отмечено номеров: ${selected.length}`}
          </span>
        </div>

        <ul className="grid gap-2 sm:grid-cols-2">
          {available.map((type) => {
            const stat = statsByNumber.get(type.number);
            const percent = stat?.total ? Math.round((stat.correct / stat.total) * 100) : null;
            const checked = selected.includes(type.id);
            return (
              <li key={type.id}>
                <label
                  className="card flex cursor-pointer items-center gap-3 p-4 transition"
                  style={{
                    borderColor: checked ? "var(--accent)" : "var(--divider)",
                    background: checked ? "var(--accent-100)" : "var(--card)",
                  }}
                >
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={checked}
                    onChange={() => toggle(type.id)}
                  />
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md border"
                    style={{
                      borderColor: checked ? "var(--accent)" : "var(--divider)",
                      background: checked ? "var(--accent)" : "transparent",
                      color: "#fff",
                    }}
                  >
                    {checked && <Check size={13} />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="muted mr-2 text-sm">№{type.number}</span>
                    {type.title}
                  </span>
                  <span className="shrink-0 text-sm">
                    {percent !== null ? (
                      <span style={{ color: percent >= 70 ? "var(--accent)" : "var(--accent-2)" }}>
                        {percent}%
                      </span>
                    ) : (
                      <span className="muted">{type.tasks_count} зад.</span>
                    )}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      </section>

      <section
        className="card flex flex-wrap items-center justify-between gap-4 p-5"
        style={{ position: "sticky", bottom: "1rem", boxShadow: "var(--shadow-md)" }}
      >
        <div className="flex items-center gap-2">
          <span className="muted text-sm">Задач в квизе:</span>
          {LENGTHS.map((n) => (
            <button
              key={n}
              onClick={() => setLength(n)}
              className={`pill ${length === n ? "pill-active" : "pill-idle"}`}
            >
              {n}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-4">
          {pool < length && (
            <span className="muted text-sm">
              в выбранном всего {pool} задач — квиз будет короче
            </span>
          )}
          <button className="btn" onClick={() => start()} disabled={pool === 0}>
            Начать квиз
          </button>
        </div>
      </section>
    </div>
  );
}

function Preset({
  icon,
  title,
  text,
  onClick,
  accent,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
  onClick: () => void;
  accent?: boolean;
}) {
  return (
    <button className="card p-5 text-left transition hover:shadow-[var(--shadow-sm)]" onClick={onClick}>
      <span style={{ color: accent ? "var(--accent-2)" : "var(--accent)" }}>{icon}</span>
      <span className="mt-2 block font-medium">{title}</span>
      <span className="muted mt-1 block text-sm">{text}</span>
    </button>
  );
}
