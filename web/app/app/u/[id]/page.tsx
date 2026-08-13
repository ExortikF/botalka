"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ArrowLeft, Flame, Swords } from "lucide-react";
import Avatar from "../../Avatar";
import { api, createDuel } from "@/lib/api";
import {
  auroraClass,
  cardBackground,
  nickStyle,
  plateStyle,
} from "@/lib/cosmetics";
import { plural } from "@/lib/exam";

type PublicProfile = {
  user_id: number;
  display_name: string;
  rank: string;
  rank_color: string;
  rating: number;
  cosmetics: {
    nick_color: string | null;
    prefix: string | null;
    frame: string | null;
    avatar: string | null;
    card_bg: string | null;
    name_plate: string | null;
  };
  solved_total: number;
  accuracy: number;
  streak_days: number;
  streak_record: number;
  achievements_unlocked: number;
  achievements_total: number;
  duels_played: number;
  duels_won: number;
  is_friend: boolean;
  is_you: boolean;
};

export default function PublicProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<PublicProfile>(`/api/users/${id}`)
      .then(setProfile)
      .catch((e: Error) => setError(e.message));
  }, [id]);

  async function challenge() {
    if (!profile) return;
    const duel = await createDuel([], 7, profile.user_id);
    window.location.href = `/app/duels/${duel.code}`;
  }

  if (error)
    return (
      <div className="space-y-4">
        <p style={{ color: "var(--accent-2)" }}>{error}</p>
        <Link className="btn-ghost" href="/app/rating">
          К лидерборду
        </Link>
      </div>
    );

  if (!profile) return <p className="muted">Загрузка…</p>;

  const nick = nickStyle(profile.cosmetics.nick_color);
  const bg = cardBackground(profile.cosmetics.card_bg);
  const plate = plateStyle(profile.cosmetics.name_plate);

  return (
    <div className="space-y-6">
      <Link
        className="muted flex items-center gap-1.5 text-sm hover:underline"
        href="/app/rating"
      >
        <ArrowLeft size={15} /> К лидерборду
      </Link>

      <section
        className={`card flex flex-wrap items-center gap-5 p-7 ${auroraClass(profile.cosmetics.card_bg)} ${plate.className}`}
        style={{
          ...bg.style,
          ...plate.style,
          color: bg.dark ? "#fff" : undefined,
        }}
      >
        <Avatar
          name={profile.display_name}
          avatar={profile.cosmetics.avatar}
          frame={profile.cosmetics.frame}
          size={72}
        />

        <div className="min-w-0 flex-1">
          <h1 className="flex flex-wrap items-center gap-3 text-2xl">
            <span className={nick.className} style={nick.style}>
              {profile.cosmetics.prefix && `${profile.cosmetics.prefix} `}
              {profile.display_name}
            </span>
            <span
              className="rounded-full px-3 py-1 text-xs font-semibold"
              style={{
                background: `${profile.rank_color}1a`,
                color: profile.rank_color,
              }}
            >
              {profile.rank}
            </span>
          </h1>
          <p className="mt-1 text-sm" style={{ opacity: 0.75 }}>
            рейтинг {profile.rating}
            {profile.is_friend && " · у вас дружба"}
          </p>
        </div>

        {!profile.is_you && profile.is_friend && (
          <button className="btn btn-accent2" onClick={challenge}>
            <Swords size={16} /> Вызвать
          </button>
        )}
      </section>

      <section className="grid gap-4 sm:grid-cols-4">
        <Metric
          value={profile.streak_days}
          label={`подряд · рекорд ${profile.streak_record}`}
          icon={<Flame size={15} style={{ color: "var(--accent-2)" }} />}
        />
        <Metric value={profile.solved_total} label="задач решено" />
        <Metric value={`${profile.accuracy}%`} label="верных ответов" />
        <Metric
          value={`${profile.achievements_unlocked}/${profile.achievements_total}`}
          label="достижений"
        />
      </section>

      <section className="card p-6">
        <h2 className="flex items-center gap-2 text-xl">
          <Swords size={18} style={{ color: "var(--accent-2)" }} /> Дуэли
        </h2>
        <p className="muted mt-2 text-sm">
          {profile.duels_played === 0
            ? "Онлайн-матчей пока не играл."
            : `${profile.duels_played} ${plural(profile.duels_played, "матч", "матча", "матчей")}, из них ${profile.duels_won} ${plural(profile.duels_won, "победа", "победы", "побед")}.`}
        </p>
      </section>
    </div>
  );
}

function Metric({
  value,
  label,
  icon,
}: {
  value: number | string;
  label: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="card p-5">
      <p className="h flex items-baseline gap-1.5 text-3xl">
        {icon}
        {value}
      </p>
      <p className="muted mt-1 text-sm leading-snug">{label}</p>
    </div>
  );
}
