"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import Avatar from "../../Avatar";
import { api } from "@/lib/api";
import { nickStyle } from "@/lib/cosmetics";
import type { Clan } from "../types";
import { MIN_FOR_BOARD, POLICY, ROLE } from "../types";

export default function ClanPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [clan, setClan] = useState<Clan | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api<Clan>(`/api/clans/${id}`)
      .then(setClan)
      .catch((e: Error) => setError(e.message));
  }, [id]);

  useEffect(load, [load]);

  async function join() {
    setError("");
    try {
      await api(`/api/clans/${id}/join`, { method: "POST" });
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (error)
    return (
      <div className="space-y-4">
        <p style={{ color: "var(--accent-2)" }}>{error}</p>
        <Link className="btn-ghost" href="/app/clans">
          К кланам
        </Link>
      </div>
    );

  if (!clan) return <p className="muted">Загрузка…</p>;

  return (
    <div className="page">
      <Link
        className="muted flex items-center gap-1.5 text-sm hover:underline"
        href="/app/clans"
      >
        <ArrowLeft size={15} /> Все кланы
      </Link>

      <section
        className="card"
        style={{ padding: "26px 28px", borderLeft: `4px solid ${clan.color}` }}
      >
        <div className="flex flex-wrap items-center gap-3">
          <span
            className="h rounded-lg px-2.5 py-1"
            style={{ background: `${clan.color}1a`, color: clan.color }}
          >
            {clan.tag}
          </span>
          <h1 className="page-title" style={{ fontSize: 24 }}>
            {clan.name}
          </h1>

          {clan.your_role ? (
            <span className="muted text-sm">
              ты {ROLE[clan.your_role] ?? clan.your_role}
            </span>
          ) : clan.requested ? (
            <span className="muted text-sm">заявка отправлена</span>
          ) : clan.can_join ? (
            <button className="btn ml-auto text-sm" onClick={join}>
              {clan.join_policy === "request" ? "Подать заявку" : "Вступить"}
            </button>
          ) : (
            <span className="muted ml-auto text-sm">
              {clan.members_count >= clan.max_members
                ? "мест нет"
                : POLICY[clan.join_policy]}
            </span>
          )}
        </div>

        {clan.description && (
          <p className="muted mt-2 text-sm">{clan.description}</p>
        )}
      </section>

      <section className="grid gap-3 sm:grid-cols-4">
        <div className="tile">
          <p className="tile-value">
            {clan.members_count}
            <span className="tile-unit">из {clan.max_members}</span>
          </p>
          <p className="tile-label">в составе</p>
        </div>
        <div className="tile">
          <p className="tile-value" style={{ color: clan.color }}>
            {clan.average_week}
          </p>
          <p className="tile-label">в среднем на активного</p>
        </div>
        <div className="tile">
          <p className="tile-value">{clan.points_week}</p>
          <p className="tile-label">решено за неделю всего</p>
        </div>
        <div className="tile">
          <p className="tile-value">{clan.active_week}</p>
          <p className="tile-label">решали на этой неделе</p>
        </div>
      </section>

      {clan.members_count < MIN_FOR_BOARD && (
        <p className="muted text-sm">
          Клан идёт вне зачёта: в таблицу попадают команды от {MIN_FOR_BOARD} человек.
        </p>
      )}

      <section className="space-y-2">
        <h2 className="section-title">Состав</h2>
        <ul className="space-y-2">
          {clan.members.map((member) => {
            const nick = nickStyle(member.nick_color);
            return (
              <li key={member.user_id}>
                <article className="row-card">
                  <Avatar
                    name={member.display_name}
                    avatar={member.avatar}
                    frame={member.frame}
                    size={32}
                    rounded="rounded-full"
                  />
                  <Link
                    className="min-w-0 flex-1 truncate hover:underline"
                    href={member.is_you ? "/app/profile" : `/app/u/${member.user_id}`}
                  >
                    <span className={nick.className} style={nick.style}>
                      {member.prefix && `${member.prefix} `}
                      {member.display_name}
                    </span>
                  </Link>
                  <span className="muted shrink-0 text-xs">
                    {ROLE[member.role] ?? member.role}
                  </span>
                  <span className="h w-10 shrink-0 text-right">
                    {member.solved_week}
                  </span>
                </article>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
