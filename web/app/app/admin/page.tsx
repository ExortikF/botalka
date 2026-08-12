"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { BarChart3, ClipboardList, Flag, Lightbulb, Pencil, Plus, Trash2 } from "lucide-react";
import MathText from "../../Math";
import { api, getTaskTypes, type TaskType } from "@/lib/api";
import TaskForm, { type AdminTask, EMPTY_TASK } from "./TaskForm";

type TaskList = { total: number; items: AdminTask[] };
type Stats = {
  total: number;
  live: number;
  draft: number;
  broken: number;
  by_type: { number: number; title: string; live: number; draft: number; broken: number }[];
};

const STATUS_LABEL: Record<string, string> = {
  live: "опубликована",
  draft: "черновик",
  broken: "снята",
};

export default function AdminPage() {
  // useSearchParams требует границы Suspense, иначе страница не пререндерится
  return (
    <Suspense fallback={<p className="muted">Загрузка…</p>}>
      <AdminTasks />
    </Suspense>
  );
}

function AdminTasks() {
  const [denied, setDenied] = useState(false);
  const [list, setList] = useState<TaskList | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [types, setTypes] = useState<TaskType[]>([]);
  const [editing, setEditing] = useState<AdminTask | null>(null);
  const [filter, setFilter] = useState<{ q: string; status: string; type: string }>({
    q: "",
    status: "",
    type: "",
  });

  const reload = useCallback(() => {
    const params = new URLSearchParams({ limit: "50" });
    if (filter.q) params.set("q", filter.q);
    if (filter.status) params.set("task_status", filter.status);
    if (filter.type) params.set("task_type_id", filter.type);

    api<TaskList>(`/api/admin/tasks?${params}`)
      .then((data) => {
        setList(data);
        setDenied(false);
      })
      .catch(() => setDenied(true));
    api<Stats>("/api/admin/stats").then(setStats).catch(() => setStats(null));
  }, [filter]);

  const params = useSearchParams();
  const requestedTask = params.get("task");

  useEffect(() => {
    getTaskTypes().then(setTypes).catch(() => setTypes([]));
  }, []);

  // ?task=42 — открыть сразу форму этой задачи, например из жалобы
  useEffect(() => {
    if (!requestedTask) return;
    api<AdminTask>(`/api/admin/tasks/${requestedTask}`)
      .then(setEditing)
      .catch(() => setDenied(true));
  }, [requestedTask]);

  useEffect(reload, [reload]);

  async function archive(task: AdminTask) {
    if (!confirm(`Снять задачу «${task.slug}» с публикации?`)) return;
    await api(`/api/admin/tasks/${task.id}`, { method: "DELETE" });
    reload();
  }

  if (denied)
    return (
      <div className="card p-7">
        <h1 className="text-2xl">Нужны права администратора</h1>
        <p className="muted mt-2 text-sm leading-relaxed">
          Войди через Telegram, затем выполни в терминале:
        </p>
        <pre className="mt-3 overflow-x-auto rounded-xl p-4 text-sm" style={{ background: "var(--surface)" }}>
          docker compose exec backend python -m app.cli.make_admin ТВОЙ_TG_ID
        </pre>
      </div>
    );

  if (editing)
    return (
      <TaskForm
        task={editing}
        types={types}
        onDone={() => {
          setEditing(null);
          reload();
        }}
        onCancel={() => setEditing(null)}
      />
    );

  return (
    <div className="space-y-7">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl">Банк задач</h1>
          <p className="muted mt-1 text-sm">
            {stats
              ? `${stats.total} всего · ${stats.live} опубликовано · ${stats.draft} черновиков · ${stats.broken} снято`
              : "загрузка…"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-ghost" href="/app/admin/dashboard">
            <BarChart3 size={16} /> Дашборд
          </Link>
          <Link className="btn-ghost" href="/app/admin/reports">
            <Flag size={16} /> Жалобы
          </Link>
          <Link className="btn-ghost" href="/app/admin/ideas">
            <Lightbulb size={16} /> Идеи
          </Link>
          <Link className="btn-ghost" href="/app/admin/mocks">
            <ClipboardList size={16} /> Пробники
          </Link>
          <button className="btn" onClick={() => setEditing({ ...EMPTY_TASK })}>
            <Plus size={16} /> Добавить задачу
          </button>
        </div>
      </header>

      {stats && (
        <section className="card p-5">
          <p className="eyebrow mb-3">Покрытие по номерам</p>
          <div className="flex flex-wrap gap-2">
            {stats.by_type.map((row) => (
              <span
                key={row.number}
                title={`${row.title}: ${row.live} опубликовано, ${row.draft} черновиков`}
                className="rounded-lg px-3 py-1.5 text-sm"
                style={{
                  background: row.live >= 20 ? "var(--accent-200)" : "var(--surface)",
                  color: row.live === 0 ? "var(--accent-2)" : "var(--text)",
                }}
              >
                №{row.number} · {row.live}
              </span>
            ))}
          </div>
          <p className="muted mt-3 text-xs">
            Цель — минимум 20 задач на номер. Подсвечены те, где цель достигнута.
          </p>
        </section>
      )}

      <section className="flex flex-wrap gap-2">
        <input
          className="input"
          style={{ maxWidth: "18rem" }}
          placeholder="Поиск по условию или slug"
          value={filter.q}
          onChange={(e) => setFilter({ ...filter, q: e.target.value })}
        />
        <select
          className="input"
          style={{ maxWidth: "12rem" }}
          value={filter.status}
          onChange={(e) => setFilter({ ...filter, status: e.target.value })}
        >
          <option value="">Любой статус</option>
          <option value="live">Опубликованные</option>
          <option value="draft">Черновики</option>
          <option value="broken">Снятые</option>
        </select>
        <select
          className="input"
          style={{ maxWidth: "14rem" }}
          value={filter.type}
          onChange={(e) => setFilter({ ...filter, type: e.target.value })}
        >
          <option value="">Любой номер</option>
          {types.map((t) => (
            <option key={t.id} value={t.id}>
              № {t.number} — {t.title}
            </option>
          ))}
        </select>
      </section>

      <section className="space-y-2">
        {list?.items.length === 0 && <p className="muted">Ничего не найдено.</p>}
        {list?.items.map((task) => (
          <article key={task.id} className="card flex items-start gap-4 p-4">
            <span
              className="rounded-lg px-2.5 py-1 text-xs font-medium"
              style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
            >
              № {task.task_type_number}
            </span>

            <div className="min-w-0 flex-1">
              <MathText className="block text-sm leading-relaxed" text={task.statement} />
              <p className="muted mt-1 text-xs">
                {task.slug} · ответ {task.answer_value} · {STATUS_LABEL[task.status]}
                {task.source && ` · ${task.source}`}
              </p>
            </div>

            <button
              className="muted p-2 hover:text-[var(--accent)]"
              title="Изменить"
              onClick={() => setEditing(task)}
            >
              <Pencil size={16} />
            </button>
            <button
              className="muted p-2 hover:text-[var(--accent-2)]"
              title="Снять с публикации"
              onClick={() => archive(task)}
            >
              <Trash2 size={16} />
            </button>
          </article>
        ))}

        {list && list.total > list.items.length && (
          <p className="muted text-sm">
            Показаны {list.items.length} из {list.total} — уточни фильтр.
          </p>
        )}
      </section>
    </div>
  );
}
