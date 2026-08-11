"use client";

import { useEffect, useState } from "react";
import { Flame, Lock, Swords } from "lucide-react";
import { api } from "@/lib/api";
import { plural } from "@/lib/exam";
import { initials } from "../TopBar";

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
  rating: number | null;
  solved_total: number;
  correct_total: number;
  accuracy: number;
  streak_days: number;
  streak_record: number;
  best_correct_run: number;
  perfect_quizzes: number;
  numbers_covered: number;
  activity: { day: string; solved: number }[];
  achievements: Achievement[];
};

const RARITY: Record<Achievement["rarity"], { label: string; color: string; bg: string }> = {
  bronze: { label: "бронза", color: "#8a5a2b", bg: "#f6ebe0" },
  silver: { label: "серебро", color: "#5b6570", bg: "#eef1f4" },
  gold: { label: "золото", color: "#8a6d0b", bg: "#fbf1cf" },
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    api<Profile>("/api/profile").then(setProfile).catch(() => setProfile(null));
  }, []);

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
          <h1 className="text-2xl">{profile.display_name}</h1>
          <p className="muted mt-1 text-sm">
            {profile.is_guest
              ? "Гостевой аккаунт — войди через Telegram, чтобы прогресс не потерялся"
              : "Аккаунт Telegram"}
            {" · "}
            открыто достижений: {unlocked.length} из {profile.achievements.length}
          </p>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-4">
        <Metric
          value={String(profile.streak_days)}
          unit={plural(profile.streak_days, "день", "дня", "дней")}
          label={`подряд · рекорд ${profile.streak_record}`}
          icon={<Flame size={15} style={{ color: "var(--accent-2)" }} />}
        />
        <Metric value={String(profile.solved_total)} label="задач решено" />
        <Metric value={`${profile.accuracy}%`} label="верных ответов" />
        <Metric
          value={`${profile.numbers_covered}/12`}
          label="номеров с верным решением"
        />
      </section>

      <section className="card p-6">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-xl">Активность за 30 дней</h2>
          <span className="muted text-sm">насыщенность — число решённых задач</span>
        </div>
        <Activity days={profile.activity} />
      </section>

      <section className="card p-6">
        <p className="eyebrow flex items-center gap-2">
          <Swords size={14} /> Рейтинг
        </p>
        <p className="muted mt-2 text-sm leading-relaxed">
          Появится вместе с дуэлями. Считаться будет только по ним: победа над сильным
          соперником даст больше, а квизы и тренировки на рейтинг не влияют — иначе он
          превратится в счётчик усидчивости.
        </p>
      </section>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl">Достижения</h2>
          <span className="muted text-sm">
            {unlocked.length} из {profile.achievements.length}
          </span>
        </div>

        <ul className="grid gap-3 sm:grid-cols-2">
          {[...unlocked, ...locked].map((a) => (
            <li key={a.code}>
              <AchievementCard achievement={a} />
            </li>
          ))}
        </ul>
      </section>
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

function Activity({ days }: { days: { day: string; solved: number }[] }) {
  const max = Math.max(1, ...days.map((d) => d.solved));

  return (
    <div className="grid grid-cols-10 gap-1.5" style={{ maxWidth: "22rem" }}>
      {days.map((d) => {
        const level = d.solved === 0 ? 0 : Math.ceil((d.solved / max) * 3);
        const bg = ["var(--surface)", "var(--accent-200)", "var(--accent-300)", "var(--accent)"][
          level
        ];
        return (
          <span
            key={d.day}
            title={`${new Date(d.day).toLocaleDateString("ru", {
              day: "numeric",
              month: "long",
              timeZone: "UTC",
            })} — решено ${d.solved}`}
            className="aspect-square w-full rounded-md"
            style={{ background: bg }}
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
      className="card flex gap-4 p-5"
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

        {!a.unlocked && (
          <div className="mt-3">
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
        )}
      </div>
    </div>
  );
}
