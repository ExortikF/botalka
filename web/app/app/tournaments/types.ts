export type Rule = {
  event: string;
  title: string;
  points: number;
  daily_cap: number | null;
  task_numbers: number[];
  exclude_hints: boolean;
};

export type Prize = {
  place_from: number;
  place_to: number;
  coins: number;
  item_code: string | null;
  item_title: string | null;
};

export type Row = {
  place: number;
  user_id: number;
  display_name: string;
  nick_color: string | null;
  prefix: string | null;
  avatar: string | null;
  frame: string | null;
  points: number;
  is_you: boolean;
  prize_coins: number;
  prize_item: string | null;
};

export type Tournament = {
  id: number;
  title: string;
  description: string | null;
  color: string;
  status: string;
  starts_at: string;
  ends_at: string;
  min_rating: number | null;
  state: string;
  seconds_left: number | null;
  eligible: boolean;
  ineligible_reason: string | null;
  rules: Rule[];
  prizes: Prize[];
  rows: Row[];
  your_place: number | null;
  your_points: number;
};

export const STATE_COLOR: Record<string, string> = {
  идёт: "var(--accent)",
  "ждёт старта": "var(--n-600)",
  "подводим итоги": "#c98a00",
  завершён: "var(--n-600)",
};

/** «2 дня» / «5 ч» / «12 мин» — точнее не нужно, а секунды создают суету. */
export function formatLeft(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  if (days > 0) return `${days} дн.`;
  const hours = Math.floor(seconds / 3600);
  if (hours > 0) return `${hours} ч`;
  return `${Math.max(1, Math.round(seconds / 60))} мин`;
}

export function placeLabel(prize: Prize): string {
  return prize.place_from === prize.place_to
    ? `${prize.place_from} место`
    : `${prize.place_from}–${prize.place_to} места`;
}
