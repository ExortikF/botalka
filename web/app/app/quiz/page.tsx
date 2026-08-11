"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, Check, Layers, Lock, Minus, Plus, Target } from "lucide-react";
import {
  getStats,
  getSubjects,
  getTaskTypes,
  type StatsRow,
  type Subject,
  type TaskType,
} from "@/lib/api";
import { plural } from "@/lib/exam";

/** Сколько задач берём из темы по умолчанию, когда её только что отметили. */
const DEFAULT_PER_TYPE = 5;

export default function QuizBuilder() {
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subject, setSubject] = useState("math_prof");
  const [types, setTypes] = useState<TaskType[]>([]);
  const [stats, setStats] = useState<StatsRow[]>([]);
  /** id номера → сколько задач из него взять. Нет ключа — тема не выбрана. */
  const [picked, setPicked] = useState<Record<number, number>>({});

  useEffect(() => {
    getSubjects().then(setSubjects).catch(() => setSubjects([]));
    getStats().then(setStats).catch(() => setStats([]));
  }, []);

  useEffect(() => {
    setPicked({});
    getTaskTypes(subject).then(setTypes).catch(() => setTypes([]));
  }, [subject]);

  const statsByNumber = new Map(stats.map((s) => [s.task_type_number, s]));
  const available = types.filter((t) => t.tasks_count > 0);
  const chosen = Object.entries(picked).map(([id, count]) => ({
    task_type_id: Number(id),
    count,
  }));
  const totalTasks = chosen.reduce((sum, c) => sum + c.count, 0);

  function toggle(type: TaskType) {
    setPicked((prev) => {
      const next = { ...prev };
      if (next[type.id]) delete next[type.id];
      else next[type.id] = Math.min(DEFAULT_PER_TYPE, type.tasks_count);
      return next;
    });
  }

  function setCount(type: TaskType, delta: number) {
    setPicked((prev) => {
      const current = prev[type.id] ?? 0;
      const next = Math.max(1, Math.min(current + delta, type.tasks_count));
      return { ...prev, [type.id]: next };
    });
  }

  function startPreset(preset: "weak" | "mistakes" | "unsolved" | null) {
    const query = new URLSearchParams({ subject, length: "10" });
    if (preset) query.set("preset", preset);
    router.push(`/app/quiz/run?${query}`);
  }

  function startPicked() {
    const query = new URLSearchParams({
      subject,
      selection: chosen.map((c) => `${c.task_type_id}:${c.count}`).join(","),
    });
    router.push(`/app/quiz/run?${query}`);
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl">Квизы</h1>
        <p className="muted mt-2">
          Выбери предмет и темы. В каждой теме стрелочками задаётся, сколько задач из неё взять.
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
            text="Десять случайных задач из всех номеров"
            onClick={() => startPreset(null)}
          />
          <Preset
            icon={<AlertTriangle size={18} />}
            title="Слабые темы"
            text="Номера, где процент ниже всего"
            accent
            onClick={() => startPreset("weak")}
          />
          <Preset
            icon={<Target size={18} />}
            title="Работа над ошибками"
            text="Задачи, где ты ошибался и ещё не решил"
            accent
            onClick={() => startPreset("mistakes")}
          />
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="eyebrow">Собрать свой квиз</h2>
          <span className="muted text-sm">
            {chosen.length === 0
              ? "тема не выбрана"
              : `${chosen.length} ${plural(chosen.length, "тема", "темы", "тем")} · ${totalTasks} ${plural(
                  totalTasks,
                  "задача",
                  "задачи",
                  "задач",
                )}`}
          </span>
        </div>

        <ul className="grid gap-2 sm:grid-cols-2">
          {available.map((type) => {
            const stat = statsByNumber.get(type.number);
            const percent = stat?.total ? Math.round((stat.correct / stat.total) * 100) : null;
            const count = picked[type.id];
            const checked = count !== undefined;

            return (
              <li key={type.id}>
                <div
                  className="card flex items-center gap-3 p-4 transition"
                  style={{
                    borderColor: checked ? "var(--accent)" : "var(--divider)",
                    background: checked ? "var(--accent-100)" : "var(--card)",
                  }}
                >
                  <button
                    onClick={() => toggle(type)}
                    className="flex min-w-0 flex-1 items-center gap-3 text-left"
                    aria-pressed={checked}
                  >
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
                    <span className="min-w-0">
                      <span className="muted mr-2 text-sm">№{type.number}</span>
                      {type.title}
                      <span className="muted block text-xs">
                        {type.tasks_count} задач в банке
                        {percent !== null && ` · сейчас ${percent}% верно`}
                      </span>
                    </span>
                  </button>

                  {checked ? (
                    <span className="flex shrink-0 items-center gap-1">
                      <Stepper
                        label="Меньше задач"
                        disabled={count <= 1}
                        onClick={() => setCount(type, -1)}
                      >
                        <Minus size={14} />
                      </Stepper>
                      <span className="h w-7 text-center text-lg">{count}</span>
                      <Stepper
                        label="Больше задач"
                        disabled={count >= type.tasks_count}
                        onClick={() => setCount(type, 1)}
                      >
                        <Plus size={14} />
                      </Stepper>
                    </span>
                  ) : (
                    <span className="muted shrink-0 text-sm">
                      {percent !== null ? `${percent}%` : `${type.tasks_count} зад.`}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      <section
        className="card flex flex-wrap items-center justify-between gap-4 p-5"
        style={{ position: "sticky", bottom: "1rem", boxShadow: "var(--shadow-md)" }}
      >
        <span className="muted text-sm">
          {chosen.length === 0
            ? "Отметь темы выше — или запусти быстрый старт"
            : `В квизе будет ${totalTasks} ${plural(totalTasks, "задача", "задачи", "задач")}`}
        </span>
        <button className="btn" onClick={startPicked} disabled={chosen.length === 0}>
          Начать квиз
        </button>
      </section>
    </div>
  );
}

function Stepper({
  children,
  onClick,
  disabled,
  label,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="flex h-7 w-7 items-center justify-center rounded-lg border transition disabled:opacity-30"
      style={{ borderColor: "var(--divider)", background: "var(--card)" }}
    >
      {children}
    </button>
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
    <button
      className="card p-5 text-left transition hover:shadow-[var(--shadow-sm)]"
      onClick={onClick}
    >
      <span style={{ color: accent ? "var(--accent-2)" : "var(--accent)" }}>{icon}</span>
      <span className="mt-2 block font-medium">{title}</span>
      <span className="muted mt-1 block text-sm">{text}</span>
    </button>
  );
}
