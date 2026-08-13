"use client";

import { useEffect, useState } from "react";
import { Check, Coins, Lock } from "lucide-react";
import { api, getMe, type User } from "@/lib/api";
import {
  auroraClass,
  cardBackground,
  frameStyle,
  nickStyle,
  plateStyle,
} from "@/lib/cosmetics";
import Avatar from "../Avatar";

type Item = {
  code: string;
  kind: string;
  kind_title: string;
  title: string;
  value: string;
  price: number;
  rarity: "common" | "rare" | "epic" | "legendary" | "mythic";
  owned: boolean;
  equipped: boolean;
};

type Shop = { coins: number; items: Item[] };

const RARITY: Record<Item["rarity"], { label: string; color: string }> = {
  common: { label: "обычная", color: "#5b6570" },
  rare: { label: "редкая", color: "#0088b0" },
  epic: { label: "эпическая", color: "#7c3aed" },
  legendary: { label: "легендарная", color: "#b8860b" },
  mythic: { label: "только для админов", color: "#00a37a" },
};

const KIND_ORDER = [
  "avatar",
  "frame",
  "nick_color",
  "prefix",
  "name_plate",
  "card_bg",
];

export default function ShopPage() {
  const [shop, setShop] = useState<Shop | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [me, setMe] = useState<User | null>(null);

  useEffect(() => {
    api<Shop>("/api/shop")
      .then(setShop)
      .catch(() => setShop(null));
    getMe()
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  async function adminAction(path: string, body?: unknown) {
    await api(`/api/admin/self/${path}`, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
    setShop(await api<Shop>("/api/shop"));
  }

  async function act(item: Item, action: "buy" | "equip") {
    setBusy(item.code);
    setError("");
    try {
      setShop(
        await api<Shop>(`/api/shop/${item.code}/${action}`, { method: "POST" }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  if (!shop) return <p className="muted">Загрузка…</p>;

  const groups = KIND_ORDER.map((kind) => ({
    kind,
    title: shop.items.find((i) => i.kind === kind)?.kind_title ?? kind,
    items: shop.items.filter((i) => i.kind === kind),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl">Магазин</h1>
        <span
          className="flex items-center gap-2 rounded-full px-4 py-2 text-lg font-semibold"
          style={{ background: "#fdf3dd", color: "#c98a00" }}
        >
          <Coins size={18} /> {shop.coins}
        </span>
      </header>

      <p className="muted -mt-4 text-sm">
        Только внешний вид. На задачи, подсказки и рейтинг ничего из этого не
        влияет.
      </p>

      {me?.is_admin && (
        <section
          className="card flex flex-wrap items-center gap-3 p-4"
          style={{ borderColor: "var(--accent-2-200)" }}
        >
          <span className="eyebrow" style={{ color: "var(--accent-2)" }}>
            Только для админа
          </span>
          <button
            className="btn-ghost text-sm"
            onClick={() => adminAction("coins", { amount: 1000 })}
          >
            +1000 монет
          </button>
          <button
            className="btn-ghost text-sm"
            onClick={() => adminAction("coins", { amount: 10000 })}
          >
            +10 000 монет
          </button>
          <button
            className="btn-ghost text-sm"
            onClick={() => {
              if (confirm("Сбросить свои покупки?"))
                adminAction("reset-purchases");
            }}
          >
            Сбросить покупки
          </button>
        </section>
      )}

      {error && (
        <p
          className="rounded-xl p-3 text-sm"
          style={{
            background: "var(--accent-2-100)",
            color: "var(--accent-2)",
          }}
        >
          {error}
        </p>
      )}

      {groups.map((group) => (
        <section key={group.kind} className="space-y-3">
          <h2 className="eyebrow">{group.title}</h2>
          <ul className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {group.items.map((item) => {
              const rarity = RARITY[item.rarity];
              return (
                <li key={item.code}>
                  <article
                    className="card flex h-full flex-col items-center gap-3 p-5 text-center"
                    style={{
                      borderColor: item.equipped ? "var(--accent)" : undefined,
                    }}
                  >
                    <Preview item={item} />

                    <div className="flex-1">
                      <p className="font-medium">{item.title}</p>
                      <p className="text-xs" style={{ color: rarity.color }}>
                        {rarity.label}
                      </p>
                    </div>

                    {item.owned ? (
                      <button
                        className={
                          item.equipped
                            ? "btn-ghost w-full text-sm"
                            : "btn w-full text-sm"
                        }
                        onClick={() => act(item, "equip")}
                        disabled={busy === item.code}
                      >
                        {item.equipped ? (
                          <>
                            <Check size={14} /> Надето
                          </>
                        ) : (
                          "Надеть"
                        )}
                      </button>
                    ) : (
                      <button
                        className="btn w-full text-sm"
                        onClick={() => act(item, "buy")}
                        disabled={busy === item.code || shop.coins < item.price}
                      >
                        {shop.coins < item.price && <Lock size={13} />}
                        {item.price === 0 ? "Забрать" : `${item.price} монет`}
                      </button>
                    )}
                  </article>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}

/** Как вещь выглядит вживую — теми же стилями, что и в профиле. */
function Preview({ item }: { item: Item }) {
  if (item.kind === "avatar")
    return <Avatar name="Тестовый Ученик" avatar={item.value} size={64} />;

  if (item.kind === "name_plate") {
    const plate = plateStyle(item.value);
    return (
      <span
        className={`flex h-16 w-full items-center gap-2 rounded-xl px-3 text-sm ${plate.className}`}
        style={{
          background: "var(--surface)",
          border:
            item.value === "none" ? "2px dashed var(--divider)" : undefined,
          ...plate.style,
        }}
      >
        <Avatar name="Тестовый Ученик" size={32} rounded="rounded-full" />
        <span className="h">Боталка</span>
      </span>
    );
  }

  if (item.kind === "frame") {
    const frame = frameStyle(item.value);
    return (
      <span
        className={`flex h-16 w-16 items-center justify-center rounded-full ${frame.className}`}
        style={{
          background: "var(--surface)",
          ...(item.value === "none"
            ? { border: "2px dashed var(--divider)" }
            : frame.style),
        }}
      >
        <span className="h text-sm">ТУ</span>
      </span>
    );
  }

  if (item.kind === "nick_color") {
    const nick = nickStyle(item.value);
    return (
      <span className={`h text-xl ${nick.className}`} style={nick.style}>
        Боталка
      </span>
    );
  }

  if (item.kind === "card_bg") {
    const bg = cardBackground(item.value);
    return (
      <span
        className={`flex h-16 w-full items-center justify-center rounded-xl text-sm ${auroraClass(item.value)}`}
        style={{
          ...bg.style,
          color: bg.dark ? "#fff" : "var(--text)",
          border:
            item.value === "none" ? "2px dashed var(--divider)" : undefined,
        }}
      >
        {item.value === "none" ? "обычный" : "фон"}
      </span>
    );
  }

  return <span className="text-4xl">{item.value}</span>;
}
