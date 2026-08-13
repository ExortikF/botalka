"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Clock, Lock, Play } from "lucide-react";
import { api, getSubjects, type Subject } from "@/lib/api";

type MockCard = {
  id: number;
  subject_slug: string;
  subject_title: string;
  title: string;
  description: string | null;
  tasks_count: number;
  duration_minutes: number;
  best_score: number | null;
  attempts: number;
  active_attempt_id: number | null;
};

function duration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h} ч ${m ? `${m} мин` : ""}`.trim() : `${m} мин`;
}

export default function MocksPage() {
  const [mocks, setMocks] = useState<MockCard[] | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    api<MockCard[]>("/api/mocks")
      .then((data) => {
        setMocks(data);
        setActive((prev) => prev ?? data[0]?.subject_slug ?? "math_prof");
      })
      .catch(() => setMocks([]));
    getSubjects()
      .then(setSubjects)
      .catch(() => setSubjects([]));
  }, []);

  if (!mocks) return <p className="muted">Загрузка…</p>;

  const countBySubject = new Map<string, number>();
  for (const mock of mocks) {
    countBySubject.set(
      mock.subject_slug,
      (countBySubject.get(mock.subject_slug) ?? 0) + 1,
    );
  }

  const shown = mocks.filter((m) => m.subject_slug === active);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl">Пробники</h1>
        <p className="muted mt-2">
          Полный вариант на время. Ответы проверяются в конце — как на экзамене.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="eyebrow">Предмет</h2>
        <ul className="grid gap-3 sm:grid-cols-3">
          {subjects.map((subject) => {
            const count = countBySubject.get(subject.slug) ?? 0;
            const selected = subject.slug === active;
            return (
              <li key={subject.slug}>
                <button
                  disabled={count === 0}
                  onClick={() => count > 0 && setActive(subject.slug)}
                  className="card w-full p-5 text-left transition disabled:cursor-default"
                  style={{
                    borderColor: selected ? "var(--accent)" : "var(--divider)",
                    background: selected ? "var(--accent-100)" : "var(--card)",
                    opacity: count === 0 ? 0.55 : 1,
                  }}
                >
                  <span className="flex items-center justify-between">
                    <span className="font-medium">{subject.title}</span>
                    {count === 0 && <Lock size={14} className="muted" />}
                  </span>
                  <span className="muted mt-2 block text-sm">
                    {count > 0 ? `${count} вариантов` : "пробников пока нет"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="space-y-3">
        {shown.length === 0 ? (
          <p className="muted">По этому предмету вариантов пока нет.</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {shown.map((mock) => (
              <li key={mock.id}>
                <article className="card flex h-full flex-col gap-4 p-6">
                  <div className="flex-1">
                    <h3 className="text-xl">{mock.title}</h3>
                    {mock.description && (
                      <p className="muted mt-1 text-sm">{mock.description}</p>
                    )}
                    <p className="muted mt-3 flex items-center gap-3 text-sm">
                      <span>{mock.tasks_count} заданий</span>
                      <span className="flex items-center gap-1">
                        <Clock size={14} /> {duration(mock.duration_minutes)}
                      </span>
                    </p>
                    {mock.attempts > 0 && (
                      <p
                        className="mt-2 text-sm"
                        style={{ color: "var(--accent-700)" }}
                      >
                        Лучший результат: {mock.best_score} из{" "}
                        {mock.tasks_count}
                      </p>
                    )}
                  </div>

                  <Link
                    className="btn"
                    href={
                      mock.active_attempt_id
                        ? `/app/mocks/run?attempt=${mock.active_attempt_id}`
                        : `/app/mocks/run?exam=${mock.id}`
                    }
                  >
                    <Play size={15} />
                    {mock.active_attempt_id ? "Продолжить" : "Начать"}
                  </Link>
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
