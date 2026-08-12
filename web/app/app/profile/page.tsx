"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Coins, Flame, Lock, Swords, X } from "lucide-react";
import { api } from "@/lib/api";
import { plural } from "@/lib/exam";
import { initials } from "@/lib/format";

type Achievement = {
  code: string;
  title: string;
  description: string;
  rarity: "bronze" | "silver" | "gold";
  progress: number;
  target: number;
  unlocked: boolean;
};

type Profile = {
  display_name: string;
  is_guest: boolean;
  rating: number;
  rank: string;
  rank_color: string;
  coins: number;
  coins_week: number;
  incoming_duels: { code: string; from: string; rounds: number }[];
  duels_played: number;
  duels_won: number;
  duel_win_streak: number;
  solved_total: number;
  correct_total: number;
  accuracy: number;
  streak_days: number;
  streak_record: number;
  best_correct_run: number;
  perfect_quizzes: number;
  numbers_covered: number;
  attempts_total: number;
  attempts_correct: number;
  attempts_wrong: number;
  mistakes_total: number;
  mistakes_fixed: number;
  mistakes_open: number;
  tasks_total: number;
  activity: { day: string; solved: number }[];
  achievements: Achievement[];
};

const RARITY: Record<Achievement["rarity"], { label: string; color: string; bg: string }> = {
  bronze: { label: "бронза", color: "#8a5a2b", bg: "#f6ebe0" },
  silver: { label: "серебро", color: "#5b6570", bg: "#eef1f4" },
  gold: { label: "золото", color: "#8a6d0b", bg: "#fbf1cf" },
};

