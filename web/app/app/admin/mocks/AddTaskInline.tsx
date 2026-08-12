"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";
import MathText from "../../../Math";
import { api, type TaskType } from "@/lib/api";

/**
 * Написать задачу прямо в конструкторе пробника и сразу вставить её в вариант.
 *
 * Задача при этом попадает в общий банк — иначе она будет жить только внутри
 * одного пробника, и найти её потом будет негде. Черновик (не публиковать)
 * оставлен для случая «нужна только в этом варианте».
 */

export type CreatedTask = {
  id: number;
  number: number;
  statement: string;
  answer_value: string;
  difficulty: number;
};

const ANSWER_TYPES = [
  { value: "number", label: "Число", hint: "7 · −0,5 · 3.14" },
  { value: "number_tolerance", label: "Число с допуском", hint: "3,14 ± 0,01" },
  { value: "string", label: "Слово", hint: "регистр и «ё» не важны" },
  { value: "digits", label: "Последовательность цифр", hint: "1324, порядок важен" },
  { value: "multi", label: "Набор чисел", hint: "2;5;7, порядок не важен" },
];

export default function AddTaskInline({
  types,
  onCreated,
}: {
  types: TaskType[];
  onCreated: (task: CreatedTask) => void;
}) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [typeId, setTypeId] = useState<number>(0);
  const [statement, setStatement] = useState("");
  const [answerType, setAnswerType] = useState("number");
  const [answerValue, setAnswerValue] = useState("");
  const [tolerance, setTolerance] = useState("");
  const [solution, setSolution] = useState("");
  const [difficulty, setDifficulty] = useState(3);
  const [publish, setPublish] = useState(true);

  const chosenType = types.find((t) => t.id === (typeId || types[0]?.id));

  async function save() {
    setSaving(true);
    setError("");
    try {
      const created = await api<{
        id: number;
        task_type_number: number;
        statement: string;
        answer_value: string;
        difficulty: number;
      }>("/api/admin/tasks", {
        method: "POST",
        body: JSON.stringify({
          task_type_id: typeId || types[0]?.id,
          statement,
          answer_type: answerType,
          answer_value: answerValue,
          answer_tolerance: answerType === "number_tolerance" ? tolerance : null,
          solution: solution || null,
          difficulty,
          status: publish ? "live" : "draft",
        }),
      });

      onCreated({
        id: created.id,
        number: created.task_type_number,
        statement: created.statement,
        answer_value: created.answer_value,
        difficulty: created.difficulty,
      });

      setStatement("");
      setAnswerValue("");
      setSolution("");
      setTolerance("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!open)
    return (
      <button className="btn-ghost text-sm" onClick={() => setOpen(true)}>
        <Plus size={15} /> Написать свою задачу
      </button>
    );

  return (
    <section
      className="space-y-3 rounded-xl p-4"
      style={{ background: "var(--surface)" }}
    >
      <div className="flex items-center justify-between">
        <p className="font-medium">Новая задача — сразу в этот вариант</p>
        <button className="muted" onClick={() => setOpen(false)} aria-label="Свернуть">
          <X size={16} />
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="eyebrow mb-1.5 block">Номер задания</span>
          <select
            className="input"
            value={typeId || types[0]?.id || ""}
            onChange={(e) => setTypeId(Number(e.target.value))}
          >
            {types.map((t) => (
              <option key={t.id} value={t.id}>
                № {t.number} — {t.title}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="eyebrow mb-1.5 block">Тип ответа</span>
          <select
            className="input"
            value={answerType}
            onChange={(e) => setAnswerType(e.target.value)}
          >
            {ANSWER_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <span className="muted mt-1 block text-xs">
            {ANSWER_TYPES.find((t) => t.value === answerType)?.hint}
          </span>
        </label>
      </div>

      <label className="block">
        <span className="eyebrow mb-1.5 block">Условие</span>
        <textarea
          className="input"
          rows={3}
          placeholder="Формулы в долларах: $x^2 + 1$"
          value={statement}
          onChange={(e) => setStatement(e.target.value)}
        />
      </label>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="eyebrow mb-1.5 block">Правильный ответ</span>
          <input
            className="input"
            value={answerValue}
            onChange={(e) => setAnswerValue(e.target.value)}
          />
        </label>

        {answerType === "number_tolerance" ? (
          <label className="block">
            <span className="eyebrow mb-1.5 block">Допуск</span>
            <input
              className="input"
              value={tolerance}
              onChange={(e) => setTolerance(e.target.value)}
            />
          </label>
        ) : (
          <label className="block">
            <span className="eyebrow mb-1.5 block">Сложность</span>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  onClick={() => setDifficulty(n)}
                  className={`pill flex-1 ${difficulty === n ? "pill-active" : "pill-idle"}`}
                  style={{ border: "1px solid var(--divider)" }}
                >
                  {n}
                </button>
              ))}
            </div>
          </label>
        )}
      </div>

      <label className="block">
        <span className="eyebrow mb-1.5 block">Разбор</span>
        <textarea
          className="input"
          rows={2}
          value={solution}
          onChange={(e) => setSolution(e.target.value)}
        />
        <span className="muted mt-1 block text-xs">
          Обязателен, если задача публикуется в банке
        </span>
      </label>

      {statement && (
        <div className="rounded-xl p-3" style={{ background: "var(--card)" }}>
          <p className="eyebrow mb-1">Предпросмотр</p>
          <MathText className="block" text={statement} />
        </div>
      )}

      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={publish} onChange={(e) => setPublish(e.target.checked)} />
        Добавить в общий банк {chosenType && `(номер ${chosenType.number})`}
      </label>

      <button
        className="btn"
        onClick={save}
        disabled={saving || statement.trim().length < 3 || !answerValue.trim()}
      >
        {saving ? "Сохраняем…" : "Добавить в вариант"}
      </button>

      {error && (
        <p className="text-sm" style={{ color: "var(--accent-2)" }}>
          {error}
        </p>
      )}
    </section>
  );
}
