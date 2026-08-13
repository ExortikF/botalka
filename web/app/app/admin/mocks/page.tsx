"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Check, Plus, Search, Trash2 } from "lucide-react";
import MathText from "../../../Math";
import { api, getTaskTypes, type TaskType } from "@/lib/api";
import AddTaskInline from "./AddTaskInline";

type PickRow = {
  id: number;
  number: number;
  statement: string;
  answer_value: string;
  difficulty: number;
};

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
  const [subjectSlug, setSubjectSlug] = useState("math_prof");
  const [numbers, setNumbers] = useState<number[]>(
    Array.from({ length: 12 }, (_, i) => i + 1),
  );
  const [publish, setPublish] = useState(true);

  /** Режим набора: автоматически по номерам или вручную выбранные задачи. */
  const [mode, setMode] = useState<"auto" | "manual">("auto");
  const [pickNumber, setPickNumber] = useState<number | null>(null);
  const [pickQuery, setPickQuery] = useState("");
  const [pool, setPool] = useState<PickRow[]>([]);
  const [picked, setPicked] = useState<PickRow[]>([]);

  const load = useCallback(() => {
    api<Mock[]>("/api/admin/mocks")
      .then(setMocks)
      .catch(() => setMocks([]));
  }, []);

  useEffect(() => {
    load();
    getTaskTypes()
      .then(setTypes)
      .catch(() => setTypes([]));
  }, [load]);

  function loadPool(number: number, q = "") {
    setPickNumber(number);
    api<PickRow[]>(`/api/admin/tasks/pick/${number}?q=${encodeURIComponent(q)}`)
      .then(setPool)
      .catch(() => setPool([]));
  }

  function togglePicked(task: PickRow) {
    setPicked((prev) =>
      prev.some((t) => t.id === task.id)
        ? prev.filter((t) => t.id !== task.id)
        : [...prev, task],
    );
  }

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
          subject_slug: subjectSlug,
          auto_numbers: mode === "auto" ? numbers : [],
          task_ids: mode === "manual" ? picked.map((t) => t.id) : [],
          status: publish ? "live" : "draft",
        }),
      });
      setPicked([]);
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
    setNumbers((prev) =>
      prev.includes(n)
        ? prev.filter((x) => x !== n)
        : [...prev, n].sort((a, b) => a - b),
    );
  }

  return (
    <div className="space-y-7">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl">Конструктор пробников</h1>
          <p className="muted mt-1 text-sm">
            Вариант собирается по одной случайной задаче на каждый отмеченный
            номер.
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
            <span className="eyebrow mb-1.5 block">Предмет</span>
            <select
              className="input"
              value={subjectSlug}
              onChange={(e) => setSubjectSlug(e.target.value)}
            >
              <option value="math_prof">Математика (профиль)</option>
              <option value="rus">Русский язык</option>
              <option value="inf">Информатика</option>
            </select>
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

        <div className="flex flex-wrap gap-2">
          {[
            { key: "auto", label: "Собрать автоматически" },
            { key: "manual", label: "Выбрать задачи вручную" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setMode(tab.key as "auto" | "manual")}
              className={`pill ${mode === tab.key ? "pill-active" : "pill-idle"}`}
              style={{ border: "1px solid var(--divider)" }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {mode === "auto" ? (
          <div>
            <span className="eyebrow mb-2 block">Какие номера включить</span>
            <div className="flex flex-wrap gap-2">
              {types.map((type) => (
                <button
                  key={type.id}
                  onClick={() => toggleNumber(type.number)}
                  disabled={type.tasks_count === 0}
                  className={`pill ${numbers.includes(type.number) ? "pill-active" : "pill-idle"}`}
                  style={{
                    border: "1px solid var(--divider)",
                    opacity: type.tasks_count === 0 ? 0.4 : 1,
                  }}
                  title={
                    type.tasks_count === 0
                      ? `${type.title} — задач в банке нет`
                      : `${type.title} · ${type.tasks_count} задач`
                  }
                >
                  № {type.number}
                </button>
              ))}
            </div>
            <p className="muted mt-2 text-xs">
              Отмечено номеров: {numbers.length}. Из каждого берётся одна
              случайная задача. Номера без задач выбрать нельзя.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <span className="eyebrow mb-2 block">Номер задания</span>
              <div className="flex flex-wrap gap-2">
                {types.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => loadPool(type.number, pickQuery)}
                    disabled={type.tasks_count === 0}
                    className={`pill ${pickNumber === type.number ? "pill-active" : "pill-idle"}`}
                    style={{
                      border: "1px solid var(--divider)",
                      opacity: type.tasks_count === 0 ? 0.4 : 1,
                    }}
                    title={type.title}
                  >
                    № {type.number}
                  </button>
                ))}
              </div>
            </div>

            {pickNumber && (
              <>
                <div className="flex gap-2">
                  <input
                    className="input"
                    placeholder="Поиск по условию"
                    value={pickQuery}
                    onChange={(e) => setPickQuery(e.target.value)}
                    onKeyDown={(e) =>
                      e.key === "Enter" && loadPool(pickNumber, pickQuery)
                    }
                  />
                  <button
                    className="btn-ghost"
                    onClick={() => loadPool(pickNumber, pickQuery)}
                  >
                    <Search size={15} />
                  </button>
                </div>

                <ul className="max-h-72 space-y-1 overflow-y-auto">
                  {pool.map((task) => {
                    const chosen = picked.some((t) => t.id === task.id);
                    return (
                      <li key={task.id}>
                        <button
                          onClick={() => togglePicked(task)}
                          className="flex w-full items-start gap-3 rounded-xl p-3 text-left text-sm transition"
                          style={{
                            background: chosen
                              ? "var(--accent-100)"
                              : "var(--surface)",
                          }}
                        >
                          <span
                            className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border"
                            style={{
                              borderColor: chosen
                                ? "var(--accent)"
                                : "var(--divider)",
                              background: chosen
                                ? "var(--accent)"
                                : "transparent",
                              color: "#fff",
                            }}
                          >
                            {chosen && <Check size={12} />}
                          </span>
                          <span className="min-w-0">
                            <MathText className="block" text={task.statement} />
                            <span className="muted text-xs">
                              ответ {task.answer_value}
                            </span>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                  {pool.length === 0 && (
                    <li className="muted text-sm">
                      По этому номеру задач не нашлось.
                    </li>
                  )}
                </ul>
              </>
            )}

            <p className="muted text-sm">
              Выбрано задач: {picked.length}
              {picked.length > 0 &&
                ` (номера ${[...new Set(picked.map((t) => t.number))].sort((a, b) => a - b).join(", ")})`}
            </p>
            <AddTaskInline
              types={types}
              onCreated={(task) => setPicked((prev) => [...prev, task])}
            />
          </div>
        )}

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
          disabled={
            creating ||
            title.trim().length < 3 ||
            (mode === "auto" ? numbers.length < 3 : picked.length < 3)
          }
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
                      {mock.task_ids.length} заданий · {mock.duration_minutes}{" "}
                      мин · {STATUS_LABEL[mock.status]} · прохождений{" "}
                      {mock.attempts}
                    </p>
                    <p className="muted text-xs">
                      номера: {mock.numbers.join(", ")}
                    </p>
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
