"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import AchievementToast from "./AchievementToast";
import { getMe, USER_EVENT, type User } from "@/lib/api";

const COLLAPSE_KEY = "botalka:sidebar-collapsed";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null));
  }, [pathname]);

  // Баланс и косметика меняются без перехода по маршруту — слушаем событие,
  // иначе в сайдбаре висит старое число до следующей навигации.
  useEffect(() => {
    const refresh = () => {
      getMe()
        .then(setUser)
        .catch(() => {});
    };
    window.addEventListener(USER_EVENT, refresh);
    return () => window.removeEventListener(USER_EVENT, refresh);
  }, []);

  // Читаем после монтирования: на сервере localStorage нет, а разное значение
  // на сервере и клиенте — это ошибка гидратации.
  useEffect(() => {
    setCollapsed(localStorage.getItem(COLLAPSE_KEY) === "1");
  }, []);

  function toggle() {
    setCollapsed((value) => {
      localStorage.setItem(COLLAPSE_KEY, value ? "0" : "1");
      return !value;
    });
  }

  return (
    <div className="flex min-h-screen" style={{ background: "var(--surface)" }}>
      <Sidebar user={user} collapsed={collapsed} onToggle={toggle} />

      {/* Контент центрируется в оставшемся месте, а не прижимается к меню:
          на широком экране иначе всё уезжает влево. */}
      <main className="min-w-0 flex-1" style={{ padding: "38px 32px 60px" }}>
        <div className="mx-auto w-full" style={{ maxWidth: 1180 }}>
          {children}
        </div>
      </main>

      <AchievementToast />
    </div>
  );
}
