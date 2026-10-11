"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Link2, Minus, Plus, Swords, Trophy, Users } from "lucide-react";
import { api, createDuel, getMe, getMyDuels, type DuelListItem, type User } from "@/lib/api";
import { initials } from "@/lib/format";
import { plural } from "@/lib/exam";

type Friend = { id: number; display_name: string };

/** Чем закончилась дуэль, если счёта нет. Отказ важно показать словом: иначе
 *  вызвавший видит «не завершена» и ждёт ответа, которого не будет. */
const STATE_LABEL: Record<string, string> = {
  declined: "отклонена",
  expired: "истёк срок",
};

const OUTCOME: Record<string, { label: string; color: string }> = {
  win: { label: "победа", color: "var(--accent-700)" },
  loss: { label: "поражение", color: "var(--accent-2)" },
  draw: { label: "ничья", color: "var(--n-700)" },
};

export default function DuelsPage() {
  const router = useRouter();
  const [duels, setDuels] = useState<DuelListItem[]>([]);
  const [length, setLength] = useState(7);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [friends, setFriends] = useState<Friend[]>([]);
  const [opponent, setOpponent] = useState<number | null>(null);
  const [me, setMe] = useState<User | null>(null);

  useEffect(() => {
    getMyDuels()
      .then(setDuels)
      .catch(() => setDuels([]));
    api<{ friends: Friend[] }>("/api/friends")
      .then((data) => setFriends(data.friends))
      .catch(() => setFriends([]));
    getMe()
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  /** opponentId задан — вызов уйдёт другу в «Тебя вызвали», иначе останется ссылкой. */
  async function create(opponentId: number | null) {
    setCreating(true);
    setError("");
    try {
      const duel = await createDuel([], length, opponentId ?? undefined);
      router.push(`/app/duels/${duel.code}`);
    } catch (e) {
      setError((e as Error).message);
      setCreating(false);
    }
  }

  const finished = duels.filter((d) => d.outcome);
  const wins = finished.filter((d) => d.outcome === "win").length;

  // Серия побед считается с последней дуэли назад — как в профиле.
  let winStreak = 0;
  for (const duel of finished) {
    if (duel.outcome !== "win") break;
    winStreak += 1;
  }

  const you = initials(me?.display_name ?? "");

  return (
    <div className="page">
      <header>
        <h1 className="page-title">Дуэли</h1>
        <p className="page-subtitle">
          Вы оба решаете один и тот же набор задач. Побеждает тот, кто ответил
          верно больше раз; при равном счёте — кто справился быстрее.
        </p>
      </header>

      <section className="grid gap-3 sm:grid-cols-3">
        <div className="tile text-center">
          <p className="tile-value justify-center">{finished.length}</p>
          <p className="tile-label">матчей сыграно</p>
        </div>
        <div className="tile text-center">
          <p
            className="tile-value justify-center"
            style={{ color: "var(--accent)" }}
          >
            {finished.length > 0 ? Math.round((wins / finished.length) * 100) : 0}%
          </p>
          <p className="tile-label">процент побед</p>
        </div>
        <div className="tile text-center">
          <p
            className="tile-value justify-center"
            style={{ color: "var(--accent)" }}
          >
            {winStreak}
          </p>
          <p className="tile-label">побед подряд сейчас</p>
        </div>
      </section>

      <section
        className="relative overflow-hidden text-center text-white"
        style={{
          background: "var(--accent-700)",
          borderRadius: "var(--radius-lg)",
          padding: "38px 30px",
        }}
      >
        {/* Сетка тетрадного листа — та же, что на черновике в квизе */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              "repeating-linear-gradient(0deg,rgba(255,255,255,.06) 0 1px,transparent 1px 26px),repeating-linear-gradient(90deg,rgba(255,255,255,.06) 0 1px,transparent 1px 26px)",
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-24 h-80 w-80 rounded-full opacity-30"
          style={{ background: "var(--accent-2)" }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-24 -left-16 h-64 w-64 rounded-full opacity-20"
          style={{ background: "#ffffff" }}
        />

        <div className="relative">
          <span
            className="mx-auto flex w-fit items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold"
            style={{ background: "rgba(255,255,255,.2)" }}
          >
            <Trophy size={13} /> Рейтинговый режим
          </span>
          <div className="mt-[22px] flex items-center justify-center gap-[22px]">
            <span
              className="h flex h-14 w-14 items-center justify-center rounded-full text-[1.0625rem]"
              style={{ background: "rgba(255,255,255,.22)" }}
            >
              {you}
            </span>
            <Swords size={26} />
            <span
              className="flex h-14 w-14 items-center justify-center rounded-full text-[1.375rem]"
              style={{ background: "rgba(255,255,255,.22)" }}
            >
              ?
            </span>
          </div>
          <h2 className="h" style={{ fontSize: 33, fontWeight: 800, margin: "18px 0 0" }}>
            Онлайн-матч
          </h2>
          <p className="mx-auto mt-3 max-w-md opacity-90">
            Соперника подбираем по рейтингу. Семь раундов, вопрос приходит обоим
            одновременно, очко забирает тот, кто ответил верно и быстрее.
          </p>
          <Link
            className="mt-7 inline-block rounded-2xl bg-white px-10 py-4 text-lg font-bold shadow-lg transition hover:scale-[1.03]"
            style={{ color: "var(--accent-700)" }}
            href="/app/duels/online"
          >
            Найти соперника
          </Link>
        </div>
      </section>

      <section className="card space-y-4 p-7">
        <div className="flex flex-wrap items-center gap-3">
          <Users size={20} style={{ color: "var(--accent-2)" }} />
          <h2 className="section-title">Дуэль с другом</h2>
          <span
            className="rounded-full px-2.5 py-1 text-xs font-semibold"
            style={{ background: "var(--surface)", color: "var(--n-700)" }}
          >
            без рейтинга
          </span>
        </div>
        <p className="muted text-sm leading-relaxed">
          Друг решает те же задачи когда ему удобно — быть онлайн одновременно
          не нужно. Рейтинг такие дуэли не меняют: их слишком легко подкрутить.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <span className="muted text-sm">Раундов:</span>
          <span
            className="flex items-center gap-2 rounded-xl px-2 py-1"
            style={{ background: "var(--surface)" }}
          >
            <button
              className="flex h-7 w-7 items-center justify-center rounded-lg disabled:opacity-30"
              onClick={() => setLength((n) => Math.max(3, n - 1))}
              disabled={length <= 3}
              aria-label="Меньше раундов"
            >
              <Minus size={14} />
            </button>
            <span className="h w-8 text-center text-lg">{length}</span>
            <button
              className="flex h-7 w-7 items-center justify-center rounded-lg disabled:opacity-30"
              onClick={() => setLength((n) => Math.min(30, n + 1))}
              disabled={length >= 30}
              aria-label="Больше раундов"
            >
              <Plus size={14} />
            </button>
          </span>
          <span className="muted text-xs">от 3 до 30</span>
        </div>

        {friends.length > 0 && (
          <div className="space-y-2">
            <p className="eyebrow">Позвать напрямую</p>
            <div className="flex flex-wrap gap-2">
              {friends.map((friend) => (
                <button
                  key={friend.id}
                  className={
                    opponent === friend.id ? "btn text-sm" : "btn-ghost text-sm"
                  }
                  onClick={() =>
                    setOpponent(opponent === friend.id ? null : friend.id)
                  }
                >
                  {friend.display_name}
                </button>
              ))}
            </div>
            <p className="muted text-xs">
              Вызов появится у друга в профиле — ссылку отправлять не нужно.
            </p>
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <button
            className="btn btn-accent2"
            onClick={() => create(opponent)}
            disabled={creating}
          >
            <Swords size={16} />
            {creating
              ? "Создаём…"
              : opponent
                ? `Вызвать: ${friends.find((f) => f.id === opponent)?.display_name}`
                : "Создать вызов"}
          </button>
          {opponent === null && (
            <span className="muted flex items-center gap-1.5 self-center text-xs">
              <Link2 size={13} /> получишь ссылку, которую можно кинуть кому
              угодно
            </span>
          )}
        </div>
        {error && (
          <p className="text-sm" style={{ color: "var(--accent-2)" }}>
            {error}
          </p>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="section-title">Мои дуэли</h2>
          {finished.length > 0 && (
            <span className="muted text-sm">
              {wins} {plural(wins, "победа", "победы", "побед")} из{" "}
              {finished.length}
            </span>
          )}
        </div>

        {duels.length === 0 ? (
          <p className="muted text-sm">
            Дуэлей пока нет — создай первый вызов.
          </p>
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
                        {duel.role === "challenger"
                          ? "ты вызвал"
                          : "тебя вызвали"}{" "}
                        ·{" "}
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
                        <span className="muted text-sm">
                          {STATE_LABEL[duel.state] ?? "не завершена"}
                        </span>
                      )}
                      {outcome && (
                        <span
                          className="block text-xs"
                          style={{ color: outcome.color }}
                        >
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
