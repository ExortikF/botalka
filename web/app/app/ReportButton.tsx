"use client";

import { useState } from "react";
import { Flag } from "lucide-react";
import { api } from "@/lib/api";

/**
 * «Нашли ошибку?» — намеренно неприметная ссылка под задачей.
 * Жалоба уходит в админку; задача из выдачи не пропадает, иначе банк можно
 * вычистить парой кликов.
 */
export default function ReportButton({
  taskId,
  givenAnswer,
}: {
  taskId: number;
  givenAnswer?: string;
}) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function send() {
    if (message.trim().length < 3) return;
    try {
      await api(`/api/tasks/${taskId}/report`, {
        method: "POST",
        body: JSON.stringify({ message, given_answer: givenAnswer ?? null }),
      });
      setSent(true);
      setOpen(false);
      setMessage("");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (sent)
    return <p className="muted text-xs">Спасибо, жалоба отправлена — разберёмся.</p>;

  if (!open)
    return (
      <button
        className="muted flex items-center gap-1.5 text-xs hover:underline"
        onClick={() => setOpen(true)}
      >
        <Flag size={12} /> Нашли ошибку?
      </button>
    );

  return (
    <div className="space-y-2 rounded-xl p-3" style={{ background: "var(--surface)" }}>
      <p className="text-xs font-medium">Что не так с задачей?</p>
      <textarea
        className="input text-sm"
        rows={2}
        autoFocus
        placeholder="Неверный ответ, опечатка, непонятное условие…"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
      />
      <div className="flex gap-2">
        <button className="btn px-3 py-1.5 text-sm" onClick={send} disabled={message.trim().length < 3}>
          Отправить
        </button>
        <button className="btn-ghost px-3 py-1.5 text-sm" onClick={() => setOpen(false)}>
          Отмена
        </button>
      </div>
      {error && (
        <p className="text-xs" style={{ color: "var(--accent-2)" }}>
          {error}
        </p>
      )}
    </div>
  );
}
