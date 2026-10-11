"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Trophy, X } from "lucide-react";
import { ACHIEVEMENT_EVENT, type Achievement } from "@/lib/achievements";
import { playAchievement } from "@/lib/sound";

const RARITY: Record<Achievement["rarity"], { label: string; color: string; bg: string }> = {
  bronze: { label: "бронза", color: "#8a5a2b", bg: "#f6ebe0" },
  silver: { label: "серебро", color: "#5b6570", bg: "#eef1f4" },
  gold: { label: "золото", color: "var(--gold)", bg: "#fbf1cf" },
};

const SHOW_MS = 6000;

/**
 * Поздравление в момент получения достижения. Живёт в общем макете, потому что
 * закрыть достижение можно откуда угодно — из квиза, дуэли или пробника.
 *
 * Несколько достижений сразу показываем по одному: три карточки внахлёст
 * читаются хуже, чем очередь.
 */
export default function AchievementToast() {
  const [queue, setQueue] = useState<Achievement[]>([]);

  useEffect(() => {
    function onUnlock(event: Event) {
      const fresh = (event as CustomEvent<Achievement[]>).detail;
      setQueue((current) => [...current, ...fresh]);
      playAchievement();
    }

    window.addEventListener(ACHIEVEMENT_EVENT, onUnlock);
    return () => window.removeEventListener(ACHIEVEMENT_EVENT, onUnlock);
  }, []);

  const dismiss = useCallback(() => setQueue((current) => current.slice(1)), []);

  const current = queue[0];

  useEffect(() => {
    if (!current) return;
    const timer = setTimeout(dismiss, SHOW_MS);
    return () => clearTimeout(timer);
  }, [current, dismiss]);

  if (!current) return null;

  const rarity = RARITY[current.rarity];

  return (
    <div
      className="achievement-toast card fixed bottom-6 right-6 z-50 flex w-80 items-start gap-3 p-4"
      role="status"
      style={{ boxShadow: "var(--shadow-lg)" }}
    >
      <span
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl"
        style={{ background: rarity.bg, color: rarity.color }}
      >
        <Trophy size={20} />
      </span>

      <span className="min-w-0 flex-1">
        <span className="eyebrow block" style={{ color: rarity.color }}>
          Достижение получено
        </span>
        <Link className="mt-0.5 block font-semibold hover:underline" href="/app/profile">
          {current.title}
        </Link>
        <span className="muted mt-0.5 block text-sm leading-snug">{current.description}</span>
        {queue.length > 1 && (
          <span className="muted mt-1 block text-xs">и ещё {queue.length - 1}</span>
        )}
      </span>

      <button className="muted p-1" onClick={dismiss} aria-label="Закрыть">
        <X size={15} />
      </button>
    </div>
  );
}
