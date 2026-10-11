"use client";

import { useEffect, useRef, useState } from "react";
import { CalendarDays, Check, Clock, Coins, Timer, Trophy } from "lucide-react";
import MathText from "../../Math";
import TaskBody from "../../TaskBody";
import { api, notifyUserChanged } from "@/lib/api";
import { checkAchievements } from "@/lib/achievements";
import { playCorrect, playWrong } from "@/lib/sound";
import { plural } from "@/lib/exam";

type Daily = {
  day: string;
  task_id: number;
  task_type_number: number;
  task_type_title: string;
  statement: string;
  image_url: string | null;
  source: string | null;
  solved: boolean;
  started: boolean;
  seconds_left: number | null;
  limit_seconds: number;
  your_seconds: number | null;
  your_place: number | null;
  solved_today: number;
  reward: number;
  next_in_hours: number;
};

type Row = {
  place: number;
  user_id: number;
  display_name: string;
  seconds: number;
  is_you: boolean;
};

type Answer = {
  is_correct: boolean;
  expired: boolean;
  correct_answer: string;
  solution: string | null;
  coins: number;
  seconds: number;
  place: number | null;
};

export default function DailyPage() {
  const [daily, setDaily] = useState<Daily | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<Answer | null>(null);
  const [sending, setSending] = useState(false);
  /** Сколько осталось. Считает сервер: вкладку переключают и перезагружают,
      а от времени зависит место в таблице — клиентскому счётчику тут не место. */
  const [left, setLeft] = useState<number | null>(null);
  const [error, setError] = useState("");
  const deadline = useRef<number | null>(null);

  function apply(data: Daily) {
    setDaily(data);
    if (data.seconds_left === null) {
      deadline.current = null;
      setLeft(null);
    } else {
      deadline.current = Date.now() + data.seconds_left * 1000;
      setLeft(data.seconds_left);
    }
  }

  function load() {
    api<Daily>("/api/daily")
      .then(apply)
      .catch((e: Error) => setError(e.message));
    api<Row[]>("/api/daily/leaderboard")
      .then(setRows)
      .catch(() => setRows([]));
  }

  useEffect(load, []);

  // Обратный отсчёт до срока, полученного с сервера. Когда время вышло —
  // отправляем пустой ответ, чтобы попытка закрылась и показался разбор.
  useEffect(() => {
    if (deadline.current === null || result) return;

    const timer = setInterval(() => {
      const rest = Math.max(
        0,
        Math.round((deadline.current! - Date.now()) / 1000),
      );
      setLeft(rest);
      if (rest === 0) {
        clearInterval(timer);
        send("");
      }
    }, 500);

    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [daily?.started, result]);

  async function start() {
    try {
      apply(await api<Daily>("/api/daily/start", { method: "POST" }));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function send(value: string) {
    if (sending) return;
    setSending(true);
    try {
      const res = await api<Answer>("/api/daily/answer", {
        method: "POST",
        body: JSON.stringify({ answer: value }),
      });
      setResult(res);
      if (res.is_correct) {
        playCorrect();
        checkAchievements();
        notifyUserChanged();
        load();
      } else {
        playWrong();
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!answer.trim()) return;
    send(answer);
  }

  if (error && !daily)
    return <p style={{ color: "var(--accent-2)" }}>{error}</p>;
  if (!daily) return <p className="muted">Загрузка…</p>;

  const done = daily.solved || result?.is_correct;
  const started = daily.started;
  const timeUp = result?.expired || (left === 0 && !done);

  return (
    <div className="page">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <CalendarDays size={22} style={{ color: "var(--accent-2)" }} />
          <div>
            <h1 className="page-title">Задача дня</h1>
            <p className="page-subtitle">
              Одна на всех, новая каждый день. Место в таблице — по времени решения,
              так что думать лучше сразу набело.
            </p>
          </div>
        </div>
        <span className="muted shrink-0 text-sm">
          новая через {daily.next_in_hours} {plural(daily.next_in_hours, "час", "часа", "часов")}
        </span>
      </header>

      <article className="card space-y-5 p-7">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="rounded-full px-3 py-1 text-xs font-medium"
            style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
          >
            Задание № {daily.task_type_number}
          </span>
          <span className="muted text-sm">{daily.task_type_title}</span>
          <span className="ml-auto flex items-center gap-2">
            {started && !done && left !== null && (
              <span
                className="h inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm"
                style={
                  left <= 60
                    ? { background: "var(--accent-2-100)", color: "var(--accent-2)" }
                    : { background: "var(--accent-100)", color: "var(--accent-700)" }
                }
              >
                <Timer size={13} /> {formatClock(left)}
              </span>
            )}
            <span
              className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs"
              style={{ background: "var(--gold-bg)", color: "var(--gold)" }}
            >
              <Coins size={13} /> {daily.reward} за решение
            </span>
          </span>
        </div>

        {started || done ? (
          <>
            <TaskBody
              className="text-lg"
              statement={daily.statement}
              imageUrl={daily.image_url}
            />
            {daily.source && (
              <p className="muted text-xs">Источник: {daily.source}</p>
            )}
          </>
        ) : (
          <div
            className="flex flex-col items-center gap-3 rounded-xl px-6 py-10 text-center"
            style={{ background: "var(--surface)" }}
          >
            <Timer size={26} style={{ color: "var(--accent)" }} />
            <p className="max-w-sm leading-relaxed">
              Условие откроется по кнопке, и сразу пойдёт время — на решение
              {" "}
              {Math.round(daily.limit_seconds / 60)} минут. В таблицу идёт первая
              попытка, так что решать лучше набело.
            </p>
            <button className="btn mt-1" onClick={start}>
              Начать
            </button>
          </div>
        )}

        {done ? (
          <div
            className="coin-fly rounded-xl p-4"
            style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
          >
            <p className="flex flex-wrap items-center gap-2 font-semibold">
              <Check size={17} /> Решено
              {(result?.seconds ?? daily.your_seconds) !== null && (
                <span className="font-normal">
                  за {result?.seconds ?? daily.your_seconds} с
                </span>
              )}
              {(result?.place ?? daily.your_place) && (
                <span className="font-normal">
                  · {result?.place ?? daily.your_place} место
                </span>
              )}
            </p>
            <p className="muted mt-1 text-sm">Возвращайся завтра — задача сменится.</p>
          </div>
        ) : started && !timeUp ? (
          <form className="flex flex-wrap gap-3" onSubmit={submit} noValidate>
            <input
              className="input flex-1"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Ответ"
              autoFocus
            />
            <button className="btn" disabled={sending}>
              {sending ? "Проверяем…" : "Ответить"}
            </button>
          </form>
        ) : null}

        {result && !result.is_correct && (
          <div
            className="rounded-xl p-4 text-sm"
            style={{ background: "var(--accent-2-100)", color: "var(--accent-2)" }}
          >
            <p className="font-semibold">
              {result.expired
                ? `Время вышло. Правильный ответ: ${result.correct_answer}`
                : `Неверно. Правильный ответ: ${result.correct_answer}`}
            </p>
            {result.solution && (
              <div className="mt-2 leading-relaxed" style={{ color: "var(--text)" }}>
                <MathText text={result.solution} />
              </div>
            )}
          </div>
        )}
      </article>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="section-title flex items-center gap-2">
            <Trophy size={18} style={{ color: "var(--accent-2)" }} /> Кто быстрее
          </h2>
          <span className="muted text-sm">
            решили сегодня: {daily.solved_today}
          </span>
        </div>

        {rows.length === 0 ? (
          <p className="muted text-sm">Сегодня ещё никто не решил — можно быть первым.</p>
        ) : (
          <ul className="space-y-2">
            {rows.map((row) => (
              <li
                key={row.user_id}
                className="card flex items-center gap-3 p-3 text-sm"
                style={row.is_you ? { background: "var(--accent-100)" } : undefined}
              >
                <span className="h w-6 text-center">{row.place}</span>
                <span className="min-w-0 flex-1 truncate">{row.display_name}</span>
                <span className="muted flex items-center gap-1">
                  <Clock size={13} /> {row.seconds} с
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function formatClock(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}
