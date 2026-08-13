import { api } from "@/lib/api";

export type Achievement = {
  code: string;
  title: string;
  description: string;
  rarity: "bronze" | "silver" | "gold";
  progress: number;
  target: number;
  unlocked: boolean;
};

export const ACHIEVEMENT_EVENT = "botalka:achievement";

/**
 * Спрашивает сервер, что человек получил с прошлой проверки, и, если что-то
 * есть, кидает событие — всплывашку рисует AchievementToast из общего макета.
 *
 * Вызывать после событий, которые могут закрыть достижение: конец квиза,
 * конец дуэли, конец пробника. Молча проглатывает ошибку: не показать
 * поздравление неприятно, но ломать этим экран результата нельзя.
 */
export async function checkAchievements(): Promise<void> {
  try {
    const fresh = await api<Achievement[]>("/api/achievements/check", { method: "POST" });
    if (fresh.length > 0) {
      window.dispatchEvent(new CustomEvent(ACHIEVEMENT_EVENT, { detail: fresh }));
    }
  } catch {
    // молча
  }
}
