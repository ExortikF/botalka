/**
 * Дата экзамена. Расписание ЕГЭ-2027 на момент написания не опубликовано —
 * стоит ориентировочная дата по прошлым годам. **Проверить и обновить**, когда
 * Рособрнадзор опубликует расписание.
 */
export const EXAM = {
  year: 2027,
  subject: "Математика профиль",
  date: new Date("2027-05-28T00:00:00+03:00"),
  approximate: true,
};

export function daysUntilExam(now = new Date()): number {
  const ms = EXAM.date.getTime() - now.getTime();
  return Math.max(0, Math.ceil(ms / 86_400_000));
}

/**
 * Часовой пояс задан явно: сервер рендерит в UTC, браузер — в своём поясе,
 * и без этого «28 мая» на клиенте превращается в «27 мая» на сервере,
 * что ломает гидратацию.
 */
export function formatExamDate(): string {
  return EXAM.date.toLocaleDateString("ru", {
    day: "numeric",
    month: "long",
    timeZone: "Europe/Moscow",
  });
}

/** «124 дня», «2 дня», «1 день» */
export function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}
