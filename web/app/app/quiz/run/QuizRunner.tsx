"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Lightbulb, PenLine, X } from "lucide-react";
import MathText from "../../../Math";
import DrawingPad, { type Stroke } from "../../DrawingPad";
import ReportButton from "../../ReportButton";
import { playCorrect, playWrong } from "@/lib/sound";
import {
  getQuizResult,
  playDuel,
  sendAnswer,
  startQuiz,
  type AnswerResult,
  type Quiz,
  type QuizPreset,
  type QuizResult,
} from "@/lib/api";

type Phase = "loading" | "playing" | "finished" | "error";

/** Что мы знаем про каждую задачу квиза на клиенте. */
type Slot = {
  answer: string;
  hintsShown: number;
  result: AnswerResult | null;
};

type Props = {
  subject: string;
  taskTypeIds: number[];
  selection: { task_type_id: number; count?: number; easy?: number; medium?: number; hard?: number }[];
  preset: QuizPreset | null;
  length: number;
  /** Если задан — это прохождение дуэли: задачи берутся из неё, а не собираются заново. */
  duelCode?: string;
};

export default function QuizRunner({
  subject,
  taskTypeIds,
  selection,
  preset,
  length,
  duelCode,
}: Props) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState("");
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [slots, setSlots] = useState<Record<number, Slot>>({});
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [sending, setSending] = useState(false);
  const [draftOpen, setDraftOpen] = useState(false);
  // черновик общий на весь квиз: при переходе к следующей задаче он остаётся
  // черновик свой у каждого задания: ключ — id задачи
  const [drafts, setDrafts] = useState<Record<number, Stroke[]>>({});

  const startedAt = useRef(Date.now());
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const starting = duelCode
      ? playDuel(duelCode)
      : startQuiz({ subject, taskTypeIds, selection, preset, length });

    starting
      .then((q) => {
        setQuiz(q);
        setSlots(
          Object.fromEntries(q.tasks.map((t) => [t.id, { answer: "", hintsShown: 0, result: null }])),
        );
        setPhase("playing");
        startedAt.current = Date.now();
      })
      .catch((e: Error) => {
        setError(e.message);
        setPhase("error");
      });
    // taskTypeIds приходит новым массивом на каждый рендер — сравниваем по строке,
    // иначе эффект перезапускается и создаёт новый квиз
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subject, taskTypeIds.join(","), JSON.stringify(selection), preset, length, duelCode]);

  const task = quiz?.tasks[index];
  const slot = task ? slots[task.id] : undefined;

  useEffect(() => {
    if (phase === "playing" && slot && !slot.result) inputRef.current?.focus();
  }, [phase, index, slot]);

  const patch = useCallback((taskId: number, next: Partial<Slot>) => {
    setSlots((prev) => ({ ...prev, [taskId]: { ...prev[taskId], ...next } }));
  }, []);

  const goTo = useCallback((i: number) => {
    setIndex(i);
    startedAt.current = Date.now();
  }, []);

  /** Следующая незаполненная задача — так работают и «Пропустить», и «Дальше». */
  const goNextUnanswered = useCallback(() => {
    if (!quiz) return false;
    for (let step = 1; step <= quiz.tasks.length; step++) {
      const i = (index + step) % quiz.tasks.length;
      if (!slots[quiz.tasks[i].id]?.result) {
        goTo(i);
        return true;
      }
    }
    return false;
  }, [quiz, index, slots, goTo]);

  async function submit() {
    if (!quiz || !task || !slot || sending || !slot.answer.trim()) return;
    setSending(true);
    try {
      const res = await sendAnswer(
        quiz.id,
        task.id,
        slot.answer,
        Date.now() - startedAt.current,
        slot.hintsShown > 0,
      );
      patch(task.id, { result: res });
      if (res.is_correct) playCorrect();
      else playWrong();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  }

  async function finish() {
    if (!quiz) return;
    if (duelCode) {
      window.location.href = `/app/duels/${duelCode}`;
      return;
    }
    setResult(await getQuizResult(quiz.id));
    setPhase("finished");
  }

  if (phase === "loading") return <p className="muted">Собираем квиз…</p>;

  if (phase === "error")
    return (
      <div className="space-y-4">
        <p style={{ color: "var(--accent-2)" }}>{error}</p>
        <Link className="btn-ghost" href="/app">
          На главную
        </Link>
      </div>
    );

  if (phase === "finished" && result) return <Result result={result} />;
  if (!quiz || !task || !slot) return null;

  const answeredCount = quiz.tasks.filter((t) => slots[t.id]?.result).length;
  const allAnswered = answeredCount === quiz.tasks.length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link
          className="muted flex items-center gap-1.5 text-sm hover:underline"
          href={duelCode ? `/app/duels/${duelCode}` : "/app/quiz"}
        >
          <X size={16} /> Выйти
        </Link>
        <span className="eyebrow">
          Вопрос {index + 1} из {quiz.tasks.length}
        </span>
      </div>

      <div
        className="h-1.5 w-full overflow-hidden rounded-full"
        style={{ background: "var(--divider)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${(answeredCount / quiz.tasks.length) * 100}%`,
            background: "var(--accent)",
          }}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_220px]">
        <article className="card space-y-5 p-7">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="rounded-full px-3 py-1 text-xs font-medium"
              style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
            >
              Задание № {task.task_type_number}
            </span>
            <span className="muted text-sm">{task.task_type_title}</span>
          </div>

          <MathText className="block text-lg leading-relaxed" text={task.statement} />

          {task.source && (
            <p className="muted text-xs">Источник: {task.source}</p>
          )}

          {task.hints.slice(0, slot.hintsShown).map((hint, i) => (
            <p
              key={i}
              className="rounded-xl p-4 text-sm leading-relaxed"
              style={{ background: "var(--accent-100)" }}
            >
              <MathText text={hint} />
            </p>
          ))}

          {!slot.result ? (
            <>
              <form
                className="flex flex-wrap gap-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  submit();
                }}
              >
                <input
                  ref={inputRef}
                  className="input flex-1"
                  placeholder="Ответ"
                  value={slot.answer}
                  onChange={(e) => patch(task.id, { answer: e.target.value })}
                />
                <button className="btn" type="submit" disabled={sending || !slot.answer.trim()}>
                  Ответить
                </button>
                <button type="button" className="btn-ghost" onClick={goNextUnanswered}>
                  Пропустить
                </button>
              </form>

              <div className="flex flex-wrap items-center gap-4">
                {slot.hintsShown < task.hints.length && (
                  <button
                    className="muted flex items-center gap-2 text-sm hover:underline"
                    onClick={() => patch(task.id, { hintsShown: slot.hintsShown + 1 })}
                  >
                    <Lightbulb size={15} />
                    Подсказка — задача будет отмечена как решённая с подсказкой
                  </button>
                )}
                <button
                  className="muted flex items-center gap-2 text-sm hover:underline"
                  onClick={() => setDraftOpen((v) => !v)}
                >
                  <PenLine size={15} />
                  {draftOpen ? "Убрать черновик" : "Черновик"}
                </button>
              </div>
            </>
          ) : (
            <Feedback
              result={slot.result}
              onNext={() => {
                if (!goNextUnanswered()) finish();
              }}
              lastOne={allAnswered}
            />
          )}

          <div className="border-t pt-3" style={{ borderColor: "var(--divider)" }}>
            <ReportButton taskId={task.id} givenAnswer={slot.answer || undefined} />
          </div>
        </article>

        <aside className="space-y-6">
          <div className="card p-5">
            <p className="eyebrow mb-3">Навигатор</p>
            <div className="grid grid-cols-5 gap-2">
              {quiz.tasks.map((t, i) => {
                const res = slots[t.id]?.result;
                const current = i === index;
                const bg = res
                  ? res.is_correct
                    ? "var(--accent-200)"
                    : "var(--accent-2-200)"
                  : "var(--surface)";
                return (
                  <button
                    key={t.id}
                    onClick={() => goTo(i)}
                    className="rounded-lg py-2 text-sm font-medium transition"
                    style={{
                      background: current ? "var(--accent)" : bg,
                      color: current ? "#fff" : "var(--text)",
                    }}
                    aria-current={current}
                  >
                    {i + 1}
                  </button>
                );
              })}
            </div>
            <ul className="muted mt-4 space-y-1.5 text-xs">
              <Legend color="var(--accent-200)" text={`верно · ${countBy(quiz, slots, true)}`} />
              <Legend
                color="var(--accent-2-200)"
                text={`ошибка · ${countBy(quiz, slots, false)}`}
              />
              <Legend
                color="var(--surface)"
                text={`не отвечено · ${quiz.tasks.length - answeredCount}`}
              />
            </ul>
          </div>

          {allAnswered && (
            <button className="btn w-full" onClick={finish}>
              Показать результат
            </button>
          )}
        </aside>
      </div>

      {draftOpen && (
        <DrawingPad
          strokes={drafts[task.id] ?? []}
          onChange={(next) => setDrafts((prev) => ({ ...prev, [task.id]: next }))}
          onClose={() => setDraftOpen(false)}
          height={820}
        />
      )}
    </div>
  );
}

