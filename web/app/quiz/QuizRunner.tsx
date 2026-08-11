"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import MathText from "../Math";
import {
  getQuizResult,
  sendAnswer,
  startQuiz,
  type AnswerResult,
  type Quiz,
  type QuizResult,
} from "@/lib/api";

type Phase = "loading" | "playing" | "finished" | "error";

export default function QuizRunner({ taskType, length }: { taskType?: number; length: number }) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState("");
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<AnswerResult | null>(null);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [hintsShown, setHintsShown] = useState(0);
  const [sending, setSending] = useState(false);

  const startedAt = useRef(Date.now());
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    startQuiz(taskType, length)
      .then((q) => {
        setQuiz(q);
        setPhase("playing");
        startedAt.current = Date.now();
      })
      .catch((e: Error) => {
        setError(e.message);
        setPhase("error");
      });
  }, [taskType, length]);

  useEffect(() => {
    if (phase === "playing" && !feedback) inputRef.current?.focus();
  }, [phase, feedback, index]);

  const task = quiz?.tasks[index];

  async function submit() {
    if (!quiz || !task || sending || !answer.trim()) return;
    setSending(true);
    try {
      const res = await sendAnswer(quiz.id, task.id, answer, Date.now() - startedAt.current);
      setFeedback(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  }

  async function next() {
    if (!quiz) return;
    if (index + 1 < quiz.tasks.length) {
      setIndex(index + 1);
      setAnswer("");
      setFeedback(null);
      setHintsShown(0);
      startedAt.current = Date.now();
      return;
    }
    setResult(await getQuizResult(quiz.id));
    setPhase("finished");
  }

  if (phase === "loading") return <p className="muted">Собираем квиз…</p>;

  if (phase === "error")
    return (
      <div className="space-y-4">
        <p className="text-wrong">{error}</p>
        <Link className="btn-outline" href="/">
          На главную
        </Link>
      </div>
    );

  if (phase === "finished" && result) return <Result result={result} />;

  if (!quiz || !task) return null;

  const progress = ((index + (feedback ? 1 : 0)) / quiz.tasks.length) * 100;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between text-sm">
        <Link className="muted hover:underline" href="/">
          ← Выйти
        </Link>
        <span className="muted">
          Задача {index + 1} из {quiz.tasks.length}
        </span>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--border)]">
        <div
          className="h-full rounded-full bg-accent transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <article className="card space-y-4 p-6">
        <p className="muted text-xs uppercase tracking-wide">
          Задание {task.task_type_number} · {task.task_type_title}
        </p>

        <MathText className="block text-lg leading-relaxed" text={task.statement} />

        {task.hints.slice(0, hintsShown).map((hint, i) => (
          <p key={i} className="rounded-lg bg-[var(--border)]/40 p-3 text-sm">
            <MathText text={hint} />
          </p>
        ))}

        {!feedback && hintsShown < task.hints.length && (
          <button className="muted text-sm underline" onClick={() => setHintsShown(hintsShown + 1)}>
            Показать подсказку
          </button>
        )}

        {!feedback ? (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <input
              ref={inputRef}
              className="input"
              placeholder="Ответ"
              value={answer}
              inputMode="text"
              onChange={(e) => setAnswer(e.target.value)}
            />
            <button className="btn" type="submit" disabled={sending || !answer.trim()}>
              Ответить
            </button>
          </form>
        ) : (
          <div className="space-y-3">
            <p className={feedback.is_correct ? "text-correct" : "text-wrong"}>
              {feedback.is_correct ? "Верно" : `Неверно. Правильный ответ: ${feedback.correct_answer}`}
            </p>
            {!feedback.is_correct && feedback.solution && (
              <div className="rounded-lg border border-[var(--border)] p-4 text-sm leading-relaxed">
                <p className="muted mb-2 text-xs uppercase tracking-wide">Разбор</p>
                <MathText text={feedback.solution} />
              </div>
            )}
            <button className="btn" onClick={next} autoFocus>
              {index + 1 < quiz.tasks.length ? "Дальше" : "Результат"}
            </button>
          </div>
        )}
      </article>
    </div>
  );
}

function Result({ result }: { result: QuizResult }) {
  const percent = Math.round((result.score / result.total) * 100);
  const wrong = result.items.filter((i) => !i.is_correct);

  return (
    <div className="space-y-6">
      <section className="card p-6 text-center">
        <p className="text-5xl font-bold">
          {result.score}
          <span className="muted text-3xl"> / {result.total}</span>
        </p>
        <p className="muted mt-2">
          {percent}% верно
          {result.streak_days > 0 && ` · серия ${result.streak_days} дн.`}
        </p>
        <div className="mt-5 flex justify-center gap-3">
          <Link className="btn" href="/quiz">
            Ещё квиз
          </Link>
          <Link className="btn-outline" href="/">
            На главную
          </Link>
        </div>
      </section>

      {wrong.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-semibold">Разбор ошибок</h2>
          {wrong.map((item) => (
            <article key={item.task_id} className="card space-y-2 p-5 text-sm">
              <p className="muted text-xs uppercase tracking-wide">
                Задание {item.task_type_number}
              </p>
              <MathText className="block" text={item.statement} />
              <p>
                <span className="text-wrong">Ваш ответ: {item.your_answer || "—"}</span>
                {" · "}
                <span className="text-correct">верный: {item.correct_answer}</span>
              </p>
              {item.solution && (
                <div className="border-t border-[var(--border)] pt-2 leading-relaxed">
                  <MathText text={item.solution} />
                </div>
              )}
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
