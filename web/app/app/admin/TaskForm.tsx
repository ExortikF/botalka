"use client";

import { useState } from "react";
import { ArrowLeft, Plus, X } from "lucide-react";
import MathText from "../../Math";
import { api, type TaskType } from "@/lib/api";

export type AdminTask = {
  id?: number;
  slug?: string;
  task_type_id: number;
  task_type_number?: number;
  statement: string;
  image_url: string | null;
  answer_type: string;
  answer_value: string;
  answer_tolerance: string | null;
  answer_synonyms: string[];
  solution: string | null;
  hints: string[];
  difficulty: number;
  source: string | null;
  source_kind: string;
  source_year: number | null;
  source_ref: string | null;
  source_url: string | null;
  status: string;
};

export const EMPTY_TASK: AdminTask = {
  task_type_id: 0,
  statement: "",
  image_url: null,
  answer_type: "number",
  answer_value: "",
  answer_tolerance: null,
  answer_synonyms: [],
  solution: "",
  hints: [],
  difficulty: 3,
  source: null,
  source_kind: "own",
  source_year: null,
  source_ref: null,
  source_url: null,
  status: "draft",
};

const ANSWER_TYPES = [
  { value: "number", label: "Число", hint: "7 · −0,5 · 3.14" },
  { value: "number_tolerance", label: "Число с допуском", hint: "3,14 ± 0,01" },
  { value: "string", label: "Слово", hint: "регистр и «ё» не важны" },
  {
    value: "digits",
    label: "Последовательность цифр",
    hint: "1324, порядок важен",
  },
  { value: "multi", label: "Набор чисел", hint: "2;5;7, порядок не важен" },
];

const SOURCE_KINDS = [
  { value: "own", label: "Собственная" },
  { value: "exam", label: "Реальный ЕГЭ прошлых лет" },
  { value: "demo", label: "Демоверсия ФИПИ" },
  { value: "fipi", label: "Открытый банк ФИПИ" },
  { value: "book", label: "Сборник" },
  { value: "other", label: "Другое" },
];

