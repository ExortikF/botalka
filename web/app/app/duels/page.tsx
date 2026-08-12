"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Swords } from "lucide-react";
import { createDuel, getMyDuels, type DuelListItem } from "@/lib/api";
import { plural } from "@/lib/exam";

const LENGTHS = [5, 7, 11];

const OUTCOME: Record<string, { label: string; color: string }> = {
  win: { label: "победа", color: "var(--accent)" },
  loss: { label: "поражение", color: "var(--accent-2)" },
  draw: { label: "ничья", color: "var(--n-600)" },
};

export default function DuelsPage() {
  const router = useRouter();
  const [duels, setDuels] = useState<DuelListItem[]>([]);
  const [length, setLength] = useState(7);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getMyDuels().then(setDuels).catch(() => setDuels([]));
  }, []);

  async function create() {
    setCreating(true);
    setError("");
    try {
      const duel = await createDuel([], length);
      router.push(`/app/duels/${duel.code}`);
    } catch (e) {
      setError((e as Error).message);
      setCreating(false);
    }
  }

  const finished = duels.filter((d) => d.outcome);
  const wins = finished.filter((d) => d.outcome === "win").length;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl">Дуэли</h1>
        <p className="muted mt-2">
          Вы оба решаете один и тот же набор задач. Побеждает тот, кто ответил верно
          больше раз; при равном счёте — кто справился быстрее.
        </p>
      </header>

      <section
        className="card flex flex-wrap items-center justify-between gap-4 p-7"
        style={{ background: "var(--accent-100)", borderColor: "var(--accent-200)" }}
      >
        <div>
          <h2 className="text-xl">Онлайн-матч</h2>
          <p className="muted mt-1 text-sm">
            Живая дуэль с подбором соперника: 7 раундов, вопрос обоим одновременно.
            Только этот режим меняет рейтинг.
          </p>
        </div>
        <Link className="btn shrink-0" href="/app/duels/online">
          Найти соперника
        </Link>
      </section>

      <section className="card space-y-4 p-7">
        <div className="flex items-center gap-3">
          <Swords size={20} style={{ color: "var(--accent-2)" }} />
          <h2 className="text-xl">Вызвать друга</h2>
        </div>
        <p className="muted text-sm leading-relaxed">
          Создай вызов, пройди свою половину и отправь ссылку. Друг решит те же задачи
          когда ему удобно — быть онлайн одновременно не нужно.
        </p>

        <div className="flex flex-wrap items-center gap-2">
          <span className="muted text-sm">Раундов:</span>
          {LENGTHS.map((n) => (
            <button
              key={n}
              onClick={() => setLength(n)}
              className={`pill ${length === n ? "pill-active" : "pill-idle"}`}
              style={{ border: "1px solid var(--divider)" }}
            >
              {n}
            </button>
          ))}
        </div>

        <button className="btn btn-accent2" onClick={create} disabled={creating}>
          {creating ? "Создаём…" : "Создать вызов"}
        </button>
        {error && <p className="text-sm" style={{ color: "var(--accent-2)" }}>{error}</p>}
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl">Мои дуэли</h2>
          {finished.length > 0 && (
            <span className="muted text-sm">
              {wins} {plural(wins, "победа", "победы", "побед")} из {finished.length}
            </span>
          )}
        </div>

        {duels.length === 0 ? (
          <p className="muted text-sm">Дуэлей пока нет — создай первый вызов.</p>
        ) : (
          <ul className="space-y-2">
            {duels.map((duel) => {
              const outcome = duel.outcome ? OUTCOME[duel.outcome] : null;
              return (
                <li key={duel.code}>
                  <Link
                    href={`/app/duels/${duel.code}`}
                    className="card flex items-center justify-between gap-4 p-4 transition hover:shadow-[var(--shadow-sm)]"
                  >
                    <span className="min-w-0">
                      <span className="block font-medium">
                        {duel.opponent_name ?? "Ждём соперника"}
                      </span>
                      <span className="muted text-sm">
                        {duel.role === "challenger" ? "ты вызвал" : "тебя вызвали"} ·{" "}
                        {new Date(duel.created_at).toLocaleDateString("ru", {
                          day: "numeric",
                          month: "long",
                        })}
                      </span>
                    </span>

                    <span className="shrink-0 text-right">
                      {duel.your_score !== null && duel.their_score !== null ? (
                        <span className="h text-lg">
                          {duel.your_score} : {duel.their_score}
                        </span>
                      ) : (
                        <span className="muted text-sm">не завершена</span>
                      )}
                      {outcome && (
                        <span className="block text-xs" style={{ color: outcome.color }}>
                          {outcome.label}
                        </span>
                      )}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
