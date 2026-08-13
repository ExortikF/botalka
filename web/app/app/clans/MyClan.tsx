"use client";

import Link from "next/link";
import { useState } from "react";
import { Check, LogOut, Shield, UserMinus, X } from "lucide-react";
import Avatar from "../Avatar";
import { api } from "@/lib/api";
import { nickStyle } from "@/lib/cosmetics";
import type { Clan } from "./types";
import { MIN_FOR_BOARD, POLICY, ROLE } from "./types";

/** Свой клан: состав, заявки и управление. Показывается над таблицей кланов. */
export default function MyClan({
  clan,
  onChange,
}: {
  clan: Clan;
  onChange: () => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const canManage = clan.your_role === "leader" || clan.your_role === "officer";
  const isLeader = clan.your_role === "leader";

  async function act(path: string, init?: RequestInit, confirmText?: string) {
    if (confirmText && !confirm(confirmText)) return;
    setBusy(true);
    setError("");
    try {
      await api(path, { method: "POST", ...init });
      onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3">
      <div
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
          <h2 className="section-title">{clan.name}</h2>
          <span className="muted text-sm">
            ты {ROLE[clan.your_role ?? ""] ?? clan.your_role}
          </span>

          <span className="ml-auto flex gap-2">
            {!isLeader && (
              <button
                className="btn-ghost text-sm"
                disabled={busy}
                onClick={() => act("/api/clans/leave", undefined, "Выйти из клана?")}
              >
                <LogOut size={14} /> Выйти
              </button>
            )}
            {isLeader && (
              <button
                className="btn-ghost text-sm"
                disabled={busy}
                onClick={() =>
                  act(
                    `/api/clans/${clan.id}`,
                    { method: "DELETE" },
                    "Распустить клан? Участники останутся без клана.",
                  )
                }
              >
                Распустить
              </button>
            )}
          </span>
        </div>

        {clan.description && (
          <p className="muted mt-2 text-sm">{clan.description}</p>
        )}

        <div className="mt-5 grid gap-3 sm:grid-cols-4">
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
        </div>

        {clan.members_count < MIN_FOR_BOARD && (
          <p className="muted mt-3 text-sm">
            В зачёт клан попадёт с {MIN_FOR_BOARD} участников — позови ещё{" "}
            {MIN_FOR_BOARD - clan.members_count}.
          </p>
        )}

        <p className="muted mt-2 text-sm">
          Вступление: {POLICY[clan.join_policy] ?? clan.join_policy}
        </p>

        {error && (
          <p className="mt-3 text-sm" style={{ color: "var(--accent-2)" }}>
            {error}
          </p>
        )}
      </div>

      {clan.requests.length > 0 && (
        <div className="card space-y-2" style={{ padding: "20px 24px" }}>
          <h3 className="eyebrow">Заявки на вступление</h3>
          {clan.requests.map((person) => (
            <div key={person.user_id} className="flex items-center gap-3">
              <Avatar
                name={person.display_name}
                avatar={person.avatar}
                frame={person.frame}
                size={30}
                rounded="rounded-full"
              />
              <span className="min-w-0 flex-1 truncate">{person.display_name}</span>
              <button
                className="btn text-sm"
                disabled={busy}
                onClick={() =>
                  act(`/api/clans/${clan.id}/requests/${person.user_id}/accept`)
                }
              >
                <Check size={14} /> Принять
              </button>
              <button
                className="muted p-2"
                title="Отклонить"
                disabled={busy}
                onClick={() =>
                  act(`/api/clans/${clan.id}/requests/${person.user_id}/decline`)
                }
              >
                <X size={15} />
              </button>
            </div>
          ))}
        </div>
      )}

      <ul className="space-y-2">
        {clan.members.map((member) => {
          const nick = nickStyle(member.nick_color);
          return (
            <li key={member.user_id}>
              <article
                className="row-card"
                style={{
                  background: member.is_you ? "var(--accent-100)" : undefined,
                }}
              >
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

                {isLeader && !member.is_you && (
                  <button
                    className="muted shrink-0 text-xs hover:underline"
                    disabled={busy}
                    onClick={() =>
                      act(`/api/clans/${clan.id}/role/${member.user_id}`, {
                        body: JSON.stringify({
                          role: member.role === "officer" ? "member" : "officer",
                        }),
                      })
                    }
                  >
                    {member.role === "officer" ? "снять офицера" : "в офицеры"}
                  </button>
                )}

                {isLeader && !member.is_you && member.role !== "leader" && (
                  <button
                    className="muted shrink-0 text-xs hover:underline"
                    disabled={busy}
                    onClick={() =>
                      act(
                        `/api/clans/${clan.id}/role/${member.user_id}`,
                        { body: JSON.stringify({ role: "leader" }) },
                        `Передать руководство: ${member.display_name}? Ты станешь офицером.`,
                      )
                    }
                  >
                    сделать главой
                  </button>
                )}

                {canManage && !member.is_you && member.role !== "leader" && (
                  <button
                    className="muted shrink-0 p-1"
                    title="Исключить"
                    disabled={busy}
                    onClick={() =>
                      act(
                        `/api/clans/${clan.id}/kick/${member.user_id}`,
                        undefined,
                        `Исключить ${member.display_name}?`,
                      )
                    }
                  >
                    <UserMinus size={15} />
                  </button>
                )}

                <span className="h w-10 shrink-0 text-right">
                  {member.solved_week}
                </span>
              </article>
            </li>
          );
        })}
      </ul>

      {isLeader && clan.members_count > 1 && (
        <p className="muted flex items-center gap-1.5 text-xs">
          <Shield size={12} /> Глава не может просто выйти: сначала передай
          руководство кому-то из состава или распусти клан.
        </p>
      )}
    </section>
  );
}
