"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Coins,
  Flag,
  Flame,
  ShoppingBag,
  CalendarDays,
  Lightbulb,
  Shield,
  Swords,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Trophy,
  Volume2,
  VolumeX,
  User as UserIcon,
  Users,
  Zap,
} from "lucide-react";
import type { User } from "@/lib/api";
import { useEffect, useState } from "react";
import { EXAM, daysUntilExam, formatExamDate, plural } from "@/lib/exam";
import { nickStyle } from "@/lib/cosmetics";
import Avatar from "./Avatar";
import { setSoundEnabled, soundEnabled } from "@/lib/sound";
import IdeaButton from "./IdeaButton";

type NavItem = {
  href: string;
  label: string;
  icon: typeof UserIcon;
  soon?: boolean;
};

const NAV: NavItem[] = [
  { href: "/app/profile", label: "Профиль", icon: UserIcon },
  { href: "/app/daily", label: "Задача дня", icon: CalendarDays },
  { href: "/app/quiz", label: "Квизы", icon: Zap },
  { href: "/app/stats", label: "Статистика", icon: BarChart3 },
  { href: "/app/mocks", label: "Пробники", icon: ClipboardList },
  { href: "/app/duels", label: "Дуэли", icon: Swords },
  { href: "/app/friends", label: "Друзья", icon: Users },
  { href: "/app/shop", label: "Магазин", icon: ShoppingBag },
  { href: "/app/league", label: "Лига", icon: Shield },
  { href: "/app/tournaments", label: "Турниры", icon: Flag },
  { href: "/app/rating", label: "Лидерборд", icon: Trophy },
  { href: "/app/suggest", label: "Своя задача", icon: Lightbulb },
];

const ADMIN_ITEM: NavItem = {
  href: "/app/admin",
  label: "Админка",
  icon: Shield,
};

