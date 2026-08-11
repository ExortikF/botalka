/** Пусто = тот же origin: Next проксирует /api на бэкенд (см. next.config.mjs). */
export const API_URL = "";

export type User = {
  id: number;
  is_guest: boolean;
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
