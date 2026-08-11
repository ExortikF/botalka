"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Flame, Swords } from "lucide-react";
import { getMe, getStats, getTaskTypes, type StatsRow, type TaskType, type User } from "@/lib/api";
import { plural } from "@/lib/exam";

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [types, setTypes] = useState<TaskType[]>([]);
  const [stats, setStats] = useState<StatsRow[]>([]);
  // дата считается в браузере: на сервере другой часовой пояс, и SSR ломает гидратацию
  const [today, setToday] = useState<string | null>(null);

  useEffect(() => {
    setToday(
      new Date()
        .toLocaleDateString("ru", { weekday: "long", day: "numeric", month: "long" })
        .toUpperCase(),
    );
  }, []);

  useEffect(() => {
    getMe().then(setUser).catch(() => setUser(null));
    getTaskTypes().then(setTypes).catch(() => setTypes([]));
    getStats().then(setStats).catch(() => setStats([]));
  }, []);

  const statsByNumber = new Map(stats.map((s) => [s.task_type_number, s]));
  const solved = stats.reduce((sum, s) => sum + s.total, 0);
  const correct = stats.reduce((sum, s) => sum + s.correct, 0);

  // слабое место — тот номер, где процент ниже всего при хотя бы двух попытках
  const weakest = [...stats]
    .filter((s) => s.total >= 2)
    .sort((a, b) => a.correct / a.total - b.correct / b.total)[0];

  const firstName = user?.display_name.split(" ")[0] ?? "";

  return (
    <div className="space-y-8">
      <section
        className="relative overflow-hidden p-8 text-white"
        style={{ background: "var(--accent)", borderRadius: "var(--radius-lg)" }}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute -right-16 -top-20 h-72 w-72 rounded-full opacity-30"
          style={{ background: "var(--accent-2)" }}
        />
        <div className="relative flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-lg">
            <p className="text-xs font-semibold uppercase tracking-widest opacity-80">
              {today ?? "\u00a0"}
            </p>
            <h1 className="mt-3 text-3xl leading-tight">
              {firstName ? `Привет, ${firstName}.` : "Привет."} Сегодня десять задач
            </h1>
            <p className="mt-3 leading-relaxed opacity-90">
              {weakest
                ? `Начни с номера ${weakest.task_type_number} — «${weakest.task_type_title}» пока проседает.`
                : "Начни со случайного квиза, чтобы стало видно, какие номера проседают."}
            </p>
          </div>

          <div className="flex flex-col items-start gap-3">
            {user && user.streak_days > 0 && (
              <span className="flex items-center gap-2 rounded-full bg-white/20 px-4 py-2 text-sm font-medium">
                <Flame size={16} />
                {user.streak_days} {plural(user.streak_days, "день", "дня", "дней")} подряд
              </span>
            )}
            <Link
              className="rounded-xl bg-white px-5 py-3 font-semibold"
              style={{ color: "var(--accent-700)" }}
              href="/app/quiz"
            >
              Начать день
            </Link>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="card space-y-1 p-6 lg:col-span-2">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-xl">План на сегодня</h2>
            <span className="muted text-sm">задачи подбираются случайно</span>
          </div>

          <PlanRow
            n="01"
            title="Случайный квиз"
            meta="10 вопросов · около 8 минут · номера 1–12"
            href="/app/quiz"
            cta="Начать"
          />
          <PlanRow
            n="02"
            title={weakest ? `Добить номер ${weakest.task_type_number}` : "Тренировка по номеру"}
            meta={
              weakest
                ? `5 задач · ${weakest.task_type_title} · сейчас ${Math.round(
                    (weakest.correct / weakest.total) * 100,
                  )}% верно`
                : "5 задач по одному номеру — выбери ниже"
            }
            href={
              weakest
                ? `/app/quiz?type=${types.find((t) => t.number === weakest.task_type_number)?.id ?? ""}&length=5`
                : "/app/quiz?length=5"
            }
            cta="Начать"
          />
          <PlanRow
            n="03"
            title="Дуэль по слабой теме"
            meta="7 раундов · вопрос приходит обоим одновременно"
            locked
            cta="Скоро"
          />
        </section>

        <div className="space-y-6">
          <section className="card p-6">
            <p className="eyebrow">Твоя статистика</p>
            <p className="h mt-2 text-4xl">
              {correct}
              <span className="muted text-2xl"> / {solved}</span>
            </p>
            <p className="muted mt-1 text-sm">
              {solved > 0
                ? `${Math.round((correct / solved) * 100)}% верных ответов за всё время`
                : "пока ни одной решённой задачи"}
            </p>
          </section>

          <section className="card p-6">
            <p className="eyebrow flex items-center gap-2">
              <Swords size={14} /> Дуэли
            </p>
            <p className="muted mt-2 text-sm leading-relaxed">
              Пока в разработке. Рейтинг будет считаться только по дуэлям — квизы на него
              не влияют.
            </p>
          </section>
        </div>
      </div>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl">Тренировка по номеру</h2>
          <span className="muted text-sm">
            {types.reduce((s, t) => s + t.tasks_count, 0)} задач в банке
          </span>
        </div>

        {types.length === 0 ? (
          <p className="muted text-sm">Банк задач пуст — запустите импорт контента.</p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {types.map((type) => {
              const stat = statsByNumber.get(type.number);
              const percent = stat?.total ? Math.round((stat.correct / stat.total) * 100) : null;
              return (
                <li key={type.id}>
                  <Link
                    href={`/app/quiz?type=${type.id}&length=5`}
                    className="card flex items-center justify-between gap-3 p-4 transition hover:shadow-[var(--shadow-sm)]"
                  >
                    <span className="min-w-0">
                      <span className="muted mr-2 text-sm">№{type.number}</span>
                      {type.title}
                    </span>
                    <span className="shrink-0 text-sm">
                      {percent !== null ? (
                        <span
                          style={{ color: percent >= 70 ? "var(--accent)" : "var(--accent-2)" }}
                        >
                          {percent}%
                        </span>
                      ) : (
                        <span className="muted">{type.tasks_count} зад.</span>
                      )}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

function PlanRow({
  n,
  title,
  meta,
  href,
  cta,
  locked,
}: {
  n: string;
  title: string;
  meta: string;
  href?: string;
  cta: string;
  locked?: boolean;
}) {
  return (
    <div
      className="flex items-center gap-4 border-b py-4 last:border-0"
      style={{ borderColor: "var(--divider)" }}
    >
      <span className="h text-lg" style={{ color: locked ? "var(--n-400)" : "var(--accent)" }}>
        {n}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-medium" style={{ color: locked ? "var(--n-500)" : undefined }}>
          {title}
        </span>
        <span className="muted block text-sm">{meta}</span>
      </span>
      {locked || !href ? (
        <span
          className="rounded-xl px-4 py-2 text-sm"
          style={{ background: "var(--surface)", color: "var(--n-500)" }}
        >
          {cta}
        </span>
      ) : (
        <Link className="btn shrink-0 text-sm" href={href}>
          {cta}
        </Link>
      )}
    </div>
  );
}
