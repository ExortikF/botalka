/** Пусто = тот же origin: Next проксирует /api на бэкенд (см. next.config.mjs). */
export const API_URL = "";

export type User = {
  id: number;
  is_guest: boolean;
  is_admin: boolean;
  username: string | null;
  display_name: string;
  avatar_url: string | null;
  rating: number;
  streak_days: number;
};

export type Task = {
  id: number;
  task_type_number: number;
  task_type_title: string;
  statement: string;
  image_url: string | null;
  answer_type: string;
  hints: string[];
  source: string | null;
};

export type Quiz = { id: number; mode: string; tasks: Task[] };

export type AnswerResult = {
  is_correct: boolean;
  used_hint: boolean;
  correct_answer: string;
  solution: string | null;
  score: number;
};

export type TaskType = { id: number; number: number; title: string; tasks_count: number };

export type StatsRow = {
  task_type_number: number;
  task_type_title: string;
  total: number;
  correct: number;
};

export type QuizResult = {
  quiz_id: number;
  score: number;
  total: number;
  finished: boolean;
  streak_days: number;
  items: {
    task_id: number;
    statement: string;
    task_type_number: number;
    your_answer: string;
    correct_answer: string;
    is_correct: boolean;
    used_hint: boolean;
    solution: string | null;
  }[];
};

/** credentials: include обязателен — сессия живёт в httpOnly-куке. */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Ошибка ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const getMe = () => api<User>("/api/auth/me");
export const logout = () => api<{ ok: boolean }>("/api/auth/logout", { method: "POST" });
export const getTaskTypes = (subject = "math_prof") =>
  api<TaskType[]>(`/api/task-types?subject=${subject}`);
export const getStats = () => api<StatsRow[]>("/api/stats");

export type Subject = {
  id: number | null;
  slug: string;
  title: string;
  tasks_count: number;
  types_count: number;
  solved: number;
  available: boolean;
};

export type QuizPreset = "weak" | "mistakes" | "unsolved";

export const getSubjects = () => api<Subject[]>("/api/subjects");

export type PublicConfig = { dev_login: boolean; bot_username: string };
export const getConfig = () => api<PublicConfig>("/api/config");

/** Вход без Telegram. Доступен, только если на бэкенде включён DEV_LOGIN. */
export const devLogin = (isAdmin = false) =>
  api<User>("/api/auth/dev-login", {
    method: "POST",
    body: JSON.stringify({
      tg_id: isAdmin ? 900002 : 900001,
      display_name: isAdmin ? "Тестовый админ" : "Тестовый ученик",
      is_admin: isAdmin,
    }),
  });

export const startQuiz = (params: {
  subject?: string;
  taskTypeIds?: number[];
  /** Сколько задач взять из каждого номера — задаётся стрелочками в плитке темы. */
  selection?: { task_type_id: number; count: number }[];
  preset?: QuizPreset | null;
  length?: number;
}) =>
  api<Quiz>("/api/quiz/start", {
    method: "POST",
    body: JSON.stringify({
      subject: params.subject ?? "math_prof",
      task_type_ids: params.taskTypeIds ?? [],
      selection: params.selection ?? [],
      preset: params.preset ?? null,
      length: params.length ?? 10,
    }),
  });

export const sendAnswer = (
  quizId: number,
  taskId: number,
  answer: string,
  timeSpentMs: number,
  usedHint: boolean,
) =>
  api<AnswerResult>(`/api/quiz/${quizId}/answer`, {
    method: "POST",
    body: JSON.stringify({
      task_id: taskId,
      answer,
      time_spent_ms: timeSpentMs,
      used_hint: usedHint,
    }),
  });

export const getQuizResult = (quizId: number) => api<QuizResult>(`/api/quiz/${quizId}/result`);


// ---------------------------------------------------------------- дуэли по ссылке

export type DuelSide = {
  name: string;
  score: number | null;
  time_ms: number | null;
  finished: boolean;
};

export type Duel = {
  code: string;
  state: "waiting" | "finished" | "expired";
  total: number;
  challenger: DuelSide;
  opponent: DuelSide | null;
  winner: "challenger" | "opponent" | "draw" | null;
  your_side: "challenger" | "opponent" | null;
  can_play: boolean;
  expires_at: string | null;
};

export type DuelListItem = {
  code: string;
  state: string;
  role: "challenger" | "opponent";
  opponent_name: string | null;
  your_score: number | null;
  their_score: number | null;
  outcome: "win" | "loss" | "draw" | null;
  created_at: string;
};

export const createDuel = (taskTypeIds: number[] = [], length = 7, opponentId?: number) =>
  api<Duel>("/api/duels", {
    method: "POST",
    body: JSON.stringify({
      subject: "math_prof",
      task_type_ids: taskTypeIds,
      length,
      opponent_id: opponentId ?? null,
    }),
  });

export const getDuel = (code: string) => api<Duel>(`/api/duels/${code}`);
export const playDuel = (code: string) => api<Quiz>(`/api/duels/${code}/play`, { method: "POST" });
export const getMyDuels = () => api<DuelListItem[]>("/api/duels");
