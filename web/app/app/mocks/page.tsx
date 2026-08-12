"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ClipboardList, Clock, Play } from "lucide-react";
import { api } from "@/lib/api";
import { plural } from "@/lib/exam";

type MockCard = {
  id: number;
  title: string;
  description: string | null;
  tasks_count: number;
  duration_minutes: number;
  best_score: number | null;
  attempts: number;
  active_attempt_id: number | null;
};

function hoursMinutes(total: number): string {
  const hours = Math.floor(total / 60);
  const minutes = total % 60;
  if (!hours) return `${minutes} мин`;
  return `${hours} ч ${String(minutes).padStart(2, "0")} мин`;
}

export default function MocksPage() {
  const [mocks, setMocks] = useState<MockCard[] | null>(null);

  useEffect(() => {
    api<MockCard[]>("/api/mocks")
      .then(setMocks)
      .catch(() => setMocks([]));
  }, []);

  return (
    <div className="space-y-7">
      <header className="flex items-start gap-3">
        <ClipboardList size={22} style={{ color: "var(--accent)" }} />
        <div>
          <h1 className="text-3xl">Пробники</h1>
          <p className="muted mt-1 text-sm">
            Полный вариант на время, как на экзамене: ответы не проверяются по ходу, идёт
            общий таймер, баллы считаются в конце.
          </p>
        </div>
      </header>

      {mocks === null ? (
        <p className="muted">Загрузка…</p>
      ) : mocks.length === 0 ? (
        <section className="card p-8 text-center">
          <p className="text-lg">Пробников пока нет</p>
          <p className="muted mx-auto mt-2 max-w-md text-sm">
            Варианты собираются в админке: можно взять по одной задаче на каждый номер
            или выбрать задачи вручную.
          </p>
        </section>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {mocks.map((mock) => (
            <li key={mock.id}>
              <article className="card flex h-full flex-col gap-4 p-6">
                <div className="flex-1">
                  <h2 className="text-xl">{mock.title}</h2>
                  {mock.description && (
                    <p className="muted mt-1 text-sm">{mock.description}</p>
                  )}

                  <p className="muted mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                    <span className="flex items-center gap-1.5">
                      <Clock size={14} /> {hoursMinutes(mock.duration_minutes)}
                    </span>
                    <span>
                      {mock.tasks_count}{" "}
                      {plural(mock.tasks_count, "задание", "задания", "заданий")}
                    </span>
                  </p>

                  {mock.attempts > 0 && (
                    <p className="mt-3 text-sm">
                      Лучший результат:{" "}
                      <span className="h">
                        {mock.best_score}/{mock.tasks_count}
                      </span>
                      <span className="muted">
                        {" "}
                        · попыток {mock.attempts}
                      </span>
                    </p>
                  )}
                </div>

                {mock.active_attempt_id ? (
                  <Link
                    className="btn btn-accent2"
                    href={`/app/mocks/run/${mock.active_attempt_id}`}
                  >
                    Продолжить начатый
                  </Link>
                ) : (
                  <Link className="btn" href={`/app/mocks/${mock.id}`}>
                    <Play size={15} /> Начать
                  </Link>
                )}
              </article>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
