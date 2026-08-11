"use client";

import Link from "next/link";
import { Flame } from "lucide-react";
import type { User } from "@/lib/api";
import { plural } from "@/lib/exam";

/** Правый верхний угол: стрик и вход в профиль. */
export default function TopBar({ user }: { user: User | null }) {
  return (
    <div className="mb-6 flex items-center justify-end gap-4">
      {user && user.streak_days > 0 && (
        <span className="muted flex items-center gap-1.5 text-sm">
          <Flame size={15} style={{ color: "var(--accent-2)" }} />
          {user.streak_days} {plural(user.streak_days, "день", "дня", "дней")} подряд
        </span>
      )}

      <Link
        href="/app/profile"
        title="Профиль и статистика"
        className="flex items-center gap-2 rounded-full py-1 pl-1 pr-3 transition hover:bg-[var(--surface)]"
      >
        <span
          className="flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold"
          style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
        >
          {user ? initials(user.display_name) : "—"}
        </span>
        <span className="hidden text-sm sm:inline">{user?.display_name ?? "Профиль"}</span>
      </Link>
    </div>
  );
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
