"use client";

import { useEffect, useRef } from "react";
import { API_URL, type User } from "@/lib/api";

declare global {
  interface Window {
    onTelegramAuth?: (user: Record<string, unknown>) => void;
    Telegram?: { WebApp?: { initData?: string; ready?: () => void } };
  }
}

type Props = {
  onLogin: (user: User) => void;
  onError: (message: string) => void;
};

/**
 * Два пути входа, оба проверяются подписью на сервере:
 *  - внутри Telegram Mini App берём initData и логинимся молча;
 *  - на сайте показываем официальный виджет Telegram Login.
 */
export default function TelegramLogin({ onLogin, onError }: Props) {
  const holder = useRef<HTMLDivElement>(null);
  const botUsername = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME;

  useEffect(() => {
    const send = async (path: string, body: unknown) => {
      const res = await fetch(`${API_URL}${path}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "не удалось войти");
      return data as User;
    };

    const initData = window.Telegram?.WebApp?.initData;
    if (initData) {
      window.Telegram?.WebApp?.ready?.();
      send("/api/auth/telegram/miniapp", { init_data: initData })
        .then(onLogin)
        .catch((e: Error) => onError(e.message));
      return;
    }

    const mount = holder.current;
    if (!botUsername || !mount) return;

    // StrictMode в dev монтирует эффект дважды — иначе получаем два виджета
    mount.innerHTML = "";

    window.onTelegramAuth = (user) => {
      send("/api/auth/telegram/widget", user)
        .then(onLogin)
        .catch((e: Error) => onError(e.message));
    };

    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", botUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "12");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    mount.appendChild(script);

    return () => {
      mount.innerHTML = "";
      delete window.onTelegramAuth;
    };
  }, [botUsername, onLogin, onError]);

  if (!botUsername) {
    return (
      <p className="muted text-sm">
        Вход выключен: не задан <code>NEXT_PUBLIC_TELEGRAM_BOT_USERNAME</code> в{" "}
        <code>.env</code>.
      </p>
    );
  }

  return <div ref={holder} />;
}
