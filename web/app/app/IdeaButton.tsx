"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { Lightbulb, X } from "lucide-react";
import { api } from "@/lib/api";

/** «Есть идеи по улучшению сайта?» — неприметная ссылка внизу бокового меню. */
export default function IdeaButton() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function send() {
    if (message.trim().length < 5) return;
    try {
      await api("/api/ideas", {
        method: "POST",
        body: JSON.stringify({ message, page: pathname }),
      });
      setSent(true);
      setMessage("");
      setTimeout(() => {
        setOpen(false);
        setSent(false);
      }, 1800);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <button
        className="muted flex items-center gap-2 text-left text-xs hover:underline"
        onClick={() => setOpen(true)}
      >
        <Lightbulb size={13} />
        Есть идеи по улучшению сайта?
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-6"
          style={{ background: "rgba(20,23,28,.4)" }}
          onClick={() => setOpen(false)}
        >
          <div
            className="card w-full max-w-md space-y-3 p-6"
            style={{ boxShadow: "var(--shadow-lg)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-xl">Предложи идею</h3>
              <button className="muted" onClick={() => setOpen(false)} aria-label="Закрыть">
                <X size={18} />
              </button>
            </div>

            {sent ? (
              <p style={{ color: "var(--accent-700)" }}>Спасибо, идея записана.</p>
            ) : (
              <>
                <p className="muted text-sm">
                  Чего не хватает, что мешает, что стоит добавить — пиши как есть.
                </p>
                <textarea
                  className="input"
                  rows={4}
                  autoFocus
                  placeholder="Например: хочу видеть, сколько задач осталось до конца квиза"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                />
                <div className="flex gap-2">
                  <button className="btn" onClick={send} disabled={message.trim().length < 5}>
                    Отправить
                  </button>
                  <button className="btn-ghost" onClick={() => setOpen(false)}>
                    Отмена
                  </button>
                </div>
                {error && (
                  <p className="text-sm" style={{ color: "var(--accent-2)" }}>
                    {error}
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
