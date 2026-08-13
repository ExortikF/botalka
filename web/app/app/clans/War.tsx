"use client";

import { useEffect, useState } from "react";
import { Check, Coins, Send, Swords } from "lucide-react";
import MathText from "../../Math";
import { api } from "@/lib/api";
import { playCorrect, playWrong } from "@/lib/sound";
import { formatFull, useCountdown } from "../tournaments/Countdown";
import type { War as WarType } from "./types";

/**
 * Экран войны кланов: набор задач общий, очко даёт тот, кто закрыл задачу
 * первым в своём клане. Решённое соперником видно сразу — это и создаёт гонку.
 */
export default function War({
  war,
  onChange,
}: {
  war: WarType;
  onChange: () => void;
}) {
  const [current, setCurrent] = useState<number | null>(null);
  const [answer, setAnswer] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  const left = useCountdown(war.seconds_left);

  useEffect(() => {
    if (left === 0) onChange();
  }, [left, onChange]);

  const task = war.tasks.find((t) => t.task_id === current) ?? null;
  const leading = war.us.score > war.them.score;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!task || sending || !answer.trim()) return;
    setSending(true);
    setMessage("");
    try {
      const res = await api<{ is_correct: boolean; already: boolean }>(
        `/api/clans/wars/${war.id}/answer`,
        { method: "POST", body: JSON.stringify({ task_id: task.task_id, answer }) },
      );
      if (res.already) setMessage("Эту задачу уже закрыл кто-то из наших");
      else if (res.is_correct) {
        setMessage("Верно — очко клану");
        playCorrect();
      } else {
        setMessage("Неверно, попробуй ещё");
        playWrong();
      }
      setAnswer("");
      onChange();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="space-y-3">
      <div
        className="relative overflow-hidden text-white"
        style={{
          borderRadius: "var(--radius-lg)",
          padding: "26px 28px",
          backgroundImage: `linear-gradient(120deg, ${war.us.color}, ${war.them.color})`,
        }}
      >
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div className="text-center">
            <p className="text-xs uppercase tracking-wider opacity-80">
              {war.us.tag}
            </p>
            <p className="h text-4xl">{war.us.score}</p>
          </div>

          <div className="text-center">
            <Swords size={22} className="mx-auto" />
            {war.state === "active" && left !== null ? (
              <>
                <p className="h mt-2 text-2xl">{formatFull(left)}</p>
                <p className="text-xs opacity-80">до конца войны</p>
              </>
            ) : (
              <p className="h mt-2 text-xl">
                {war.winner === "мы"
                  ? "Победа"
                  : war.winner === "они"
                    ? "Поражение"
                    : "Ничья"}
              </p>
            )}
            <p className="mt-1 flex items-center justify-center gap-1 text-xs opacity-90">
              <Coins size={12} /> банк {war.prize}
            </p>
          </div>

          <div className="text-center">
            <p className="text-xs uppercase tracking-wider opacity-80">
              {war.them.tag}
            </p>
            <p className="h text-4xl">{war.them.score}</p>
          </div>
        </div>
      </div>

      {war.state === "active" && (
        <p className="muted text-sm">
          {leading
            ? "Ведём. Очко даёт задача, которую ещё не закрыл никто из наших."
            : "Задачи общие: чем больше разных закроете, тем лучше. Решать одно и то же вдвоём смысла нет."}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,320px)_1fr]">
        <ul className="space-y-1.5">
          {war.tasks.map((item, index) => (
            <li key={item.task_id}>
              <button
                className="flex w-full items-center gap-2 rounded-xl border p-2.5 text-left text-sm"
                style={{
                  borderColor:
                    item.task_id === current ? "var(--accent-300)" : "var(--divider)",
                  background: item.solved_by_us
                    ? "var(--accent-100)"
                    : item.task_id === current
                      ? "var(--surface)"
                      : "var(--card)",
                }}
                onClick={() => {
                  setCurrent(item.task_id);
                  setMessage("");
                  setAnswer("");
                }}
              >
                <span className="h w-6 shrink-0 text-center">{index + 1}</span>
                <span className="muted w-10 shrink-0 text-xs">№ {item.number}</span>
                <span className="min-w-0 flex-1 truncate">{item.title}</span>

                {item.solved_by_us && (
                  <Check size={15} style={{ color: "var(--accent)" }} />
                )}
                {item.solved_by_them && !item.solved_by_us && (
                  <span className="text-xs" style={{ color: "var(--accent-2)" }}>
                    у них
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>

        {task ? (
          <article className="card space-y-5 p-7">
            <div className="flex flex-wrap items-center gap-2">
              <span className="muted text-sm">
                № {task.number} · {task.title}
              </span>
              {task.solved_by_them && (
                <span
                  className="rounded-full px-2.5 py-1 text-xs"
                  style={{ background: "var(--accent-2-100)", color: "var(--accent-2)" }}
                >
                  соперник уже закрыл
                </span>
              )}
            </div>

            <MathText
              className="block text-lg leading-relaxed"
              text={task.statement}
            />

            {task.solved_by_us ? (
              <p
                className="rounded-xl p-4 font-semibold"
                style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
              >
                <Check size={17} className="inline" /> Закрыта
                {task.solver && ` — ${task.solver}`}
              </p>
            ) : war.can_answer ? (
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
            ) : null}

            {message && (
              <p className="rounded-xl p-3 text-sm" style={{ background: "var(--surface)" }}>
                {message}
              </p>
            )}
          </article>
        ) : (
          <p className="muted text-sm">Выбери задачу слева.</p>
        )}
      </div>
    </section>
  );
}
