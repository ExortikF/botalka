"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, Check, Lock, Minus, Plus, Shuffle, Target } from "lucide-react";
import {
  getStats,
  getSubjects,
  getTaskTypes,
  type StatsRow,
  type Subject,
  type TaskType,
} from "@/lib/api";
import { plural } from "@/lib/exam";

/** Полосы сложности: цвет и подпись. Совпадают с DIFFICULTY_BANDS на бэкенде. */
const BANDS = [
  { key: "easy", label: "лёгкие", color: "var(--success)", bg: "#e8f6ee" },
  { key: "medium", label: "средние", color: "var(--gold)", bg: "var(--gold-bg)" },
  { key: "hard", label: "сложные", color: "var(--accent-2)", bg: "#ffe9f0" },
] as const;

type Band = (typeof BANDS)[number]["key"];
type Pick = Record<Band, number>;

const EMPTY: Pick = { easy: 0, medium: 0, hard: 0 };

export default function QuizBuilder() {
  const router = useRouter();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subject, setSubject] = useState("math_prof");
  const [types, setTypes] = useState<TaskType[]>([]);
  const [stats, setStats] = useState<StatsRow[]>([]);
  /** id номера → сколько задач каждой сложности взять. */
  const [picked, setPicked] = useState<Record<number, Pick>>({});

  useEffect(() => {
    getSubjects()
      .then(setSubjects)
      .catch(() => setSubjects([]));
    getStats()
      .then(setStats)
      .catch(() => setStats([]));
  }, []);

  useEffect(() => {
    setPicked({});
    getTaskTypes(subject)
      .then(setTypes)
      .catch(() => setTypes([]));
  }, [subject]);

  const statsByNumber = new Map(stats.map((s) => [s.task_type_number, s]));
  const chosen = Object.entries(picked)
    .map(([id, pick]) => ({ task_type_id: Number(id), ...pick }))
    .filter((p) => p.easy + p.medium + p.hard > 0);
  const totalTasks = chosen.reduce(
    (sum, p) => sum + p.easy + p.medium + p.hard,
    0,
  );

  function bump(type: TaskType, band: Band, delta: number) {
    const max = type[band];
    setPicked((prev) => {
      const current = prev[type.id] ?? EMPTY;
      const next = Math.max(0, Math.min(current[band] + delta, max));
      const updated = { ...current, [band]: next };
      if (updated.easy + updated.medium + updated.hard === 0) {
        const copy = { ...prev };
        delete copy[type.id];
        return copy;
      }
      return { ...prev, [type.id]: updated };
    });
  }

  /** Десять случайных задач по всему банку — вход в один клик. */
  function startRandom() {
    router.push(`/app/quiz/run?subject=${subject}&length=10`);
  }

  function startPreset(preset: "weak" | "mistakes") {
    router.push(`/app/quiz/run?subject=${subject}&length=10&preset=${preset}`);
  }

  function startPicked() {
    const selection = chosen
      .map((p) => `${p.task_type_id}:${p.easy}:${p.medium}:${p.hard}`)
      .join(",");
    router.push(`/app/quiz/run?subject=${subject}&bands=${selection}`);
  }

  return (
    <div className="page">
      <header>
        <h1 className="page-title">Квизы</h1>
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
                    {s.available ? `${s.tasks_count} задач` : "скоро"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      {/* Быстрый вход: набирать задачи стрелочками ради «просто порешать»
          — слишком долго для главного действия на странице. */}
      <section
        className="card flex flex-wrap items-center justify-between gap-4"
        style={{ padding: "22px 24px" }}
      >
        <div className="min-w-0">
          <h2 className="section-title">Просто порешать</h2>
          <p className="muted mt-1 text-sm">
            Десять случайных задач по всему банку — набирать ничего не нужно.
          </p>
        </div>
        <button className="btn" onClick={startRandom}>
          <Shuffle size={16} /> Случайный квиз
        </button>
      </section>

      <section className="space-y-3">
        <h2 className="eyebrow">Разобрать проблемные места</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Preset
            icon={<Target size={18} />}
            title="Работа над ошибками"
            text="Задачи, где ты ошибался и ещё не решил верно"
            onClick={() => startPreset("mistakes")}
          />
          <Preset
            icon={<AlertTriangle size={18} />}
            title="Слабые темы"
            text="Номера, где процент верных ниже всего"
            onClick={() => startPreset("weak")}
          />
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="eyebrow">Собрать свой квиз</h2>
          <div className="flex items-center gap-3 text-xs">
            {BANDS.map((band) => (
              <span key={band.key} className="flex items-center gap-1.5">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ background: band.color }}
                />
                {band.label}
              </span>
            ))}
          </div>
        </div>

        <ul className="space-y-2">
          {types.map((type) => {
            const stat = statsByNumber.get(type.number);
            const percent = stat?.total
              ? Math.round((stat.correct / stat.total) * 100)
              : null;
            const pick = picked[type.id] ?? EMPTY;
            const chosenHere = pick.easy + pick.medium + pick.hard;
            const empty = type.tasks_count === 0;

            return (
              <li key={type.id}>
                <div
                  className="card flex flex-wrap items-center gap-4 p-4 transition"
                  style={{
                    borderColor: chosenHere
                      ? "var(--accent)"
                      : "var(--divider)",
                    background: chosenHere
                      ? "var(--accent-100)"
                      : "var(--card)",
                    opacity: empty ? 0.55 : 1,
                  }}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block">
                      <span className="muted mr-2 text-sm">№{type.number}</span>
                      {type.title}
                    </span>
                    <span className="muted text-xs">
                      {empty ? (
                        "задач пока нет"
                      ) : (
                        <>
                          {type.tasks_count} задач
                          {percent !== null
                            ? ` · сейчас ${percent}% верно`
                            : " · ещё не решал"}
                        </>
                      )}
                    </span>
                  </span>

                  {!empty && (
                    <span className="flex flex-wrap items-center gap-3">
                      {BANDS.map((band) => (
                        <Stepper
                          key={band.key}
                          band={band}
                          value={pick[band.key]}
                          max={type[band.key]}
                          onChange={(delta) => bump(type, band.key, delta)}
                        />
                      ))}
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
        style={{
          position: "sticky",
          bottom: "1rem",
          boxShadow: "var(--shadow-md)",
        }}
      >
        <span className="muted text-sm">
          {totalTasks === 0
            ? "Добавь задачи стрелочками — по сложности"
            : `В квизе будет ${totalTasks} ${plural(totalTasks, "задача", "задачи", "задач")}`}
        </span>
        <button
          className="btn"
          onClick={startPicked}
          disabled={totalTasks === 0}
        >
          Начать квиз
        </button>
      </section>
    </div>
  );
}

function Stepper({
  band,
  value,
  max,
  onChange,
}: {
  band: (typeof BANDS)[number];
  value: number;
  max: number;
  onChange: (delta: number) => void;
}) {
  const disabled = max === 0;
  return (
    <span
      className="flex items-center gap-1 rounded-xl px-1.5 py-1"
      style={{
        background: value > 0 ? band.bg : "var(--surface)",
        opacity: disabled ? 0.4 : 1,
      }}
      title={`${band.label}: доступно ${max}`}
    >
      <button
        onClick={() => onChange(-1)}
        disabled={disabled || value === 0}
        aria-label={`Меньше: ${band.label}`}
        className="flex h-6 w-6 items-center justify-center rounded-lg disabled:opacity-30"
      >
        <Minus size={13} />
      </button>
      <span
        className="h w-6 text-center text-base"
        style={{ color: value > 0 ? band.color : "var(--n-500)" }}
      >
        {value}
      </span>
      <button
        onClick={() => onChange(1)}
        disabled={disabled || value >= max}
        aria-label={`Больше: ${band.label}`}
        className="flex h-6 w-6 items-center justify-center rounded-lg disabled:opacity-30"
      >
        <Plus size={13} />
      </button>
    </span>
  );
}

function Preset({
  icon,
  title,
  text,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
  onClick: () => void;
}) {
  return (
    <button
      className="card p-5 text-left transition hover:shadow-[var(--shadow-sm)]"
      onClick={onClick}
    >
      <span style={{ color: "var(--accent-2)" }}>{icon}</span>
      <span className="mt-2 block font-medium">{title}</span>
      <span className="muted mt-1 block text-sm">{text}</span>
    </button>
  );
}
