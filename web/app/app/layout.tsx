"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import AchievementToast from "./AchievementToast";
import { getMe, type User } from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const pathname = usePathname();

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null));
  }, [pathname]);

  return (
    <div className="flex min-h-screen" style={{ background: "var(--surface)" }}>
      <Sidebar user={user} />
      <main className="min-w-0 flex-1 p-8">
        <div className="mx-auto max-w-4xl">{children}</div>
      </main>
      <AchievementToast />
    </div>
  );
}
