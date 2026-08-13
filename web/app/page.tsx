"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Layers, Swords, User as UserIcon, Zap } from "lucide-react";
import TelegramLogin from "./TelegramLogin";
import { initials } from "@/lib/format";
import { devLogin, getConfig, getMe, getTaskTypes, type User } from "@/lib/api";
import { EXAM, daysUntilExam, formatExamDate, plural } from "@/lib/exam";

export default function Landing() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [me, setMe] = useState<User | null>(null);
  const [tasksCount, setTasksCount] = useState<number | null>(null);
  const [devAvailable, setDevAvailable] = useState(false);
  // считаем после монтирования: на сервере и в браузере «сейчас» разное,
  // а расхождение ломает гидратацию
  const [days, setDays] = useState<number | null>(null);
  useEffect(() => setDays(daysUntilExam()), []);

  useEffect(() => {
    // уже вошёл — незачем показывать лендинг
    // намеренно без редиректа: на лендинг заходят осознанно, кликнув по логотипу
    getMe()
      .then((u: User) => setMe(u))
      .catch(() => setMe(null));

    getTaskTypes()
      .then((types) =>
        setTasksCount(types.reduce((s, t) => s + t.tasks_count, 0)),
      )
      .catch(() => setTasksCount(null));

    getConfig()
      .then((cfg) => setDevAvailable(cfg.dev_login))
      .catch(() => setDevAvailable(false));
  }, [router]);

  const onLogin = useCallback(() => router.push("/app"), [router]);

  return (
    <div>
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <span className="h text-4xl tracking-tight">
          Боталка<span style={{ color: "var(--accent)" }}>.</span>
        </span>
        <nav className="flex items-center gap-6 text-sm">
          <Link
            href="/app/profile"
            title="Профиль и статистика"
            className="flex items-center gap-2 rounded-full py-1 pl-1 pr-3 transition hover:bg-[var(--surface)]"
          >
            <span
              className="flex h-9 w-9 items-center justify-center rounded-full"
              style={{
                background: "var(--accent-100)",
                color: "var(--accent-700)",
              }}
            >
              {me ? (
                <span className="text-xs font-semibold">
                  {initials(me.display_name)}
                </span>
              ) : (
                <UserIcon size={17} />
              )}
            </span>
            <span className="hidden sm:inline">
              {me ? me.display_name : "Профиль"}
            </span>
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-20">
        <section
          className="relative overflow-hidden px-8 py-14 text-white sm:px-12"
          style={{
            background: "var(--accent)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <div
            aria-hidden
            className="pointer-events-none absolute -right-20 -top-24 h-96 w-96 rounded-full opacity-30"
            style={{ background: "var(--accent-2)" }}
          />
          <div className="relative max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-widest opacity-80">
              ЕГЭ {EXAM.year}
              {days !== null &&
                ` · ${days} ${plural(days, "день", "дня", "дней")} до экзамена`}
            </p>
            <div className="my-5 h-px w-24 bg-white/40" />
            <h1 className="text-4xl leading-tight sm:text-5xl">
              Готовься к ЕГЭ так, будто это игра с самим собой
            </h1>
            <p className="mt-5 text-lg leading-relaxed opacity-90">
              Короткие квизы вместо многочасовых занятий, разбор каждой ошибки и
              дуэли 1 на 1, где вопрос приходит обоим одновременно.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <TelegramLogin onLogin={onLogin} onError={setError} />
              <span className="text-sm opacity-80">
                Без пароля, вход за 10 секунд
              </span>
            </div>
            {error && <p className="mt-3 text-sm text-white/90">{error}</p>}

            {devAvailable && (
              <div className="mt-5 rounded-xl border border-white/30 p-4">
                <p className="text-sm font-medium">Отладочный вход</p>
                <p className="mt-1 text-sm opacity-80">
                  Домен для виджета Telegram пока не настроен, поэтому кнопка
                  выше не работает. Эти входят без Telegram — включено
                  переменной DEV_LOGIN.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    className="rounded-lg bg-white/20 px-3 py-2 text-sm"
                    onClick={() => devLogin(false).then(onLogin)}
                  >
                    Войти учеником
                  </button>
                  <button
                    className="rounded-lg bg-white/20 px-3 py-2 text-sm"
                    onClick={() => devLogin(true).then(onLogin)}
                  >
                    Войти админом
                  </button>
                </div>
              </div>
            )}

            <p className="mt-4 text-sm opacity-80">
              Или{" "}
              <Link href="/app/quiz" className="underline underline-offset-4">
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
            text="Вы решаете один набор задач. Побеждает тот, кто ответил верно больше раз, а при равном счёте — кто быстрее."
            accent
          />
        </section>

        <section
          id="duels"
          className="grid items-center gap-10 px-8 py-12 md:grid-cols-2 sm:px-12"
          style={{
            background: "var(--surface)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <div>
            <p className="eyebrow" style={{ color: "var(--accent-2)" }}>
              Чем это отличается от курсов
            </p>
            <h2 className="mt-3 text-3xl leading-tight">
              Это не школа, а спортзал
            </h2>
            <p className="muted mt-4 leading-relaxed">
              Никаких вебинаров по два часа и домашки на неделю. Заходишь на
              пятнадцать минут, решаешь, видишь разбор своих ошибок и уходишь.
              Результат даёт не длина занятия, а то, что ты приходишь каждый
              день.
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
            Десять задач, восемь минут. Регистрация не нужна — прогресс
            сохранится и привяжется к аккаунту, если потом войдёшь.
          </p>
          <div className="mt-7 flex justify-center">
            <Link className="btn" href="/app/quiz/run">
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
      <span style={{ color: accent ? "var(--accent-2)" : "var(--accent)" }}>
        {icon}
      </span>
      <h3 className="mt-3 flex items-center gap-2 text-xl">
        {title}
        {soon && (
          <span
            className="rounded-full px-2 py-0.5 text-xs font-medium"
            style={{
              background: "var(--accent-2-100)",
              color: "var(--accent-2)",
            }}
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
