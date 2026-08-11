export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type User = {
  id: number;
  username: string | null;
  display_name: string;
  avatar_url: string | null;
  rating: number;
  streak_days: number;
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