function countBy(quiz: Quiz, slots: Record<number, Slot>, correct: boolean): number {
  return quiz.tasks.filter((t) => slots[t.id]?.result?.is_correct === correct).length;
}

function Legend({ color, text }: { color: string; text: string }) {
  return (
    <li className="flex items-center gap-2">
      <span className="inline-block h-3 w-3 rounded" style={{ background: color }} />
      {text}
    </li>
  );
}

function Feedback({
  result,
  onNext,
  lastOne,
}: {
  result: AnswerResult;
  onNext: () => void;
  lastOne: boolean;
}) {
  return (
    <div className="space-y-4">
      <div
        className="rounded-xl p-4"
        style={{
          background: result.is_correct ? "var(--accent-100)" : "var(--accent-2-100)",
        }}
      >
        <p
          className="font-semibold"
          style={{ color: result.is_correct ? "var(--accent-700)" : "var(--accent-2)" }}
        >
          {result.is_correct ? "Верно" : `Неверно. Правильный ответ: ${result.correct_answer}`}
        </p>
        {result.is_correct && result.used_hint && (
          <p className="muted mt-1 text-sm">Решено с подсказкой</p>
        )}
      </div>

      {!result.is_correct && result.solution && (
        <div
          className="rounded-xl border p-5 text-sm leading-relaxed"
          style={{ borderColor: "var(--divider)" }}
        >
          <p className="eyebrow mb-2">Разбор</p>
          <MathText text={result.solution} />
        </div>
      )}

      <button className="btn" onClick={onNext} autoFocus>
        {lastOne ? "Показать результат" : "Дальше"}
      </button>
    </div>
  );
}

