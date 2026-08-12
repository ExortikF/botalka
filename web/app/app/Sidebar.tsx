"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Flame,
  Shield,
  Swords,
  ClipboardList,
  Trophy,
  User as UserIcon,
  Users,
  Zap,
} from "lucide-react";
import type { User } from "@/lib/api";
import { useEffect, useState } from "react";
import { EXAM, daysUntilExam, formatExamDate, plural } from "@/lib/exam";
import { initials } from "@/lib/format";

type NavItem = {
  href: string;
  label: string;
  icon: typeof UserIcon;
  soon?: boolean;
};

const NAV: NavItem[] = [
  { href: "/app/profile", label: "Профиль", icon: UserIcon },
  { href: "/app/quiz", label: "Квизы", icon: Zap },
  { href: "/app/mocks", label: "Пробники", icon: ClipboardList },
  { href: "/app/subjects", label: "Предметы", icon: BookOpen, soon: true },
  { href: "/app/duels", label: "Дуэли", icon: Swords },
  { href: "/app/friends", label: "Друзья", icon: Users },
  { href: "/app/rating", label: "Лидерборд", icon: Trophy },
];

const ADMIN_ITEM: NavItem = { href: "/app/admin", label: "Админка", icon: Shield };

export default function Sidebar({ user }: { user: User | null }) {
  const pathname = usePathname();
  const [days, setDays] = useState<number | null>(null);
  useEffect(() => setDays(daysUntilExam()), []);

  return (
    <aside
      className="flex w-64 shrink-0 flex-col justify-between border-r p-5"
      style={{ borderColor: "var(--divider)", background: "var(--card)" }}
    >
      <div>
        <Link href="/" className="h mb-8 block text-3xl tracking-tight">
          Боталка<span style={{ color: "var(--accent)" }}>.</span>
        </Link>

        <nav className="space-y-1">
          {(user?.is_admin ? [...NAV, ADMIN_ITEM] : NAV).map(({ href, label, icon: Icon, soon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={soon ? "#" : href}
                aria-disabled={soon}
                onClick={(e) => soon && e.preventDefault()}
                className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition"
                style={{
                  background: active ? "var(--accent-100)" : "transparent",
                  color: active ? "var(--accent-700)" : soon ? "var(--n-400)" : "var(--text)",
                  cursor: soon ? "default" : "pointer",
                  fontWeight: active ? 600 : 400,
                }}
              >
                <Icon size={18} />
                {label}
                {soon && <span className="ml-auto text-[11px]">скоро</span>}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="space-y-5">
        <div>
          <p className="eyebrow">До экзамена</p>
          <p className="h mt-1 text-2xl">
            {days === null ? "—" : `${days} ${plural(days, "день", "дня", "дней")}`}
          </p>
          <p className="muted mt-0.5 text-xs">
            {EXAM.subject} · {formatExamDate()}
            {EXAM.approximate && " (ориентировочно)"}
          </p>
        </div>

        {user && (
          <div className="flex items-center gap-3 border-t pt-4" style={{ borderColor: "var(--divider)" }}>
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
              style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
            >
              {initials(user.display_name)}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm">{user.display_name}</span>
              <span className="muted flex items-center gap-1 text-xs">
                {user.streak_days > 0 ? (
                  <>
                    <Flame size={12} style={{ color: "var(--accent-2)" }} />
                    {user.streak_days} {plural(user.streak_days, "день", "дня", "дней")} подряд
                  </>
                ) : user.is_guest ? (
                  "без входа"
                ) : (
                  "серии пока нет"
                )}
              </span>
            </span>
          </div>
        )}
      </div>
    </aside>
  );
}
