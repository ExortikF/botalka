"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import TelegramLogin from "./TelegramLogin";
import {
  getMe,
  getStats,
  getTaskTypes,
  logout,
  type StatsRow,
  type TaskType,
  type User,
} from "@/lib/api";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [types, setTypes] = useState<TaskType[]>([]);
  const [stats, setStats] = useState<StatsRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMe().then(setUser).catch(() => setUser(null));
    getTaskTypes().then(setTypes).catch(() => setTypes([]));
    getStats().then(setStats).catch(() => setStats([]));
  }, []);

  const onLogin = useCallback((u: User) => {
    setUser(u);
    setError(null);
  }, []);

  const statsByNumber = new Map(stats.map((s) => [s.task_type_number, s]));
  const totalTasks = types.reduce((sum, t) => sum + t.tasks_count, 0);

  return (
    <div className="space-y-10">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Botalka</h1>
          <p className="muted mt-1">Профильная математика. Часть 1.</p>
        </div>
        {user && !user.is_guest && (
          <div className="text-right text-sm">
            <p className="font-medium">{user.display_name}</p>
            <button className="muted underline" onClick={() => logout().then(() => setUser(null))}>
              выйти
            </button>
          </div>
        )}
      </header>

      <section className="card space-y-4 p-6">
        <div>
          <h2 className="text-xl font-semibold">Случайный квиз</h2>
          <p className="muted mt-1 text-sm">
            10 задач из разных номеров. Регистрация не нужна — прогресс сохранится.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link className="btn" href="/quiz">
            Начать
          </Link>
          <Link className="btn-outline" href="/quiz?length=5">
            Короткий, 5 задач
          </Link>
        </div>
        {user?.streak_days ? (
          <p className="muted text-sm">Серия: {user.streak_days} дн. подряд</p>
        ) : null}
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <h2 className="text-xl font-semibold">Тренировка по номеру</h2>
          <span className="muted text-sm">{totalTasks} задач в банке</span>
        </div>

        {types.length === 0 ? (
          <p className="muted text-sm">Банк задач пуст — запустите импорт контента.</p>
        ) : (
          <ul className="grid gap-2 sm:grid-cols-2">
            {types.map((type) => {
              const stat = statsByNumber.get(type.number);
              const percent = stat && stat.total ? Math.round((stat.correct / stat.total) * 100) : null;
              return (
                <li key={type.id}>
                  <Link
                    href={`/quiz?type=${type.id}&length=5`}
                    className="card flex items-center justify-between gap-3 p-4 transition hover:border-accent"
                  >
                    <span>
                      <span className="muted mr-2 text-sm">№{type.number}</span>
                      {type.title}
                    </span>
                    <span className="shrink-0 text-sm">
                      {percent !== null ? (
                        <span className={percent >= 70 ? "text-correct" : "text-wrong"}>
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

      {stats.length > 0 && (
        <section className="card space-y-2 p-6">
          <h2 className="font-semibold">Ваша статистика</h2>
          <ul className="muted space-y-1 text-sm">
            {stats.map((row) => (
              <li key={row.task_type_number}>
                №{row.task_type_number} {row.task_type_title}: {row.correct} из {row.total}
              </li>
            ))}
          </ul>
        </section>
      )}

      {(!user || user.is_guest) && (
        <section className="card space-y-3 p-6">
          <h2 className="font-semibold">Сохранить прогресс</h2>
          <p className="muted text-sm">
            Вход через Telegram привяжет уже решённое к аккаунту — понадобится для дуэлей
            и рейтинга.
          </p>
          <TelegramLogin onLogin={onLogin} onError={setError} />
          {error && <p className="text-sm text-wrong">{error}</p>}
        </section>
      )}
    </div>
  );
}
