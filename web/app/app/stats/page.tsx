"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { plural } from "@/lib/exam";

type MonthRow = {
  month: string;
  solved: number;
  correct: number;
  days_active: number;
};
type HourRow = { hour: number; attempts: number };
type TypeRow = {
  number: number;
  title: string;
  total: number;
  correct: number;
  accuracy: number;
  avg_seconds: number;
};

type StatsYear = {
  days_total: number;
  attempts_total: number;
  correct_total: number;
  accuracy: number;
  minutes_total: number;
  avg_seconds: number;
  best_day: { day: string; solved: number } | null;
  quizzes: number;
  mocks: number;
  duels: number;
  forecast_secondary: number;
  months: MonthRow[];
  hours: HourRow[];
  by_type: TypeRow[];
};

const MONTHS = [
  "янв",
  "фев",
  "мар",
  "апр",
  "май",
  "июн",
  "июл",
  "авг",
  "сен",
  "окт",
  "ноя",
  "дек",
];

function monthLabel(key: string): string {
  const [, month] = key.split("-");
  return MONTHS[Number(month) - 1] ?? key;
}

export default function StatsPage() {
  const [stats, setStats] = useState<StatsYear | null>(null);

  useEffect(() => {
    api<StatsYear>("/api/stats/year")
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  if (!stats) return <p className="muted">Загрузка…</p>;

  const maxMonth = Math.max(1, ...stats.months.map((m) => m.solved));
  const maxHour = Math.max(1, ...stats.hours.map((h) => h.attempts));
  const worst = [...stats.by_type]
    .filter((t) => t.total >= 3)
    .sort((a, b) => a.accuracy - b.accuracy);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl">Статистика за год</h1>
      </header>

      <section
        className="relative overflow-hidden p-8 text-white"
        style={{
          background: "var(--accent)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute -right-16 -top-20 h-72 w-72 rounded-full opacity-30"
          style={{ background: "var(--accent-2)" }}
        />
        <div className="relative">
          <p className="text-xs font-semibold uppercase tracking-widest opacity-80">
            Прогноз по текущей точности
          </p>
          <p className="h mt-2 text-6xl">{stats.forecast_secondary}</p>
          <p className="mt-2 max-w-lg opacity-90">
            Столько тестовых баллов дала бы часть 1, если решать её с твоей
            нынешней точностью {stats.accuracy}%. Это оценка, а не обещание:
            настоящий экзамен сложнее домашнего квиза.
          </p>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <Metric
          value={stats.days_total}
          label={plural(
            stats.days_total,
            "день с занятиями",
            "дня с занятиями",
            "дней с занятиями",
          )}
        />
        <Metric value={stats.attempts_total} label="ответов всего" />
        <Metric value={`${stats.accuracy}%`} label="верных" />
        <Metric value={stats.minutes_total} label="минут за решением" />
        <Metric value={stats.quizzes} label="квизов пройдено" />
        <Metric value={stats.mocks} label="пробников сдано" />
        <Metric value={stats.duels} label="дуэлей сыграно" />
        <Metric
          value={stats.avg_seconds ? `${stats.avg_seconds} с` : "—"}
          label="в среднем на задачу"
        />
      </section>

      {stats.best_day && (
        <p className="muted text-sm">
          Лучший день:{" "}
          {new Date(stats.best_day.day).toLocaleDateString("ru", {
            day: "numeric",
            month: "long",
          })}{" "}
          — {stats.best_day.solved}{" "}
          {plural(stats.best_day.solved, "ответ", "ответа", "ответов")}.
        </p>
      )}

      <section className="card p-6">
        <h2 className="mb-4 text-xl">По месяцам</h2>
        {stats.months.length === 0 ? (
          <p className="muted text-sm">Пока пусто — реши первый квиз.</p>
        ) : (
          <div className="flex items-end gap-2" style={{ height: 160 }}>
            {stats.months.map((month) => (
              <div
                key={month.month}
                className="flex flex-1 flex-col items-center gap-2"
              >
                <span className="muted text-xs">{month.solved}</span>
                <div
                  className="w-full rounded-t-lg"
                  style={{
                    height: `${(month.solved / maxMonth) * 110}px`,
                    background: "var(--accent)",
                    minHeight: 4,
                  }}
                  title={`${month.correct} верных из ${month.solved}, дней: ${month.days_active}`}
                />
                <span className="muted text-xs">{monthLabel(month.month)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card p-6">
        <h2 className="mb-1 text-xl">Когда ты решаешь</h2>
        <p className="muted mb-4 text-sm">По часам, время московское</p>
        <div className="flex items-end gap-1" style={{ height: 110 }}>
          {stats.hours.map((hour) => (
            <div
              key={hour.hour}
              className="flex flex-1 flex-col items-center gap-1"
            >
              <div
                className="w-full rounded-t"
                style={{
                  height: `${(hour.attempts / maxHour) * 80}px`,
                  background: hour.attempts
                    ? "var(--accent-300)"
                    : "var(--surface)",
                  minHeight: 3,
                }}
                title={`${hour.hour}:00 — ${hour.attempts}`}
              />
              {hour.hour % 6 === 0 && (
                <span className="muted text-[10px]">{hour.hour}</span>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="card p-6">
        <h2 className="mb-4 text-xl">По номерам заданий</h2>
        {stats.by_type.length === 0 ? (
          <p className="muted text-sm">Данных пока нет.</p>
        ) : (
          <ul className="space-y-2">
            {stats.by_type.map((row) => (
              <li key={row.number} className="flex items-center gap-3 text-sm">
                <span className="muted w-10 shrink-0">№{row.number}</span>
                <span className="w-44 shrink-0 truncate">{row.title}</span>
                <span
                  className="h-2 flex-1 overflow-hidden rounded-full"
                  style={{ background: "var(--surface)" }}
                >
                  <span
                    className="block h-full rounded-full"
                    style={{
                      width: `${row.accuracy}%`,
                      background:
                        row.accuracy >= 70
                          ? "#1f9d55"
                          : row.accuracy >= 40
                            ? "#c98a00"
                            : "var(--accent-2)",
                    }}
                  />
                </span>
                <span className="w-12 shrink-0 text-right">
                  {row.accuracy}%
                </span>
                <span className="muted w-20 shrink-0 text-right">
                  {row.avg_seconds ? `${row.avg_seconds} с` : "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {worst.length > 0 && (
        <section className="card p-6">
          <h2 className="text-xl">Что тянет вниз</h2>
          <p className="muted mt-1 text-sm">
            Номера с худшей точностью при трёх и более попытках
          </p>
          <ul className="mt-3 space-y-1 text-sm">
            {worst.slice(0, 3).map((row) => (
              <li key={row.number}>
                <b>№{row.number}</b> {row.title} — {row.accuracy}% из{" "}
                {row.total}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Metric({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="card p-5">
      <p className="h text-3xl">{value}</p>
      <p className="muted mt-1 text-sm leading-snug">{label}</p>
    </div>
  );
}
