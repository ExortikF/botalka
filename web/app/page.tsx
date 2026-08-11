"use client";

import { useCallback, useEffect, useState } from "react";
import TelegramLogin from "./TelegramLogin";
import { API_URL, getMe, logout, type User } from "@/lib/api";

type Health = Record<string, string>;

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));

    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "недоступен" }));
  }, []);

  const onLogin = useCallback((u: User) => {
    setUser(u);
    setError(null);
  }, []);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Botalka</h1>
        <p className="muted mt-1">Подготовка к ЕГЭ: квизы, дуэли, рейтинг.</p>
      </header>

      <section className="card p-6">
        {loading ? (
          <p className="muted">Загрузка…</p>
        ) : user ? (
          <div className="space-y-3">
            <p className="text-lg">
              Привет, <span className="font-semibold">{user.display_name}</span>
            </p>
            <p className="muted text-sm">
              Рейтинг {user.rating} · серия {user.streak_days} дн.
            </p>
            <button
              className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm"
              onClick={() => logout().then(() => setUser(null))}
            >
              Выйти
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="font-medium">Войти через Telegram</p>
            <TelegramLogin onLogin={onLogin} onError={setError} />
            {error && <p className="text-sm text-wrong">{error}</p>}
          </div>
        )}
      </section>

      <section className="card p-6">
        <h2 className="mb-3 font-semibold">Состояние сервисов</h2>
        <ul className="muted space-y-1 text-sm">
          {health ? (
            Object.entries(health).map(([k, v]) => (
              <li key={k}>
                {k}: <span className={v === "ok" ? "text-correct" : "text-wrong"}>{v}</span>
              </li>
            ))
          ) : (
            <li>проверяем…</li>
          )}
        </ul>
      </section>

      <p className="muted text-sm">
        Каркас Спринта 0. Что дальше — <code>docs/ROADMAP.md</code>.
      </p>
    </div>
  );
}
