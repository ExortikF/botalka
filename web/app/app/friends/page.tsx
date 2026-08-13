"use client";

import Link from "next/link";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Check, Copy, Flame, Swords, UserPlus, X } from "lucide-react";
import { api, createDuel } from "@/lib/api";
import { plural } from "@/lib/exam";
import { initials } from "@/lib/format";
import { nickStyle } from "@/lib/cosmetics";
import UserAvatar from "../Avatar";

type Friend = {
  id: number;
  display_name: string;
  streak_days: number;
  solved: number;
  friendship_id: number;
  cosmetics: {
    nick_color: string | null;
    prefix: string | null;
    frame: string | null;
    avatar: string | null;
  };
};

type Request = {
  friendship_id: number;
  user_id: number;
  display_name: string;
  direction: "incoming" | "outgoing";
};

type FriendsPage = { my_code: string; friends: Friend[]; requests: Request[] };

export default function FriendsPage() {
  const router = useRouter();
  const [data, setData] = useState<FriendsPage | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<FriendsPage>("/api/friends")
      .then(setData)
      .catch(() => setData(null));
  }, []);

  useEffect(load, [load]);

  async function addFriend() {
    if (!code.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api("/api/friends/request", {
        method: "POST",
        body: JSON.stringify({ code: code.trim() }),
      });
      setCode("");
      load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function accept(id: number) {
    await api(`/api/friends/${id}/accept`, { method: "POST" });
    load();
  }

  async function remove(id: number) {
    await api(`/api/friends/${id}`, { method: "DELETE" });
    load();
  }

  async function challenge(friend: Friend) {
    const duel = await createDuel([], 7, friend.id);
    router.push(`/app/duels/${duel.code}`);
  }

  async function copyCode() {
    if (!data) return;
    await navigator.clipboard.writeText(data.my_code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!data) return <p className="muted">Загрузка…</p>;

  const incoming = data.requests.filter((r) => r.direction === "incoming");
  const outgoing = data.requests.filter((r) => r.direction === "outgoing");

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl">Друзья</h1>
        <p className="muted mt-2">
          Добавляй по коду и вызывай на дуэль в один клик. Поиска по всем
          пользователям нет — только по коду, который человек сам тебе дал.
        </p>
      </header>

      <section className="card grid gap-6 p-7 sm:grid-cols-2">
        <div>
          <p className="eyebrow mb-2">Твой код</p>
          <div className="flex items-center gap-3">
            <span className="h text-3xl tracking-widest">{data.my_code}</span>
            <button className="btn-ghost px-3 py-2" onClick={copyCode}>
              {copied ? <Check size={15} /> : <Copy size={15} />}
            </button>
          </div>
          <p className="muted mt-2 text-sm">
            Отправь его тому, кого хочешь добавить.
          </p>
        </div>

        <div>
          <p className="eyebrow mb-2">Добавить друга</p>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              addFriend();
            }}
          >
            <input
              className="input"
              placeholder="Код друга"
              value={code}
              maxLength={8}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
            />
            <button
              className="btn"
              type="submit"
              disabled={busy || !code.trim()}
            >
              <UserPlus size={16} />
            </button>
          </form>
          {error && (
            <p className="mt-2 text-sm" style={{ color: "var(--accent-2)" }}>
              {error}
            </p>
          )}
        </div>
      </section>

      {incoming.length > 0 && (
        <section className="space-y-3">
          <h2 className="eyebrow">Хотят добавиться</h2>
          {incoming.map((request) => (
            <article
              key={request.friendship_id}
              className="card flex items-center gap-4 p-4"
              style={{
                background: "var(--accent-2-100)",
                borderColor: "var(--accent-2-200)",
              }}
            >
              <Avatar name={request.display_name} />
              <span className="min-w-0 flex-1 font-medium">
                {request.display_name}
              </span>
              <button
                className="btn text-sm"
                onClick={() => accept(request.friendship_id)}
              >
                Принять
              </button>
              <button
                className="muted p-2"
                title="Отклонить"
                onClick={() => remove(request.friendship_id)}
              >
                <X size={16} />
              </button>
            </article>
          ))}
        </section>
      )}

      <section className="space-y-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl">Мои друзья</h2>
          <span className="muted text-sm">
            {data.friends.length}{" "}
            {plural(data.friends.length, "друг", "друга", "друзей")}
          </span>
        </div>

        {data.friends.length === 0 ? (
          <p className="muted text-sm">
            Пока никого. Обменяйтесь кодами — и сможете вызывать друг друга на
            дуэль.
          </p>
        ) : (
          <ul className="space-y-2">
            {data.friends.map((friend) => (
              <li key={friend.id}>
                <article className="card flex items-center gap-4 p-4">
                  <UserAvatar
                    name={friend.display_name}
                    avatar={friend.cosmetics?.avatar}
                    frame={friend.cosmetics?.frame}
                    size={40}
                    rounded="rounded-full"
                  />
                  <span className="min-w-0 flex-1">
                    <Link
                      className="block font-medium hover:underline"
                      href={`/app/u/${friend.id}`}
                      style={nickStyle(friend.cosmetics?.nick_color).style}
                    >
                      <span
                        className={
                          nickStyle(friend.cosmetics?.nick_color).className
                        }
                      >
                        {friend.cosmetics?.prefix &&
                          `${friend.cosmetics.prefix} `}
                        {friend.display_name}
                      </span>
                    </Link>
                    <span className="muted flex items-center gap-2 text-sm">
                      решено {friend.solved}
                      {friend.streak_days > 0 && (
                        <>
                          ·
                          <Flame
                            size={12}
                            style={{ color: "var(--accent-2)" }}
                          />
                          {friend.streak_days}
                        </>
                      )}
                    </span>
                  </span>
                  <button
                    className="btn btn-accent2 text-sm"
                    onClick={() => challenge(friend)}
                  >
                    <Swords size={15} /> Вызвать
                  </button>
                  <button
                    className="muted p-2"
                    title="Удалить из друзей"
                    onClick={() => remove(friend.friendship_id)}
                  >
                    <X size={16} />
                  </button>
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>

      {outgoing.length > 0 && (
        <section className="space-y-2">
          <h2 className="eyebrow">Отправленные заявки</h2>
          {outgoing.map((request) => (
            <article
              key={request.friendship_id}
              className="card flex items-center gap-4 p-4"
            >
              <Avatar name={request.display_name} />
              <span className="min-w-0 flex-1">{request.display_name}</span>
              <span className="muted text-sm">ждём ответа</span>
              <button
                className="muted p-2"
                title="Отменить"
                onClick={() => remove(request.friendship_id)}
              >
                <X size={16} />
              </button>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

function Avatar({ name }: { name: string }) {
  return (
    <span
      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
      style={{ background: "var(--accent-100)", color: "var(--accent-700)" }}
    >
      {initials(name)}
    </span>
  );
}