export default function TaskForm({
  task,
  types,
  onDone,
  onCancel,
}: {
  task: AdminTask;
  types: TaskType[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<AdminTask>({
    ...task,
    task_type_id: task.task_type_id || types[0]?.id || 0,
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function set<K extends keyof AdminTask>(key: K, value: AdminTask[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function save() {
    setSaving(true);
    setError("");
    try {
      const body = {
        task_type_id: form.task_type_id,
        statement: form.statement,
        image_url: form.image_url || null,
        answer_type: form.answer_type,
        answer_value: form.answer_value,
        answer_tolerance: form.answer_tolerance || null,
        answer_synonyms: form.answer_synonyms,
        solution: form.solution || null,
        hints: form.hints.filter((h) => h.trim()),
        difficulty: form.difficulty,
        source: form.source || null,
        source_kind: form.source_kind,
        source_year: form.source_year,
        source_ref: form.source_ref || null,
        source_url: form.source_url || null,
        status: form.status,
      };
      await api(form.id ? `/api/admin/tasks/${form.id}` : "/api/admin/tasks", {
        method: form.id ? "PUT" : "POST",
        body: JSON.stringify(body),
      });
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between gap-4">
        <button
          className="muted flex items-center gap-2 text-sm"
          onClick={onCancel}
        >
          <ArrowLeft size={16} /> К списку
        </button>
        <h1 className="text-2xl">
          {form.id ? `Правка ${form.slug}` : "Новая задача"}
        </h1>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-5">
          <Field label="Номер задания">
            <select
              className="input"
              value={form.task_type_id}
              onChange={(e) => set("task_type_id", Number(e.target.value))}
            >
              {types.map((t) => (
                <option key={t.id} value={t.id}>
                  № {t.number} — {t.title}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Условие" hint="формулы в долларах: $x^2 + 1$">
            <textarea
              className="input"
              rows={4}
              value={form.statement}
              onChange={(e) => set("statement", e.target.value)}
            />
          </Field>

          <Field label="Разбор" hint="обязателен для публикации">
            <textarea
              className="input"
              rows={4}
              value={form.solution ?? ""}
              onChange={(e) => set("solution", e.target.value)}
            />
          </Field>

          <Field label="Подсказки">
            <div className="space-y-2">
              {form.hints.map((hint, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    className="input"
                    value={hint}
                    onChange={(e) =>
                      set(
                        "hints",
                        form.hints.map((h, j) =>
                          i === j ? e.target.value : h,
                        ),
                      )
                    }
                  />
                  <button
                    className="btn-ghost px-3"
                    onClick={() =>
                      set(
                        "hints",
                        form.hints.filter((_, j) => j !== i),
                      )
                    }
                    aria-label="Удалить подсказку"
                  >
                    <X size={15} />
                  </button>
                </div>
              ))}
              <button
                className="btn-ghost text-sm"
                onClick={() => set("hints", [...form.hints, ""])}
              >
                <Plus size={14} /> Добавить подсказку
              </button>
            </div>
          </Field>

          <Field
            label="Ссылка на картинку"
            hint="для геометрии и графиков; пока просто URL"
          >
            <input
              className="input"
              value={form.image_url ?? ""}
              onChange={(e) => set("image_url", e.target.value)}
            />
          </Field>
        </div>

        <aside className="space-y-5">
          <Field label="Тип ответа">
            <select
              className="input"
              value={form.answer_type}
              onChange={(e) => set("answer_type", e.target.value)}
            >
              {ANSWER_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <p className="muted mt-1 text-xs">
              {ANSWER_TYPES.find((t) => t.value === form.answer_type)?.hint}
            </p>
          </Field>

          <Field label="Правильный ответ">
            <input
              className="input"
              value={form.answer_value}
              onChange={(e) => set("answer_value", e.target.value)}
            />
          </Field>

          {form.answer_type === "number_tolerance" && (
            <Field label="Допуск">
              <input
                className="input"
                value={form.answer_tolerance ?? ""}
                onChange={(e) => set("answer_tolerance", e.target.value)}
              />
            </Field>
          )}

          {form.answer_type === "string" && (
            <Field label="Синонимы" hint="через запятую">
              <input
                className="input"
                value={form.answer_synonyms.join(", ")}
                onChange={(e) =>
                  set(
                    "answer_synonyms",
                    e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  )
                }
              />
            </Field>
          )}

          <Field label="Сложность">
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  onClick={() => set("difficulty", n)}
                  className={`pill flex-1 ${form.difficulty === n ? "pill-active" : "pill-idle"}`}
                  style={{ border: "1px solid var(--divider)" }}
                >
                  {n}
                </button>
              ))}
            </div>
          </Field>

          <Field
            label="Откуда задача"
            hint="показывается ученику мелким шрифтом"
          >
            <select
              className="input"
              value={form.source_kind}
              onChange={(e) => set("source_kind", e.target.value)}
            >
              {SOURCE_KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
          </Field>

          {form.source_kind !== "own" && (
            <>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Год">
                  <input
                    className="input"
                    inputMode="numeric"
                    value={form.source_year ?? ""}
                    onChange={(e) =>
                      set(
                        "source_year",
                        e.target.value ? Number(e.target.value) : null,
                      )
                    }
                  />
                </Field>
                <Field label="Номер в источнике">
                  <input
                    className="input"
                    value={form.source_ref ?? ""}
                    onChange={(e) => set("source_ref", e.target.value)}
                  />
                </Field>
              </div>
              <Field
                label="Подпись"
                hint="если пусто — соберём из года и номера"
              >
                <input
                  className="input"
                  placeholder="ЕГЭ 2024, основная волна"
                  value={form.source ?? ""}
                  onChange={(e) => set("source", e.target.value)}
                />
              </Field>
            </>
          )}

          <Field label="Статус">
            <select
              className="input"
              value={form.status}
              onChange={(e) => set("status", e.target.value)}
            >
              <option value="draft">Черновик</option>
              <option value="live">Опубликована</option>
              <option value="broken">Снята</option>
            </select>
          </Field>
        </aside>
      </div>

      <section className="card p-6">
        <p className="eyebrow mb-3">Предпросмотр</p>
        <MathText
          className="block text-lg leading-relaxed"
          text={form.statement || "…"}
        />
        {form.solution && (
          <div
            className="mt-4 border-t pt-3 text-sm"
            style={{ borderColor: "var(--divider)" }}
          >
            <MathText text={form.solution} />
          </div>
        )}
      </section>

      {error && (
        <p
          className="rounded-xl p-4 text-sm"
          style={{
            background: "var(--accent-2-100)",
            color: "var(--accent-2)",
          }}
        >
          {error}
        </p>
      )}

      <div className="flex gap-3">
        <button
          className="btn"
          onClick={save}
          disabled={saving || !form.statement.trim()}
        >
          {saving ? "Сохраняем…" : "Сохранить"}
        </button>
        <button className="btn-ghost" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="eyebrow mb-1.5 block">{label}</span>
      {children}
      {hint && <span className="muted mt-1 block text-xs">{hint}</span>}
    </label>
  );
}
