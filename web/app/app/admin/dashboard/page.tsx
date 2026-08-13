"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";

type UserRow = {
  id: number;
  display_name: string;
  kind: "guest" | "telegram";
  solved: number;
  accuracy: number | null;
  streak_days: number;
  rating: number;
  duels: number;
  registered: string;
  last_seen: string | null;
};

type ProblemTask = {
  id: number;
  number: number;
  statement: string;
  attempts: number;
  accuracy: number;
};

type Funnel = {
  registered: number;
  started_quiz: number;
  finished_quiz: number;
  came_back: number;
  played_duel: number;
};

type Dashboard = {
  coins_issued: number;
  avg_seconds: number;
  retention_d1: number;
  retention_d7: number;
  funnel: Funnel;
  users_total: number;
  users_telegram: number;
  users_guests: number;
  users_new_week: number;
  users_active_week: number;
  users_active_today: number;
  attempts_total: number;
  attempts_week: number;
  accuracy_avg: number | null;
  quizzes_finished: number;
  duels_link: number;
  duels_online: number;
  users: UserRow[];
  hardest: ProblemTask[];
  easiest: ProblemTask[];
};

export default function AdminDashboard() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    api<Dashboard>("/api/admin/dashboard")
      .then(setData)
      .catch(() => setDenied(true));
  }, []);

  if (denied) return <p className="muted">Нужны права администратора.</p>;
  if (!data) return <p className="muted">Загрузка…</p>;

  return (
    <div className="page">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Дашборд</h1>
          <p className="muted mt-1 text-sm">
            Личные данные сюда не попадают: ни Telegram-id, ни ников, ни
            контактов.
          </p>
        </div>
        <Link className="btn-ghost" href="/app/admin">
          <ArrowLeft size={15} /> К задачам
        </Link>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <Metric value={data.users_total} label="пользователей всего" />
        <Metric
          value={data.users_active_today}
          label="решали за сутки"
          hint={`за неделю ${data.users_active_week}`}
        />
        <Metric value={data.users_new_week} label="новых за неделю" />
        <Metric
          value={data.users_telegram}
          label="вошли через Telegram"
          hint={`гостей ${data.users_guests}`}
        />
        <Metric
          value={data.attempts_total}
          label="ответов всего"
          hint={`за неделю ${data.attempts_week}`}
        />
        <Metric
          value={data.accuracy_avg === null ? "—" : `${data.accuracy_avg}%`}
          label="средняя точность"
          hint={`квизов ${data.quizzes_finished}`}
        />
      </section>

      <section className="grid gap-4 sm:grid-cols-4">
        <Metric
          value={`${data.retention_d1}%`}
          label="вернулись на следующий день"
          hint="из тех, кто зарегистрирован сутки назад и раньше"
        />
        <Metric
          value={`${data.retention_d7}%`}
          label="вернулись через неделю"
          hint="главная метрика продукта"
        />
        <Metric value={data.coins_issued} label="монет выдано всего" />
        <Metric value={`${data.avg_seconds} с`} label="в среднем на задачу" />
      </section>

      <section className="card p-6">
        <p className="eyebrow mb-4">Воронка</p>
        <ul className="space-y-2">
          {[
            { label: "Зарегистрировались", value: data.funnel.registered },
            { label: "Начали квиз", value: data.funnel.started_quiz },
            { label: "Закончили квиз", value: data.funnel.finished_quiz },
            { label: "Вернулись в другой день", value: data.funnel.came_back },
            { label: "Сыграли дуэль", value: data.funnel.played_duel },
          ].map((step) => {
            const percent = data.funnel.registered
              ? Math.round((step.value / data.funnel.registered) * 100)
              : 0;
            return (
              <li key={step.label} className="flex items-center gap-3 text-sm">
                <span className="w-52 shrink-0">{step.label}</span>
                <span
                  className="h-3 flex-1 overflow-hidden rounded-full"
                  style={{ background: "var(--surface)" }}
                >
                  <span
                    className="block h-full rounded-full"
                    style={{
                      width: `${percent}%`,
                      background: "var(--accent)",
                    }}
                  />
                </span>
                <span className="w-20 shrink-0 text-right">
                  {step.value} <span className="muted">· {percent}%</span>
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="card p-6">
        <p className="eyebrow mb-3">Дуэли</p>
        <div className="flex flex-wrap gap-8">
          <div>
            <p className="h text-3xl">{data.duels_link}</p>
            <p className="muted text-sm">по ссылке</p>
          </div>
          <div>
            <p className="h text-3xl">{data.duels_online}</p>
            <p className="muted text-sm">онлайн-матчей</p>
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="section-title">Задачи с подозрительной решаемостью</h2>
        <p className="muted text-sm">
          0% почти всегда значит ошибку в эталонном ответе, 100% — что задача
          слишком лёгкая. Смотреть при трёх и более попытках.
        </p>
        <div className="grid gap-4 lg:grid-cols-2">
          <TaskList title="Проваливают чаще всего" tasks={data.hardest} bad />
          <TaskList title="Решают почти все" tasks={data.easiest} />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="section-title">Пользователи</h2>
        <div className="card overflow-x-auto">
          <table className="w-full text-sm" style={{ minWidth: "44rem" }}>
            <thead>
              <tr
                className="muted text-left"
                style={{ borderBottom: "1px solid var(--divider)" }}
              >
                <Th>Имя</Th>
                <Th>Вход</Th>
                <Th>Решено</Th>
                <Th>Точность</Th>
                <Th>Серия</Th>
                <Th>Рейтинг</Th>
                <Th>Дуэли</Th>
                <Th>Последняя активность</Th>
              </tr>
            </thead>
            <tbody>
              {data.users.map((user) => (
                <tr
                  key={user.id}
                  style={{ borderBottom: "1px solid var(--divider)" }}
                >
                  <Td>{user.display_name}</Td>
                  <Td>
                    <span className="muted">
                      {user.kind === "guest" ? "гость" : "Telegram"}
                    </span>
                  </Td>
                  <Td>{user.solved}</Td>
                  <Td>{user.accuracy === null ? "—" : `${user.accuracy}%`}</Td>
                  <Td>{user.streak_days}</Td>
                  <Td>{user.rating}</Td>
                  <Td>{user.duels}</Td>
                  <Td>
                    <span className="muted">
                      {user.last_seen
                        ? new Date(user.last_seen).toLocaleDateString("ru", {
                            day: "numeric",
                            month: "short",
                          })
                        : "не решал"}
                    </span>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Metric({
  value,
  label,
  hint,
}: {
  value: number | string;
  label: string;
  hint?: string;
}) {
  return (
    <div className="card p-5">
      <p className="h text-3xl">{value}</p>
      <p className="muted mt-1 text-sm leading-snug">{label}</p>
      {hint && <p className="muted text-xs">{hint}</p>}
    </div>
  );
}

function TaskList({
  title,
  tasks,
  bad,
}: {
  title: string;
  tasks: ProblemTask[];
  bad?: boolean;
}) {
  return (
    <div className="card p-5">
      <p className="eyebrow mb-3">{title}</p>
      {tasks.length === 0 ? (
        <p className="muted text-sm">Пока мало данных.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {tasks.map((task) => (
            <li
              key={task.id}
              className="flex items-start justify-between gap-3"
            >
              <span className="min-w-0">
                <span className="muted mr-2">№{task.number}</span>
                {task.statement}…
              </span>
              <span
                className="shrink-0 font-medium"
                style={{ color: bad ? "var(--accent-2)" : "var(--accent)" }}
              >
                {task.accuracy}%
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-4 py-3 font-medium">{children}</th>;
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-4 py-3">{children}</td>;
}
