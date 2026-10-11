"use client";

import { useEffect, useState } from "react";
import { Check, Clock, Send, Users } from "lucide-react";
import MathText from "../../../Math";
import TaskBody from "../../../TaskBody";
import { api } from "@/lib/api";
import { playCorrect, playWrong } from "@/lib/sound";
import type { SubmitResult, Tournament } from "../types";
import { formatFull, useCountdown } from "../Countdown";

/**
 * Экран контеста: слева список задач, справа выбранная задача с полем ответа.
 * Условия приходят с сервера только после старта, поэтому до начала здесь
 * показывается обратный отсчёт, а не пустые карточки.
 */
export default function Contest({
  data,
  onReload,
}: {
  data: Tournament;
  onReload: () => void;
}) {
  const [current, setCurrent] = useState<string | null>(
    data.problems.find((p) => !p.solved)?.letter ?? data.problems[0]?.letter ?? null,
  );
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const left = useCountdown(
    data.started ? data.seconds_left : data.seconds_to_start,
  );

  // Ноль означает смену фазы: контест начался или кончился — перечитываем.
  useEffect(() => {
    if (left === 0) onReload();
  }, [left, onReload]);

  const problem = data.problems.find((p) => p.letter === current) ?? null;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!problem || sending || !answer.trim()) return;
    setSending(true);
    setError("");
    try {
      const res = await api<SubmitResult>(`/api/tournaments/${data.id}/submit`, {
        method: "POST",
        body: JSON.stringify({ task_id: problem.task_id, answer }),
      });
      setResult(res);
      setAnswer("");
      if (res.is_correct) playCorrect();
      else playWrong();
      onReload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  }

  if (!data.started)
    return (
      <section className="card flex flex-col items-center gap-3 p-10 text-center">
        <Clock size={26} style={{ color: "var(--accent)" }} />
        <p className="h text-4xl">{left !== null ? formatFull(left) : "—"}</p>
        <p className="muted max-w-sm leading-relaxed">
          До старта. Задачи откроются у всех одновременно — набор до начала
          не показывается никому.
        </p>
      </section>
    );

  return (
    <>
      {!data.over && left !== null && (
        <section
          className="card flex flex-wrap items-center justify-between gap-4 p-5"
          style={{ borderColor: left <= 300 ? "var(--accent-2-200)" : undefined }}
        >
          <span className="eyebrow">До конца контеста</span>
          <span
            className="h text-3xl"
            style={{ color: left <= 300 ? "var(--accent-2)" : undefined }}
          >
            {formatFull(left)}
          </span>
        </section>
      )}

      {data.over && (
        <p
          className="rounded-xl p-4 text-sm"
          style={{ background: "var(--surface)" }}
        >
          Контест закончился. Задачи остались открытыми — можно дорешать, но в
          таблицу такие ответы не идут.
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-[210px_1fr]">
        <ul className="flex gap-2 lg:flex-col">
          {data.problems.map((item) => (
            <li key={item.letter} className="flex-1">
              <button
                className="w-full rounded-2xl border p-3 text-left transition"
                style={{
                  borderColor: item.solved
                    ? "var(--accent)"
                    : item.letter === current
                      ? "var(--accent-300)"
                      : "var(--divider)",
                  background:
                    item.letter === current ? "var(--accent-100)" : "var(--card)",
                }}
                onClick={() => {
                  setCurrent(item.letter);
                  setResult(null);
                  setAnswer("");
                }}
              >
                <span className="flex items-center justify-between">
                  <span className="h text-lg">{item.letter}</span>
                  {item.solved ? (
                    <Check size={16} style={{ color: "var(--accent)" }} />
                  ) : item.wrong > 0 ? (
                    <span className="text-xs" style={{ color: "var(--accent-2)" }}>
                      −{item.wrong}
                    </span>
                  ) : null}
                </span>
                <span className="muted mt-0.5 block text-xs">
                  {item.points} баллов
                </span>
                <span className="muted flex items-center gap-1 text-xs">
                  <Users size={11} /> {item.solved_count}
                </span>
              </button>
            </li>
          ))}
        </ul>

        {problem && (
          <article className="card space-y-5 p-7">
            <div className="flex flex-wrap items-center gap-2">
              <span className="h text-xl">Задача {problem.letter}</span>
              <span
                className="rounded-full px-3 py-1 text-xs font-medium"
                style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
              >
                {problem.points} баллов
              </span>
              <span className="muted text-sm">
                № {problem.task_type_number} · {problem.task_type_title}
              </span>
            </div>

            <TaskBody
              className="text-lg"
              statement={problem.statement}
              imageUrl={problem.image_url}
            />

            {problem.solved ? (
              <p
                className="rounded-xl p-4 font-semibold"
                style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
              >
                <Check size={17} className="inline" /> Решено
                {problem.minute !== null && ` на ${problem.minute}-й минуте`}
                {problem.wrong > 0 && ` · неверных попыток: ${problem.wrong}`}
              </p>
            ) : (
              <form className="flex flex-wrap gap-3" onSubmit={submit} noValidate>
                <input
                  className="input flex-1"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Ответ"
                  autoFocus
                />
                <button className="btn" disabled={sending}>
                  <Send size={15} /> {sending ? "Проверяем…" : "Сдать"}
                </button>
              </form>
            )}

            {result && (
              <p
                className="rounded-xl p-4 text-sm"
                style={{
                  background: result.is_correct
                    ? "var(--accent-100)"
                    : "var(--accent-2-100)",
                  color: result.is_correct ? "var(--accent-700)" : "var(--accent-2)",
                }}
              >
                {result.message}
              </p>
            )}

            {error && (
              <p className="text-sm" style={{ color: "var(--accent-2)" }}>
                {error}
              </p>
            )}

            {!data.over && !problem.solved && (
              <p className="muted text-xs">
                Каждая неверная попытка добавит {data.penalty_minutes} минут штрафа,
                но только если задачу в итоге решишь.
              </p>
            )}
          </article>
        )}
      </div>
    </>
  );
}
