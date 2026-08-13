"use client";

import { useEffect, useState } from "react";
import {
  CalendarDays,
  Check,
  Target,
  Timer,
  TrendingUp,
} from "lucide-react";
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

/** Сетка тетрадного листа — та же, что на баннерах дуэлей. */
const GRID =
  "repeating-linear-gradient(0deg,rgba(255,255,255,.05) 0 1px,transparent 1px 28px)," +
  "repeating-linear-gradient(90deg,rgba(255,255,255,.05) 0 1px,transparent 1px 28px)";

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
  const lastMonth = stats.months[stats.months.length - 1]?.month;
  const worst = [...stats.by_type]
    .filter((t) => t.total >= 3)
    .sort((a, b) => a.accuracy - b.accuracy)
    .slice(0, 3);

  return (
    <div className="page">
      <header>
        <h1 className="page-title">Статистика за год</h1>
      </header>

      <section
        className="relative overflow-hidden text-white"
        style={{
          borderRadius: "var(--radius-lg)",
          padding: "32px 34px",
          backgroundImage: "linear-gradient(120deg,#0088b0,#0aa0c9 60%,#7c3aed)",
          boxShadow: "0 12px 32px rgba(0,136,176,.25)",
        }}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{ backgroundImage: GRID }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-24 h-[300px] w-[300px] rounded-full"
          style={{ background: "var(--accent-2)", opacity: 0.25 }}
        />

        <div className="relative flex flex-wrap items-center gap-7">
          <div>
            <span
              className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[11px] font-bold uppercase tracking-wider"
              style={{ background: "rgba(255,255,255,.2)" }}
            >
              <TrendingUp size={13} /> Прогноз по текущей точности
            </span>
            <p
              className="h mt-2.5"
              style={{ fontSize: 64, fontWeight: 800, lineHeight: 1 }}
            >
              {stats.forecast_secondary}
            </p>
          </div>
          <p
            className="min-w-[260px] max-w-[480px] flex-1 text-sm leading-relaxed"
            style={{ opacity: 0.92 }}
          >
            Столько тестовых баллов дала бы часть 1, если решать её с твоей
            нынешней точностью {stats.accuracy}%. Это оценка, а не обещание:
            настоящий экзамен сложнее домашнего квиза.
          </p>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <IconTile
          icon={<CalendarDays size={17} style={{ color: "var(--accent-700)" }} />}
          iconBg="var(--accent-100)"
          value={stats.days_total}
          label={plural(
            stats.days_total,
            "день с занятиями",
            "дня с занятиями",
            "дней с занятиями",
          )}
        />
        <IconTile
          icon={<Target size={17} style={{ color: "var(--n-700)" }} />}
          iconBg="var(--surface)"
          value={stats.attempts_total}
          label="ответов всего"
        />
        <IconTile
          icon={<Check size={17} style={{ color: "var(--accent-700)" }} />}
          iconBg="var(--accent-100)"
          value={`${stats.accuracy}%`}
          valueColor="var(--accent-700)"
          label="верных"
        />
        <IconTile
          icon={<Timer size={17} style={{ color: "var(--accent-2)" }} />}
          iconBg="var(--accent-2-100)"
          value={stats.avg_seconds ? `${stats.avg_seconds} с` : "—"}
          label="в среднем на задачу"
        />
      </section>

      <section className="card" style={{ padding: "28px 30px" }}>
        <div className="section-head mb-5">
          <h2 className="section-title">По месяцам</h2>
          <span className="text-xs" style={{ color: "var(--n-400)" }}>
            решённых задач
          </span>
        </div>

        {stats.months.length === 0 ? (
          <p className="muted text-sm">Пока пусто — реши первый квиз.</p>
        ) : (
          <div
            className="relative flex items-end gap-4"
            style={{ height: 150 }}
          >
            <div
              aria-hidden
              className="absolute inset-x-0 bottom-0"
              style={{ height: 1, background: "var(--divider)" }}
            />
            {stats.months.map((month) => {
              const current = month.month === lastMonth;
              return (
                <div
                  key={month.month}
                  className="flex flex-col items-center gap-2"
                  style={{ width: 52 }}
                  title={`${month.correct} верных из ${month.solved}, дней: ${month.days_active}`}
                >
                  <span
                    className="h text-[12.5px]"
                    style={{ color: current ? "var(--accent)" : "var(--n-600)" }}
                  >
                    {month.solved}
                  </span>
                  <div
                    className="w-full"
                    style={{
                      height: Math.max(6, (month.solved / maxMonth) * 100),
                      borderRadius: "10px 10px 3px 3px",
                      background: current ? "var(--accent)" : "var(--accent-300)",
                      boxShadow: current
                        ? "0 4px 14px rgba(0,136,176,.35)"
                        : undefined,
                    }}
                  />
                  <span
                    className="text-xs"
                    style={{
                      color: "var(--n-600)",
                      fontWeight: current ? 700 : 400,
                    }}
                  >
                    {monthLabel(month.month)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="card" style={{ padding: "28px 30px" }}>
        <h2 className="section-title">Когда ты решаешь</h2>
        <p className="muted mb-5 mt-1 text-[13px]">
          По часам, время московское
        </p>

        <div
          className="flex items-end gap-[5px]"
          style={{
            height: 90,
            background: "var(--surface)",
            borderRadius: 10,
            padding: "10px 6px 0",
          }}
        >
          {stats.hours.map((hour) => (
            <div
              key={hour.hour}
              className="flex h-full flex-1 flex-col justify-end"
              title={`${hour.hour}:00 — ${hour.attempts}`}
            >
              <div
                style={{
                  height: Math.max(
                    hour.attempts ? 4 : 2,
                    (hour.attempts / maxHour) * 70,
                  ),
                  borderRadius: 4,
                  background: hour.attempts
                    ? "var(--accent)"
                    : "var(--divider)",
                }}
              />
            </div>
          ))}
        </div>

        <div className="mt-1.5 flex gap-[5px]">
          {stats.hours.map((hour) => (
            <div key={hour.hour} className="flex-1 text-center">
              {hour.hour % 6 === 0 && (
                <span className="muted text-[10.5px]">{hour.hour}</span>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="card" style={{ padding: "28px 30px" }}>
        <h2 className="section-title">Что тянет вниз</h2>
        <p className="muted mb-5 mt-1 text-[13px]">
          Номера с худшей точностью при трёх и более попытках
        </p>

        {worst.length === 0 ? (
          <p className="muted text-sm">
            Пока мало данных: номер попадает сюда после трёх попыток.
          </p>
        ) : (
          <ul className="flex flex-col gap-3.5">
            {worst.map((row) => (
              <TopicRow key={row.number} row={row} />
            ))}
          </ul>
        )}
      </section>

      <section className="card" style={{ padding: "28px 30px" }}>
        <h2 className="section-title">По номерам заданий</h2>
        <p className="muted mb-5 mt-1 text-[13px]">
          Все номера, где были попытки — точность и среднее время
        </p>

        {stats.by_type.length === 0 ? (
          <p className="muted text-sm">Данных пока нет.</p>
        ) : (
          <ul className="flex flex-col gap-3.5">
            {stats.by_type.map((row) => (
              <TopicRow key={row.number} row={row} showTime />
            ))}
          </ul>
        )}
      </section>

      {stats.best_day && (
        <p className="muted text-sm">
          Лучший день:{" "}
          {new Date(stats.best_day.day).toLocaleDateString("ru", {
            day: "numeric",
            month: "long",
          })}{" "}
          — {stats.best_day.solved}{" "}
          {plural(stats.best_day.solved, "ответ", "ответа", "ответов")}. Всего за
          решением {stats.minutes_total}{" "}
          {plural(stats.minutes_total, "минута", "минуты", "минут")}: квизов{" "}
          {stats.quizzes}, пробников {stats.mocks}, дуэлей {stats.duels}.
        </p>
      )}
    </div>
  );
}

function accuracyColor(accuracy: number): string {
  if (accuracy >= 70) return "#1f9d55";
  if (accuracy >= 40) return "#c98a00";
  return "var(--accent-2)";
}

function TopicRow({ row, showTime }: { row: TypeRow; showTime?: boolean }) {
  const color = accuracyColor(row.accuracy);

  return (
    <li className="flex items-center gap-3.5">
      <span
        className="h flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-[10px] text-[12.5px]"
        style={{ background: `${color}1a`, color }}
      >
        {row.number}
      </span>
      <span className="w-[190px] shrink-0 truncate text-[13.5px] font-medium">
        {row.title}
      </span>
      <span
        className="h-[9px] flex-1 overflow-hidden rounded-full"
        style={{ background: "var(--surface)" }}
      >
        <span
          className="block h-full rounded-full"
          style={{ width: `${row.accuracy}%`, background: color }}
        />
      </span>
      <span
        className="h w-11 shrink-0 text-right text-sm"
        style={{ color }}
      >
        {row.accuracy}%
      </span>
      {showTime && (
        <span className="muted w-12 shrink-0 text-right text-[13px]">
          {row.avg_seconds ? `${row.avg_seconds} с` : "—"}
        </span>
      )}
    </li>
  );
}

function IconTile({
  icon,
  iconBg,
  value,
  valueColor,
  label,
}: {
  icon: React.ReactNode;
  iconBg: string;
  value: number | string;
  valueColor?: string;
  label: string;
}) {
  return (
    <div
      className="flex items-center gap-3.5"
      style={{
        background: "var(--card)",
        border: "1px solid var(--divider)",
        borderRadius: 16,
        padding: 18,
        boxShadow: "0 1px 2px rgba(45,43,43,.08)",
      }}
    >
      <span
        className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-xl"
        style={{ background: iconBg }}
      >
        {icon}
      </span>
      <span className="min-w-0">
        <span
          className="h block text-[22px]"
          style={{ color: valueColor }}
        >
          {value}
        </span>
        <span className="muted mt-px block text-xs">{label}</span>
      </span>
    </div>
  );
}
