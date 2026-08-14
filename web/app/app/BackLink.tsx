"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";

/**
 * Стрелка «назад», которая действительно ведёт назад.
 *
 * Раньше на таких страницах стояла жёсткая ссылка («к лидерборду»), и человек,
 * пришедший из клана, возвращался туда, где вообще не был. Если истории нет
 * (страницу открыли по прямой ссылке), уходим на запасной адрес.
 */
export default function BackLink({
  fallback,
  fallbackLabel,
}: {
  fallback: string;
  fallbackLabel: string;
}) {
  const router = useRouter();
  const [canGoBack, setCanGoBack] = useState(false);

  // window на сервере нет, поэтому проверяем после монтирования.
  useEffect(() => {
    setCanGoBack(window.history.length > 1);
  }, []);

  const className = "muted flex w-fit items-center gap-1.5 text-sm hover:underline";

  if (!canGoBack)
    return (
      <Link className={className} href={fallback}>
        <ArrowLeft size={15} /> {fallbackLabel}
      </Link>
    );

  return (
    <button className={className} onClick={() => router.back()}>
      <ArrowLeft size={15} /> Назад
    </button>
  );
}