type DayStats = {
  day: string;
  total: number;
  correct: number;
  wrong: number;
  with_hint: number;
  minutes: number;
  quizzes: number;
  by_type: { number: number; title: string; total: number; correct: number }[];
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [day, setDay] = useState<DayStats | null>(null);

  useEffect(() => {
    api<Profile>("/api/profile").then(setProfile).catch(() => setProfile(null));
  }, []);

  function openDay(iso: string) {
    api<DayStats>(`/api/profile/day?day=${iso}`).then(setDay).catch(() => setDay(null));
  }

  if (!profile) return <p className="muted">Загрузка…</p>;

  const unlocked = profile.achievements.filter((a) => a.unlocked);
  const locked = profile.achievements.filter((a) => !a.unlocked);

  return (
    <div className="space-y-8">
      <section className="card flex flex-wrap items-center gap-5 p-7">
        <span
          className="h flex h-16 w-16 items-center justify-center rounded-2xl text-xl"
          style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
        >
          {initials(profile.display_name)}
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="flex flex-wrap items-center gap-3 text-2xl">
            {profile.display_name}
            <span
              className="rounded-full px-3 py-1 text-xs font-semibold"
              style={{ background: `${profile.rank_color}1a`, color: profile.rank_color }}
            >
              {profile.rank}
            </span>
          </h1>
          <p className="muted mt-1 text-sm">
            {profile.is_guest
              ? "Гостевой аккаунт — войди через Telegram, чтобы прогресс не потерялся"
              : "Аккаунт Telegram"}
          </p>
        </div>
      </section>

      {profile.incoming_duels.length > 0 && (
        <section
          className="card space-y-3 p-6"
          style={{ background: "var(--accent-2-100)", borderColor: "var(--accent-2-200)" }}
        >
          <h2 className="flex items-center gap-2 text-xl">
            <Swords size={18} style={{ color: "var(--accent-2)" }} />
            {profile.incoming_duels.length === 1
              ? "Тебя вызвали на дуэль"
              : `Тебя вызвали на дуэль: ${profile.incoming_duels.length}`}
          </h2>
          {profile.incoming_duels.map((duel) => (
            <div key={duel.code} className="flex flex-wrap items-center justify-between gap-3">
              <span>
                <b>{duel.from}</b> — {duel.rounds} {plural(duel.rounds, "раунд", "раунда", "раундов")}
              </span>
              <Link className="btn btn-accent2 text-sm" href={`/app/duels/${duel.code}`}>
                Принять вызов
              </Link>
            </div>
          ))}
        </section>
      )}

      <section className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <Metric
          value={String(profile.streak_days)}
          unit={plural(profile.streak_days, "день", "дня", "дней")}
          label={`подряд · рекорд ${profile.streak_record}`}
          icon={<Flame size={15} style={{ color: "var(--accent-2)" }} />}
        />
        <Metric
          value={`${unlocked.length}/${profile.achievements.length}`}
          label="получено достижений"
        />
        <Metric
          value={String(profile.coins)}
          label={profile.coins_week > 0 ? `монет · +${profile.coins_week} за неделю` : "монет"}
          icon={<Coins size={15} style={{ color: "#c98a00" }} />}
        />
        <Metric value={`${profile.accuracy}%`} label="верных ответов" />
        <Metric
          value={`${profile.attempts_correct} / ${profile.attempts_wrong}`}
          label="верных и ошибочных ответов"
        />
      </section>

      <section className="card flex flex-wrap items-center gap-7 p-7">
        <Ring
          done={profile.mistakes_fixed}
          total={profile.mistakes_total}
          value={profile.mistakes_open}
          accent={profile.mistakes_open > 0}
        />
        <div className="min-w-0 flex-1">
          <h2 className="text-xl">Работа над ошибками</h2>
          <p className="muted mt-1 text-sm leading-relaxed">
            {profile.mistakes_total === 0
              ? "Ошибок пока не было — как появятся, они соберутся здесь."
              : profile.mistakes_open > 0
                ? `Ты ошибался в ${profile.mistakes_total} ${plural(profile.mistakes_total, "задаче", "задачах", "задачах")}, из них закрыто ${profile.mistakes_fixed}. Осталось проработать ${profile.mistakes_open}.`
                : `Все ${profile.mistakes_total} ${plural(profile.mistakes_total, "задача", "задачи", "задач")}, где ты ошибался, уже решены верно.`}
          </p>
          {profile.mistakes_open > 0 && (
            <Link className="btn mt-4" href="/app/quiz/run?preset=mistakes&length=10">
              Проработать
            </Link>
          )}
        </div>
      </section>

      <section className="card p-6">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-xl">Активность за 30 дней</h2>
          <span className="muted text-sm">насыщенность — число решённых задач</span>
        </div>
        <Activity days={profile.activity} onPick={openDay} />
      </section>

      <section className="card flex flex-wrap items-center gap-7 p-7">
        <div className="text-center">
          <p className="h text-5xl">{profile.rating}</p>
          <p
            className="mt-1 inline-block rounded-full px-3 py-1 text-xs font-semibold"
            style={{ background: `${profile.rank_color}1a`, color: profile.rank_color }}
          >
            {profile.rank}
          </p>
        </div>

        <div className="min-w-0 flex-1">
          <h2 className="flex items-center gap-2 text-xl">
            <Swords size={18} style={{ color: "var(--accent-2)" }} /> Рейтинг
          </h2>
          <p className="muted mt-2 text-sm leading-relaxed">
            {profile.duels_played === 0
              ? "Меняется только в онлайн-матчах. Сыграй первый — первые пять матчей двигают рейтинг сильнее, чтобы быстрее найти твой уровень."
              : `Онлайн-матчей: ${profile.duels_played}, побед: ${profile.duels_won}.` +
                (profile.duel_win_streak >= 2
                  ? ` Серия из ${profile.duel_win_streak} побед подряд.`
                  : "")}
          </p>
          <Link className="btn mt-4" href="/app/duels">
            Сразиться
          </Link>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl">Достижения</h2>
          <span className="muted text-sm">
            {unlocked.length} из {profile.achievements.length}
          </span>
        </div>

        {/* items-stretch + h-full: иначе открытая плитка ниже закрытой,
            и в сетке появляются рваные пустоты */}
        <ul className="grid items-stretch gap-3 sm:grid-cols-2">
          {[...unlocked, ...locked].map((a) => (
            <li key={a.code} className="h-full">
              <AchievementCard achievement={a} />
            </li>
          ))}
        </ul>
      </section>

      {day && <DayModal stats={day} onClose={() => setDay(null)} />}
    </div>
  );
}

function Ring({
  done,
  total,
  value,
  accent,
}: {
  done: number;
  total: number;
  value: number;
  accent?: boolean;
}) {
  const size = 116;
  const stroke = 12;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const ratio = total > 0 ? done / total : 0;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--surface)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={accent ? "var(--accent-2)" : "var(--accent)"}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - ratio)}
          style={{ transition: "stroke-dashoffset .6s ease" }}
        />
      </svg>
      <span className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="h text-3xl">{value}</span>
        <span className="muted text-[11px]">{total === 0 ? "ошибок" : "осталось"}</span>
      </span>
    </div>
  );
}

