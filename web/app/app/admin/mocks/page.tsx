"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { api, getTaskTypes, type TaskType } from "@/lib/api";

type Mock = {
  id: number;
  title: string;
  description: string | null;
  duration_minutes: number;
  status: string;
  task_ids: number[];
  numbers: number[];
  attempts: number;
};

const STATUS_LABEL: Record<string, string> = {
  draft: "черновик",
  live: "опубликован",
  hidden: "скрыт",
};

export default function AdminMocksPage() {
  const [mocks, setMocks] = useState<Mock[] | null>(null);
  const [types, setTypes] = useState<TaskType[]>([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState(235);
  const [numbers, setNumbers] = useState<number[]>(Array.from({ length: 12 }, (_, i) => i + 1));
  const [publish, setPublish] = useState(true);

  const load = useCallback(() => {
    api<Mock[]>("/api/admin/mocks")
      .then(setMocks)
      .catch(() => setMocks([]));
  }, []);

  useEffect(() => {
    load();
    getTaskTypes().then(setTypes).catch(() => setTypes([]));
  }, [load]);

  async function create() {
    setCreating(true);
    setError("");
    try {
      await api("/api/admin/mocks", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          duration_minutes: duration,
          auto_numbers: numbers,
          status: publish ? "live" : "draft",
        }),
      });
      setTitle("");
      setDescription("");
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCreating(false);
    }
  }

  async function hide(id: number) {
    if (!confirm("Скрыть пробник от учеников?")) return;
    await api(`/api/admin/mocks/${id}`, { method: "DELETE" });
    load();
  }

  function toggleNumber(n: number) {
    setNumbers((prev) => (prev.includes(n) ? prev.filter((x) => x !== n) : [...prev, n].sort((a, b) => a - b)));
  }

  return (
    <div className="space-y-7">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl">Конструктор пробников</h1>
          <p className="muted mt-1 text-sm">
            Вариант собирается по одной случайной задаче на каждый отмеченный номер.
          </p>
        </div>
        <Link className="btn-ghost" href="/app/admin">
          <ArrowLeft size={15} /> К задачам
        </Link>
      </header>

      <section className="card space-y-4 p-6">
        <h2 className="text-xl">Новый пробник</h2>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="eyebrow mb-1.5 block">Название</span>
            <input
              className="input"
              placeholder="Пробник №1 · часть 1"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="eyebrow mb-1.5 block">Время, минут</span>
            <input
              className="input"
              inputMode="numeric"
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value) || 0)}
            />
            <span className="muted mt-1 block text-xs">
              235 минут — это 3 часа 55 минут, как на экзамене
            </span>
          </label>
        </div>

        <label className="block">
          <span className="eyebrow mb-1.5 block">Описание</span>
          <input
            className="input"
            placeholder="Полный вариант части 1"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>

        <div>
          <span className="eyebrow mb-2 block">Какие номера включить</span>
          <div className="flex flex-wrap gap-2">
            {types.map((type) => (
              <button
                key={type.id}
                onClick={() => toggleNumber(type.number)}
                className={`pill ${numbers.includes(type.number) ? "pill-active" : "pill-idle"}`}
                style={{ border: "1px solid var(--divider)" }}
                title={type.title}
              >
                № {type.number}
              </button>
            ))}
          </div>
          <p className="muted mt-2 text-xs">Отмечено номеров: {numbers.length}</p>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={publish}
            onChange={(e) => setPublish(e.target.checked)}
          />
          Сразу опубликовать
        </label>

        <button
          className="btn"
          onClick={create}
          disabled={creating || title.trim().length < 3 || numbers.length < 3}
        >
          <Plus size={16} /> {creating ? "Собираем…" : "Собрать пробник"}
        </button>
        {error && (
          <p className="text-sm" style={{ color: "var(--accent-2)" }}>
            {error}
          </p>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xl">Готовые пробники</h2>
        {mocks === null ? (
          <p className="muted">Загрузка…</p>
        ) : mocks.length === 0 ? (
          <p className="muted text-sm">Пока ни одного.</p>
        ) : (
          <ul className="space-y-2">
            {mocks.map((mock) => (
              <li key={mock.id}>
                <article className="card flex items-center gap-4 p-4">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{mock.title}</p>
                    <p className="muted text-sm">
                      {mock.task_ids.length} заданий · {mock.duration_minutes} мин ·{" "}
                      {STATUS_LABEL[mock.status]} · прохождений {mock.attempts}
                    </p>
                    <p className="muted text-xs">номера: {mock.numbers.join(", ")}</p>
                  </div>
                  <button
                    className="muted p-2 hover:text-[var(--accent-2)]"
                    title="Скрыть"
                    onClick={() => hide(mock.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
