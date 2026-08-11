"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Layers, Swords, Zap } from "lucide-react";
import TelegramLogin from "./TelegramLogin";
import { getMe, getTaskTypes, type User } from "@/lib/api";
import { EXAM, daysUntilExam, formatExamDate, plural } from "@/lib/exam";

export default function Landing() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [tasksCount, setTasksCount] = useState<number | null>(null);
  // считаем после монтирования: на сервере и в браузере «сейчас» разное,
  // а расхождение ломает гидратацию
  const [days, setDays] = useState<number | null>(null);
  useEffect(() => setDays(daysUntilExam()), []);

  useEffect(() => {
    // уже вошёл — незачем показывать лендинг
    getMe()
      .then((u: User) => {
        if (!u.is_guest) router.replace("/app");
      })
      .catch(() => {});

    getTaskTypes()
      .then((types) => setTasksCount(types.reduce((s, t) => s + t.tasks_count, 0)))
      .catch(() => setTasksCount(null));
  }, [router]);

  const onLogin = useCallback(() => router.push("/app"), [router]);

  return (
    <div>
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="h text-xl">
          Боталка<span style={{ color: "var(--accent)" }}>.</span>
        </span>
        <nav className="muted hidden gap-6 text-sm md:flex">
          <a href="#how">Как это работает</a>
          <a href="#duels">Дуэли</a>
          <Link href="/app">Тренажёр</Link>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-20">
        <section
          className="relative overflow-hidden px-8 py-14 text-white sm:px-12"
          style={{ background: "var(--accent)", borderRadius: "var(--radius-lg)" }}
        >
          <div
            aria-hidden
            className="pointer-events-none absolute -right-20 -top-24 h-96 w-96 rounded-full opacity-30"
            style={{ background: "var(--accent-2)" }}
          />
          <div className="relative max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-widest opacity-80">
              ЕГЭ {EXAM.year}
              {days !== null && ` · ${days} ${plural(days, "день", "дня", "дней")} до экзамена`}
            </p>
            <div className="my-5 h-px w-24 bg-white/40" />
            <h1 className="text-4xl leading-tight sm:text-5xl">
              Готовься к ЕГЭ так, будто это игра с самим собой
            </h1>
            <p className="mt-5 text-lg leading-relaxed opacity-90">
              Короткие квизы вместо многочасовых занятий, разбор каждой ошибки и дуэли
              1 на 1, где вопрос приходит обоим одновременно.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <TelegramLogin onLogin={onLogin} onError={setError} />
              <span className="text-sm opacity-80">Без пароля, вход за 10 секунд</span>
            </div>
            {error && <p className="mt-3 text-sm text-white/90">{error}</p>}

            <p className="mt-4 text-sm opacity-80">
              Или{" "}
              <Link href="/app" className="underline underline-offset-4">
                попробовать без регистрации
              </Link>
            </p>
          </div>
        </section>

        <section id="how" className="grid gap-8 py-16 md:grid-cols-3">
          <Feature
            icon={<Zap size={22} />}
            title="Короткие квизы"
            text="Десять вопросов по одной теме. Ошибся — разбор приходит сразу, вместе с решением по шагам."
          />
          <Feature
            icon={<Layers size={22} />}
            title="Тренировка по номерам КИМ"
            text="Каждая задача привязана к номеру задания. Видно, какой номер проседает, и можно добивать именно его."
          />
          <Feature
            icon={<Swords size={22} />}
            title="Дуэли 1 на 1"
            text="Семь раундов, вопрос у обоих одновременно. Очко забирает тот, кто ответил верно и быстрее."
            accent
            soon
          />
        </section>

        <section
          id="duels"
          className="grid items-center gap-10 px-8 py-12 md:grid-cols-2 sm:px-12"
          style={{ background: "var(--surface)", borderRadius: "var(--radius-lg)" }}
        >
          <div>
            <p className="eyebrow" style={{ color: "var(--accent-2)" }}>
              Чем это отличается от курсов
            </p>
            <h2 className="mt-3 text-3xl leading-tight">Это не школа, а спортзал</h2>
            <p className="muted mt-4 leading-relaxed">
              Никаких вебинаров по два часа и домашки на неделю. Заходишь на пятнадцать
              минут, решаешь, видишь разбор своих ошибок и уходишь. Результат даёт не
              длина занятия, а то, что ты приходишь каждый день.
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-6">
            <Stat
              value={tasksCount !== null ? String(tasksCount) : "—"}
              label="задач с разбором в банке"
            />
            <Stat value="12" label="номеров части 1 покрыто" />
            <Stat value="0 ₽" label="стоит и будет стоить тренажёр" />
            <Stat value="10 сек" label="занимает вход через Telegram" />
          </dl>
        </section>

        <section className="py-16 text-center">
          <h2 className="text-3xl">Начни с одного квиза</h2>
          <p className="muted mx-auto mt-3 max-w-xl">
            Десять задач, восемь минут. Регистрация не нужна — прогресс сохранится и
            привяжется к аккаунту, если потом войдёшь.
          </p>
          <div className="mt-7 flex justify-center">
            <Link className="btn" href="/app/quiz">
              Решить квиз
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t" style={{ borderColor: "var(--divider)" }}>
        <div className="muted mx-auto flex max-w-6xl flex-wrap justify-between gap-3 px-6 py-8 text-sm">
          <span>Боталка — тренажёр для подготовки к ЕГЭ</span>
          <span>
            {EXAM.subject} · экзамен {EXAM.approximate ? "ориентировочно " : ""}
            {formatExamDate()}
          </span>
        </div>
      </footer>
    </div>
  );
}

function Feature({
  icon,
  title,
  text,
  accent,
  soon,
}: {
  icon: React.ReactNode;
  title: string;
  text: string;
  accent?: boolean;
  soon?: boolean;
}) {
  return (
    <article>
      <span style={{ color: accent ? "var(--accent-2)" : "var(--accent)" }}>{icon}</span>
      <h3 className="mt-3 flex items-center gap-2 text-xl">
        {title}
        {soon && (
          <span
            className="rounded-full px-2 py-0.5 text-xs font-medium"
            style={{ background: "var(--accent-2-100)", color: "var(--accent-2)" }}
          >
            скоро
          </span>
        )}
      </h3>
      <p className="muted mt-2 leading-relaxed">{text}</p>
    </article>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <dt className="h text-3xl">{value}</dt>
      <dd className="muted mt-1 text-sm leading-snug">{label}</dd>
    </div>
  );
}