function Result({ result }: { result: QuizResult }) {
  const percent = Math.round((result.score / result.total) * 100);
  const wrong = result.items.filter((i) => !i.is_correct);
  const withHint = result.items.filter((i) => i.is_correct && i.used_hint).length;

  return (
    <div className="space-y-6">
      <section className="card flex flex-wrap items-center justify-between gap-6 p-7">
        <div className="flex items-center gap-5">
          <span
            className="h flex h-20 w-20 items-center justify-center rounded-2xl text-2xl"
            style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
          >
            {result.score}/{result.total}
          </span>
          <div>
            <h1 className="text-2xl">{percent}% верно</h1>
            <p className="muted mt-1 text-sm">
              {result.streak_days > 0 && `серия ${result.streak_days} дн.`}
              {withHint > 0 && ` · с подсказкой: ${withHint}`}
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <Link className="btn" href="/app/quiz">
            Собрать ещё
          </Link>
          <Link className="btn-ghost" href="/app">
            На главную
          </Link>
        </div>
      </section>

      {wrong.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl">Разбор ошибок</h2>
          {wrong.map((item) => (
            <article key={item.task_id} className="card space-y-3 p-6 text-sm">
              <p className="eyebrow">Задание № {item.task_type_number}</p>
              <MathText className="block text-base leading-relaxed" text={item.statement} />
              <p>
                <span style={{ color: "var(--accent-2)" }}>
                  Твой ответ: {item.your_answer || "—"}
                </span>
                {" · "}
                <span style={{ color: "var(--accent-700)" }}>верный: {item.correct_answer}</span>
              </p>
              {item.solution && (
                <div className="border-t pt-3 leading-relaxed" style={{ borderColor: "var(--divider)" }}>
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
