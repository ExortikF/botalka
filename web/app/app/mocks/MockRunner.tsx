"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Clock, PenLine } from "lucide-react";
import MathText from "../../Math";
import DrawingPad, { type Stroke } from "../DrawingPad";
import ReportButton from "../ReportButton";
import { checkAchievements } from "@/lib/achievements";
import { api } from "@/lib/api";

type MockTask = {
  id: number;
  number: number;
  title: string;
  statement: string;
  image_url: string | null;
  answer_type: string;
  source: string | null;
};

type Run = {
  attempt_id: number;
  title: string;
  seconds_left: number;
  duration_minutes: number;
  tasks: MockTask[];
  answers: Record<string, string>;
};

type ResultItem = {
  task_id: number;
  number: number;
  statement: string;
  your_answer: string;
  correct_answer: string;
  is_correct: boolean;
  solution: string | null;
};

type Result = {
  attempt_id: number;
  title: string;
  score: number;
  secondary: number;
  max_primary: number;
  total: number;
  percent: number;
  spent_minutes: number;
  timed_out: boolean;
  by_number: { number: number; total: number; correct: number }[];
  items: ResultItem[];
};

function clock(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function MockRunner({
  examId,
  attemptId,
}: {
  examId?: number;
  attemptId?: number;
}) {
  const [run, setRun] = useState<Run | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [left, setLeft] = useState(0);
  const [draftOpen, setDraftOpen] = useState(false);
  // черновик свой у каждого задания: ключ — id задачи
  const [drafts, setDrafts] = useState<Record<number, Stroke[]>>({});
  const [finishing, setFinishing] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const request = attemptId
      ? api<Run>(`/api/mocks/attempt/${attemptId}`)
      : api<Run>(`/api/mocks/${examId}/start`, { method: "POST" });

    request
      .then((data) => {
        setRun(data);
        setLeft(data.seconds_left);
        setAnswers(
          Object.fromEntries(
            Object.entries(data.answers).map(([k, v]) => [Number(k), v]),
          ),
        );
      })
      .catch((e: Error) => setError(e.message));
  }, [examId, attemptId]);

  const finish = useCallback(async () => {
    if (!run || finishing) return;
    setFinishing(true);
    try {
      setResult(
        await api<Result>(`/api/mocks/attempt/${run.attempt_id}/finish`, {
          method: "POST",
        }),
      );
      checkAchievements();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setFinishing(false);
    }
  }, [run, finishing]);

  // Таймер только отображает: дедлайн хранится на сервере, он же решает,
  // засчитан ли ответ. Здесь просто автосдача, когда время вышло.
  useEffect(() => {
    if (!run || result) return;
    const id = setInterval(() => {
      setLeft((value) => {
        if (value <= 1) {
          clearInterval(id);
          finish();
          return 0;
        }
        return value - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [run, result, finish]);

  function setAnswer(taskId: number, value: string) {
    setAnswers((prev) => ({ ...prev, [taskId]: value }));
    if (saveTimer.current) clearTimeout(saveTimer.current);
    // сохраняем с задержкой, чтобы не дёргать сервер на каждую букву
    saveTimer.current = setTimeout(() => {
      if (!run) return;
      api(`/api/mocks/attempt/${run.attempt_id}/answer`, {
        method: "POST",
        body: JSON.stringify({ task_id: taskId, answer: value }),
      }).catch(() => {});
    }, 600);
  }

  if (error)
    return (
      <div className="space-y-4">
        <p style={{ color: "var(--accent-2)" }}>{error}</p>
        <Link className="btn-ghost" href="/app/mocks">
          К пробникам
        </Link>
      </div>
    );

  if (result) return <MockResult result={result} />;
  if (!run) return <p className="muted">Готовим вариант…</p>;

  const task = run.tasks[index];
  const answered = Object.values(answers).filter((v) => v.trim()).length;

  return (
    <div className="space-y-6">
      <div className="card flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <h1 className="text-xl">{run.title}</h1>
          <p className="muted text-sm">
            отвечено {answered} из {run.tasks.length}
          </p>
        </div>
        <div className="text-right">
          <p
            className="h flex items-center gap-2 text-3xl"
            style={{ color: left < 300 ? "var(--accent-2)" : undefined }}
          >
            <Clock size={20} /> {clock(left)}
          </p>
          <p className="muted text-xs">до конца работы</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_220px]">
        <article className="card space-y-5 p-7">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="rounded-full px-3 py-1 text-xs font-medium"
              style={{
                background: "var(--accent-100)",
                color: "var(--accent-700)",
              }}
            >
              Задание № {task.number}
            </span>
            <span className="muted text-sm">{task.title}</span>
          </div>

          <MathText
            className="block text-lg leading-relaxed"
            text={task.statement}
          />
          {task.source && (
            <p className="muted text-xs">Источник: {task.source}</p>
          )}

          <input
            className="input"
            placeholder="Ответ"
            value={answers[task.id] ?? ""}
            onChange={(e) => setAnswer(task.id, e.target.value)}
          />

          <div className="flex flex-wrap items-center gap-4">
            <button
              className="btn-ghost text-sm"
              onClick={() => setIndex(Math.max(0, index - 1))}
              disabled={index === 0}
            >
              Назад
            </button>
            <button
              className="btn text-sm"
              onClick={() =>
                setIndex(Math.min(run.tasks.length - 1, index + 1))
              }
              disabled={index === run.tasks.length - 1}
            >
              Дальше
            </button>
            <button
              className="muted flex items-center gap-2 text-sm hover:underline"
              onClick={() => setDraftOpen((v) => !v)}
            >
              <PenLine size={15} />
              {draftOpen ? "Убрать черновик" : "Черновик"}
            </button>
          </div>

          <div
            className="border-t pt-3"
            style={{ borderColor: "var(--divider)" }}
          >
            <ReportButton taskId={task.id} givenAnswer={answers[task.id]} />
          </div>
        </article>

        <aside className="space-y-5">
          <div className="card p-5">
            <p className="eyebrow mb-3">Задания</p>
            <div className="grid grid-cols-5 gap-2">
              {run.tasks.map((t, i) => {
                const filled = (answers[t.id] ?? "").trim().length > 0;
                const current = i === index;
                return (
                  <button
                    key={t.id}
                    onClick={() => setIndex(i)}
                    className="rounded-lg py-2 text-sm font-medium transition"
                    style={{
                      background: current
                        ? "var(--accent)"
                        : filled
                          ? "var(--accent-200)"
                          : "var(--surface)",
                      color: current ? "#fff" : "var(--text)",
                    }}
                  >
                    {t.number}
                  </button>
                );
              })}
            </div>
            <p className="muted mt-3 text-xs">
              Закрашены те, где есть ответ. Порядок любой, ответы можно менять
              до сдачи.
            </p>
          </div>

          <button
            className="btn btn-accent2 w-full"
            onClick={() => {
              if (confirm("Сдать работу? После этого ответы изменить нельзя."))
                finish();
            }}
            disabled={finishing}
          >
            {finishing ? "Проверяем…" : "Сдать работу"}
          </button>
        </aside>
      </div>

      {draftOpen && (
        <DrawingPad
          strokes={drafts[task.id] ?? []}
          onChange={(next) =>
            setDrafts((prev) => ({ ...prev, [task.id]: next }))
          }
          onClose={() => setDraftOpen(false)}
          height={820}
        />
      )}
    </div>
  );
}

function MockResult({ result }: { result: Result }) {
  const wrong = result.items.filter((i) => !i.is_correct);

  return (
    <div className="space-y-6">
      <section className="card p-8 text-center">
        <p className="h text-5xl">
          {result.score}
          <span className="muted text-3xl"> / {result.total}</span>
        </p>
        <p className="muted mt-1 text-sm">первичных баллов</p>

        <div className="mt-5 flex flex-wrap items-center justify-center gap-8">
          <div>
            <p className="h text-4xl" style={{ color: "var(--accent)" }}>
              {result.secondary}
            </p>
            <p className="muted text-sm">тестовый балл</p>
          </div>
          <div>
            <p className="h text-4xl">{result.percent}%</p>
            <p className="muted text-sm">верных ответов</p>
          </div>
          <div>
            <p className="h text-4xl">{result.spent_minutes}</p>
            <p className="muted text-sm">минут потрачено</p>
          </div>
        </div>

        {result.timed_out && (
          <p className="muted mt-3 text-sm">
            Время вышло — работа сдана автоматически.
          </p>
        )}
        <p className="muted mx-auto mt-3 max-w-lg text-sm">
          Тестовый балл посчитан по официальной шкале перевода. За всю работу
          целиком (части 1 и 2) можно набрать {result.max_primary} первичных
          баллов — здесь только часть 1.
        </p>
        <div className="mt-5 flex justify-center gap-3">
          <Link className="btn" href="/app/mocks">
            К пробникам
          </Link>
          <Link className="btn-ghost" href="/app/quiz">
            Разобрать темы
          </Link>
        </div>
      </section>

      {wrong.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl">Разбор ошибок</h2>
          {wrong.map((item) => (
            <article key={item.task_id} className="card space-y-3 p-6 text-sm">
              <p className="eyebrow">Задание № {item.number}</p>
              <MathText
                className="block text-base leading-relaxed"
                text={item.statement}
              />
              <p>
                <span style={{ color: "var(--accent-2)" }}>
                  Твой ответ: {item.your_answer || "—"}
                </span>
                {" · "}
                <span style={{ color: "var(--accent-700)" }}>
                  верный: {item.correct_answer}
                </span>
              </p>
              {item.solution && (
                <div
                  className="border-t pt-3 leading-relaxed"
                  style={{ borderColor: "var(--divider)" }}
                >
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
