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

export type Problem = {
  letter: string;
  task_id: number;
  points: number;
  task_type_number: number;
  task_type_title: string;
  statement: string;
  image_url: string | null;
  answer_type: string;
  solved: boolean;
  wrong: number;
  minute: number | null;
  solved_count: number;
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
  penalty: number;
  solved: number;
  cells: Record<string, string>;
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
  format: "contest" | "marathon";
  penalty_minutes: number;
  started: boolean;
  over: boolean;
  seconds_to_start: number | null;
  rules: Rule[];
  prizes: Prize[];
  problems: Problem[];
  rows: Row[];
  your_place: number | null;
  your_points: number;
  your_penalty: number;
};

export type SubmitResult = {
  is_correct: boolean;
  upsolve: boolean;
  wrong: number;
  minute: number | null;
  message: string;
};

/** «1:23:45» — на контесте важны и часы, и секунды до конца. */
export function formatClock(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

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