function DayModal({ stats, onClose }: { stats: DayStats; onClose: () => void }) {
  const title = new Date(stats.day).toLocaleDateString("ru", {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
      style={{ background: "rgba(20,23,28,.4)" }}
      onClick={onClose}
    >
      <div
        className="card w-full max-w-md p-6"
        style={{ boxShadow: "var(--shadow-lg)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h3 className="text-xl">{title}</h3>
            <p className="muted mt-0.5 text-sm">
              {stats.total > 0
                ? `${stats.quizzes} ${plural(stats.quizzes, "квиз", "квиза", "квизов")} · ${stats.minutes} мин`
                : "в этот день ты не занимался"}
            </p>
          </div>
          <button className="muted" onClick={onClose} aria-label="Закрыть">
            <X size={18} />
          </button>
        </div>

        {stats.total > 0 && (
          <>
            <div className="grid grid-cols-3 gap-3 text-center">
              <DayMetric value={stats.total} label="попыток" />
              <DayMetric value={stats.correct} label="верно" color="var(--accent)" />
              <DayMetric value={stats.wrong} label="ошибок" color="var(--accent-2)" />
            </div>

            {stats.with_hint > 0 && (
              <p className="muted mt-3 text-sm">С подсказкой: {stats.with_hint}</p>
            )}

            <ul className="mt-5 space-y-2">
              {stats.by_type.map((row) => (
                <li key={row.number} className="flex items-center justify-between gap-3 text-sm">
                  <span className="min-w-0 truncate">
                    <span className="muted mr-2">№{row.number}</span>
                    {row.title}
                  </span>
                  <span
                    style={{
                      color: row.correct === row.total ? "var(--accent)" : "var(--accent-2)",
                    }}
                  >
                    {row.correct}/{row.total}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

function DayMetric({ value, label, color }: { value: number; label: string; color?: string }) {
  return (
    <div className="rounded-xl p-3" style={{ background: "var(--surface)" }}>
      <p className="h text-2xl" style={{ color }}>
        {value}
      </p>
      <p className="muted text-xs">{label}</p>
    </div>
  );
}

function Metric({
  value,
  unit,
  label,
  icon,
}: {
  value: string;
  unit?: string;
  label: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="card p-5">
      <p className="h flex items-baseline gap-1.5 text-3xl">
        {icon}
        {value}
        {unit && <span className="muted text-base">{unit}</span>}
      </p>
      <p className="muted mt-1 text-sm leading-snug">{label}</p>
    </div>
  );
}

function Activity({
  days,
  onPick,
}: {
  days: { day: string; solved: number }[];
  onPick: (day: string) => void;
}) {
  const max = Math.max(1, ...days.map((d) => d.solved));

  return (
    <div className="grid grid-cols-10 gap-1.5" style={{ maxWidth: "22rem" }}>
      {days.map((d) => {
        const level = d.solved === 0 ? 0 : Math.ceil((d.solved / max) * 3);
        const bg = ["var(--surface)", "var(--accent-200)", "var(--accent-300)", "var(--accent)"][
          level
        ];
        return (
          <button
            key={d.day}
            onClick={() => onPick(d.day)}
            title={`${new Date(d.day).toLocaleDateString("ru", {
              day: "numeric",
              month: "long",
              timeZone: "UTC",
            })} — решено ${d.solved}`}
            className="aspect-square w-full rounded-md transition hover:ring-2"
            style={{ background: bg, ["--tw-ring-color" as string]: "var(--accent)" }}
          />
        );
      })}
    </div>
  );
}

function AchievementCard({ achievement: a }: { achievement: Achievement }) {
  const rarity = RARITY[a.rarity];
  const percent = Math.min(100, Math.round((a.progress / a.target) * 100));

  return (
    <div
      className="card flex h-full gap-4 p-5"
      style={{ opacity: a.unlocked ? 1 : 0.75, borderColor: a.unlocked ? rarity.color : undefined }}
    >
      <span
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
        style={{ background: a.unlocked ? rarity.bg : "var(--surface)" }}
      >
        {a.unlocked ? (
          <span className="h text-lg" style={{ color: rarity.color }}>
            ★
          </span>
        ) : (
          <Lock size={16} className="muted" />
        )}
      </span>

      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-2 font-medium">
          {a.title}
          <span
            className="rounded-full px-2 py-0.5 text-[11px]"
            style={{ background: rarity.bg, color: rarity.color }}
          >
            {rarity.label}
          </span>
        </p>
        <p className="muted mt-0.5 text-sm">{a.description}</p>

        <div className="mt-3" style={{ visibility: a.unlocked ? "hidden" : "visible" }}>
            <div
              className="h-1.5 overflow-hidden rounded-full"
              style={{ background: "var(--surface)" }}
            >
              <div
                className="h-full rounded-full"
                style={{ width: `${percent}%`, background: rarity.color }}
              />
            </div>
          <p className="muted mt-1 text-xs">
            {a.progress} из {a.target}
          </p>
        </div>
      </div>
    </div>
  );
}
