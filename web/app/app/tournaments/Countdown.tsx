"use client";

import { useEffect, useState } from "react";

/**
 * Обратный отсчёт до момента, полученного с сервера.
 *
 * Считаем от разницы «сколько осталось на момент ответа», а не от абсолютного
 * времени конца: часы на телефоне ученика могут врать на минуты, а таймер
 * контеста должен совпадать с серверным.
 */
export function useCountdown(seconds: number | null): number | null {
  const [left, setLeft] = useState(seconds);

  useEffect(() => {
    setLeft(seconds);
    if (seconds === null) return;

    const deadline = Date.now() + seconds * 1000;
    const timer = setInterval(() => {
      setLeft(Math.max(0, Math.round((deadline - Date.now()) / 1000)));
    }, 1000);

    return () => clearInterval(timer);
  }, [seconds]);

  return left;
}

/** «02:14:07», а больше суток — «2 д 03:11:45». */
export function formatFull(seconds: number): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  const days = Math.floor(seconds / 86400);
  const rest = seconds % 86400;
  const clock = `${pad(Math.floor(rest / 3600))}:${pad(Math.floor((rest % 3600) / 60))}:${pad(rest % 60)}`;
  return days > 0 ? `${days} д ${clock}` : clock;
}

export default function Countdown({
  seconds,
  className,
  style,
}: {
  seconds: number | null;
  className?: string;
  style?: React.CSSProperties;
}) {
  const left = useCountdown(seconds);
  if (left === null) return null;

  return (
    <span className={className} style={style}>
      {formatFull(left)}
    </span>
  );
}