export default function Sidebar({
  user,
  collapsed,
  onToggle,
}: {
  user: User | null;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const pathname = usePathname();
  const [days, setDays] = useState<number | null>(null);
  const [sound, setSound] = useState(true);

  useEffect(() => {
    setDays(daysUntilExam());
    setSound(soundEnabled());
  }, []);

  return (
    <aside
      className="sticky top-0 flex h-screen shrink-0 flex-col justify-between overflow-y-auto border-r"
      style={{
        width: collapsed ? 72 : 258,
        padding: collapsed ? "22px 10px" : "22px 16px",
        borderColor: "var(--divider)",
        background: "var(--card)",
        transition: "width 0.18s ease",
      }}
    >
      <div>
        <div
          className="mb-[26px] flex items-center"
          style={{ justifyContent: collapsed ? "center" : "space-between" }}
        >
          {!collapsed && (
            <Link
              href="/"
              className="h"
              style={{ fontSize: 25, fontWeight: 800, marginLeft: 8 }}
            >
              Боталка<span style={{ color: "var(--accent)" }}>.</span>
            </Link>
          )}
          <button
            className="flex h-8 w-8 items-center justify-center rounded-[10px]"
            style={{ background: "var(--surface)", color: "var(--n-600)" }}
            onClick={onToggle}
            aria-label={collapsed ? "Развернуть меню" : "Свернуть меню"}
            title={collapsed ? "Развернуть меню" : "Свернуть меню"}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        <nav className="space-y-1">
          {(user?.is_admin ? [...NAV, ADMIN_ITEM] : NAV).map(
            ({ href, label, icon: Icon, soon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={soon ? "#" : href}
                  aria-disabled={soon}
                  onClick={(e) => soon && e.preventDefault()}
                  title={collapsed ? label : undefined}
                  className="flex items-center gap-[11px] rounded-[14px] transition"
                  style={{
                    padding: collapsed ? "10px 0" : "10px 12px",
                    justifyContent: collapsed ? "center" : "flex-start",
                    fontSize: 14.5,
                    background: active ? "var(--accent-100)" : "transparent",
                    color: active
                      ? "var(--accent-700)"
                      : soon
                        ? "var(--n-400)"
                        : "var(--text)",
                    cursor: soon ? "default" : "pointer",
                    fontWeight: active ? 700 : 400,
                  }}
                >
                  <Icon size={18} className="shrink-0" />
                  {!collapsed && label}
                  {!collapsed && soon && (
                    <span className="ml-auto text-[11px]">скоро</span>
                  )}
                </Link>
              );
            },
          )}
        </nav>
      </div>

      <div className="space-y-4">
        {!collapsed && (
        <div
          className="space-y-2 rounded-xl p-3"
          style={{ background: "var(--surface)" }}
        >
          <button
            className="flex w-full items-center justify-between gap-2 text-sm font-medium"
            onClick={() => {
              const next = !sound;
              setSound(next);
              setSoundEnabled(next);
            }}
          >
            <span className="flex items-center gap-2">
              {sound ? (
                <Volume2 size={17} style={{ color: "var(--accent)" }} />
              ) : (
                <VolumeX size={17} className="muted" />
              )}
              Звук
            </span>
            <span
              className="rounded-full px-2 py-0.5 text-xs font-semibold"
              style={{
                background: sound ? "var(--accent-100)" : "var(--divider)",
                color: sound ? "var(--accent-700)" : "var(--n-600)",
              }}
            >
              {sound ? "вкл" : "выкл"}
            </span>
          </button>

          <div
            className="border-t pt-2"
            style={{ borderColor: "var(--divider)" }}
          >
            <IdeaButton />
          </div>
        </div>
        )}

        {!collapsed && (
        <div>
          <p className="eyebrow">До экзамена</p>
          <p className="h mt-1 text-2xl">
            {days === null
              ? "—"
              : `${days} ${plural(days, "день", "дня", "дней")}`}
          </p>
          <p className="muted mt-0.5 text-xs">
            {EXAM.subject} · {formatExamDate()}
            {EXAM.approximate && " (ориентировочно)"}
          </p>
        </div>
        )}

        {user && (
          <Link
            href="/app/profile"
            className="flex items-center gap-3 border-t pt-4"
            style={{
              borderColor: "var(--divider)",
              justifyContent: collapsed ? "center" : "flex-start",
            }}
            title={collapsed ? user.display_name : undefined}
          >
            <Avatar
              name={user.display_name}
              avatar={user.cosmetics?.avatar}
              frame={user.cosmetics?.frame}
              size={38}
              rounded="rounded-full"
            />
            {!collapsed && (
            <span className="min-w-0">
              <span
                className={`block truncate text-sm ${nickStyle(user.cosmetics?.nick_color).className}`}
                style={nickStyle(user.cosmetics?.nick_color).style}
              >
                {user.cosmetics?.prefix && `${user.cosmetics.prefix} `}
                {user.display_name}
              </span>
              {user.coins > 0 && (
                <span
                  className="mr-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
                  style={{ background: "#fdf3dd", color: "#c98a00" }}
                >
                  <Coins size={12} />
                  {user.coins}
                </span>
              )}
              {user.streak_days > 0 ? (
                <span
                  className="mt-0.5 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
                  style={{
                    background:
                      user.streak_days >= 7
                        ? "var(--accent-2-100)"
                        : "var(--surface)",
                    color:
                      user.streak_days >= 7
                        ? "var(--accent-2)"
                        : "var(--n-700)",
                  }}
                >
                  <Flame
                    size={14}
                    style={{ color: "var(--accent-2)" }}
                    fill={user.streak_days >= 7 ? "var(--accent-2)" : "none"}
                  />
                  {user.streak_days}
                </span>
              ) : (
                <span className="muted text-xs">
                  {user.is_guest ? "без входа" : "серии пока нет"}
                </span>
              )}
            </span>
            )}
          </Link>
        )}
      </div>
    </aside>
  );
}
