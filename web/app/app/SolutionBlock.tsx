"use client";

import { useState } from "react";
import { PenLine } from "lucide-react";
import MathText from "../Math";
import { api } from "@/lib/api";

/**
 * Разбор задачи — или честное признание, что его нет.
 *
 * Часть банка приехала из открытого банка ФИПИ: там есть условия, но нет ни
 * ответов, ни разборов. Ответы мы считаем и перепроверяем сами, а разбор
 * получается не всегда — и выдумывать его нельзя. Пустого места здесь тоже
 * быть не должно: человек только что ошибся и ждёт объяснения, поэтому пишем
 * прямо, что разбора пока нет, и даём предложить свой.
 *
 * Предложение уходит той же ручкой, что и жалоба на задачу: админка у неё уже
 * есть, заводить вторую очередь ради этого незачем.
 */
export default function SolutionBlock({
  solution,
  taskId,
}: {
  solution: string | null;
  taskId?: number;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  if (solution) {
    return (
      <div
        className="rounded-xl border p-4"
        style={{ borderColor: "var(--divider)" }}
      >
        <p className="eyebrow mb-2">Разбор</p>
        <MathText text={solution} />
      </div>
    );
  }

  async function send() {
    if (text.trim().length < 10) {
      setError("Напиши хотя бы пару предложений — иначе разбор не поможет");
      return;
    }
    try {
      await api(`/api/tasks/${taskId}/report`, {
        method: "POST",
        body: JSON.stringify({
          message: `Разбор от ученика:\n${text.trim()}`,
          given_answer: null,
        }),
      });
      setSent(true);
      setOpen(false);
      setText("");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div
      className="rounded-xl border p-4"
      style={{ borderColor: "var(--divider)", background: "var(--surface)" }}
    >
      <p className="eyebrow mb-1">Разбор</p>
      <p className="muted text-sm">
        Разбора к этой задаче пока нет — сорян. Ответ проверен, а объяснение
        ещё не написали.
      </p>

      {sent && (
        <p className="mt-2 text-sm" style={{ color: "var(--accent-700)" }}>
          Спасибо! Посмотрим и добавим — с твоим именем в благодарностях.
        </p>
      )}

      {!sent && taskId !== undefined && !open && (
        <button
          className="btn-ghost btn-ghost-2 mt-3 text-sm"
          onClick={() => setOpen(true)}
        >
          <PenLine size={14} /> Предложить разбор
        </button>
      )}

      {open && (
        <div className="mt-3 space-y-2">
          <textarea
            className="input w-full"
            rows={4}
            autoFocus
            placeholder="Как ты решал эту задачу? Достаточно по шагам, формулы можно словами."
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setError("");
            }}
          />
          {error && (
            <p className="text-xs" style={{ color: "var(--accent-2)" }}>
              {error}
            </p>
          )}
          <div className="flex gap-2">
            <button className="btn text-sm" onClick={send}>
              Отправить
            </button>
            <button
              className="btn-ghost text-sm"
              onClick={() => {
                setOpen(false);
                setError("");
              }}
            >
              Отмена
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
