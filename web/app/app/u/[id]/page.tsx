"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { ArrowLeft, Flame, Swords, Trophy } from "lucide-react";
import Avatar from "../../Avatar";
import BackLink from "../../BackLink";
import { CLANS_ENABLED } from "@/lib/features";
import { api, createDuel } from "@/lib/api";
import {
  auroraClass,
  cardBackground,
  nickStyle,
  plateStyle,
} from "@/lib/cosmetics";
import { plural } from "@/lib/exam";

type PublicAchievement = {
  code: string;
  title: string;
  description: string;
  rarity: "bronze" | "silver" | "gold";
  unlocked_at: string | null;
};

const RARITY: Record<
  PublicAchievement["rarity"],
  { label: string; color: string; bg: string }
> = {
  bronze: { label: "бронза", color: "#8a5a2b", bg: "#f6ebe0" },
  silver: { label: "серебро", color: "#5b6570", bg: "#eef1f4" },
  gold: { label: "золото", color: "#8a6d0b", bg: "#fbf1cf" },
};

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
  achievements: PublicAchievement[];
  duels_played: number;
  duels_won: number;
  is_friend: boolean;
  is_you: boolean;
  clan: {
    id: number;
    name: string;
    tag: string;
    color: string;
    role: string;
  } | null;
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
      <BackLink fallback="/app/rating" fallbackLabel="К лидерборду" />

      <section
        className={`card flex flex-wrap items-center gap-[18px] p-[30px] ${auroraClass(profile.cosmetics.card_bg)} ${plate.className}`}
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
            {CLANS_ENABLED && profile.clan && (
              <Link
                href={`/app/clans/${profile.clan.id}`}
                className="h flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-sm"
                style={
                  bg.dark
                    ? { background: "rgba(255,255,255,.2)", color: "#fff" }
                    : { background: `${profile.clan.color}1a`, color: profile.clan.color }
                }
                title={profile.clan.name}
              >
                {profile.clan.tag}
              </Link>
            )}

            <span
              className="rounded-full px-3 py-1 text-xs font-bold"
              style={
                bg.dark
                  ? { background: "rgba(255,255,255,.24)", color: "#fff" }
                  : { background: `${profile.rank_color}1a`, color: profile.rank_color }
              }
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

      <section className="grid gap-3 sm:grid-cols-4">
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

      <section className="space-y-3">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="flex items-center gap-2 text-xl">
            <Trophy size={18} style={{ color: "var(--accent-2)" }} /> Достижения
          </h2>
          <span className="muted text-sm">
            {profile.achievements_unlocked} из {profile.achievements_total}
          </span>
        </div>

        {profile.achievements.length === 0 ? (
          <p className="muted text-sm">
            Пока ни одного — {profile.is_you ? "самое время начать" : "всё впереди"}.
          </p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {profile.achievements.map((item) => {
              const rarity = RARITY[item.rarity];
              return (
                <li key={item.code} className="card flex items-start gap-3 p-4">
                  <span
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                    style={{ background: rarity.bg, color: rarity.color }}
                  >
                    <Trophy size={17} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{item.title}</span>
                    <span className="muted mt-0.5 block text-sm leading-snug">
                      {item.description}
                    </span>
                    {item.unlocked_at && (
                      <span className="muted mt-1 block text-xs">
                        {new Date(item.unlocked_at).toLocaleDateString("ru", {
                          day: "numeric",
                          month: "long",
                          year: "numeric",
                        })}
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
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
    <div className="tile">
      <p className="tile-value">
        {icon}
        {value}
      </p>
      <p className="tile-label">{label}</p>
    </div>
  );
}
