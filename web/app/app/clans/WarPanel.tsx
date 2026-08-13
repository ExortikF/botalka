"use client";

import { useState } from "react";
import { Check, Coins, Swords, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Clan, ClanRow, War } from "./types";
import { MIN_FOR_BOARD } from "./types";

const DEFAULT_STAKE = 500;

/**
 * Казна, входящие вызовы и кнопка «вызвать» напротив других кланов.
 * Сам бой рисует War.tsx — здесь всё вокруг него.
 */
export default function WarPanel({
  clan,
  wars,
  rows,
  onChange,
}: {
  clan: Clan;
  wars: War[];
  rows: ClanRow[];
  onChange: () => void;
}) {
  const [stake, setStake] = useState(DEFAULT_STAKE);
  const [amount, setAmount] = useState(100);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const canManage = clan.your_role === "leader" || clan.your_role === "officer";
  const pending = wars.filter((war) => war.state === "pending");
  const active = wars.find((war) => war.state === "active");
  const history = wars.filter((war) => war.state === "finished").slice(0, 3);
  const rivals = rows.filter(
    (row) => row.id !== clan.id && row.members_count >= MIN_FOR_BOARD,
  );

  async function call(path: string, body?: unknown) {
    setBusy(true);
    setError("");
    try {
      await api(path, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      });
      onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card space-y-5" style={{ padding: "26px 28px" }}>
      <div className="section-head">
        <h2 className="section-title flex items-center gap-2">
          <Swords size={18} style={{ color: "var(--accent-2)" }} /> Войны кланов
        </h2>
        <span className="section-note">
          5 часов, 20 общих задач, ставка с обеих сторон
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <span className="flex items-center gap-2">
          <Coins size={16} style={{ color: "#c98a00" }} />
          <span className="h text-xl">{clan.coins}</span>
          <span className="muted text-sm">в казне</span>
        </span>

        <span className="flex items-center gap-2">
          <input
            className="input"
            style={{ width: 110 }}
            type="number"
            min={1}
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
          />
          <button
            className="btn-ghost text-sm"
            disabled={busy}
            onClick={() => call("/api/clans/wars/deposit", { amount })}
          >
            Скинуться
          </button>
        </span>

        <span className="muted text-sm">
          Ставки платятся из казны, личные монеты не трогаются.
        </span>
      </div>

      {error && (
        <p className="text-sm" style={{ color: "var(--accent-2)" }}>
          {error}
        </p>
      )}

      {pending.map((war) => (
        <div
          key={war.id}
          className="flex flex-wrap items-center gap-3 rounded-xl p-4"
          style={{ background: "var(--accent-2-100)" }}
        >
          <Swords size={16} style={{ color: "var(--accent-2)" }} />
          <span className="min-w-0 flex-1">
            {war.you_challenged ? (
              <>
                Вызов отправлен клану <b>{war.them.name}</b> — ждём ответа.
              </>
            ) : (
              <>
                <b>{war.them.name}</b> вызывает на войну.
              </>
            )}
            <span className="muted"> Ставка {war.stake} с каждого.</span>
          </span>

          {canManage && !war.you_challenged && (
            <button
              className="btn text-sm"
              disabled={busy}
              onClick={() => call(`/api/clans/wars/${war.id}/accept`)}
            >
              <Check size={14} /> Принять
            </button>
          )}
          {canManage && (
            <button
              className="btn-ghost text-sm"
              disabled={busy}
              onClick={() => call(`/api/clans/wars/${war.id}/decline`)}
            >
              <X size={14} /> {war.you_challenged ? "Отозвать" : "Отклонить"}
            </button>
          )}
        </div>
      ))}

      {!active && pending.length === 0 && canManage && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <label style={{ width: 150 }}>
              <span className="eyebrow">Ставка</span>
              <input
                className="input mt-1.5 w-full"
                type="number"
                min={50}
                step={50}
                value={stake}
                onChange={(e) => setStake(Number(e.target.value))}
              />
            </label>
            <span className="muted pb-2.5 text-sm">
              Победитель забирает {stake * 2}, при ничьей ставки вернутся.
            </span>
          </div>

          {rivals.length === 0 ? (
            <p className="muted text-sm">
              Пока некого вызывать: нужен другой клан хотя бы из {MIN_FOR_BOARD}{" "}
              человек.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {rivals.map((row) => (
                <button
                  key={row.id}
                  className="btn-ghost text-sm"
                  disabled={busy || clan.coins < stake}
                  title={
                    clan.coins < stake ? "в казне не хватает на ставку" : undefined
                  }
                  onClick={() =>
                    call("/api/clans/wars", { clan_id: row.id, stake })
                  }
                >
                  <Swords size={14} /> {row.tag} · {row.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {!canManage && !active && (
        <p className="muted text-sm">
          Вызов на войну бросает глава или офицер. Скинуться в казну может любой.
        </p>
      )}

      {history.length > 0 && (
        <div className="space-y-1.5">
          <p className="eyebrow">Прошлые войны</p>
          {history.map((war) => (
            <p key={war.id} className="text-sm">
              <b
                style={{
                  color:
                    war.winner === "мы"
                      ? "var(--accent)"
                      : war.winner === "они"
                        ? "var(--accent-2)"
                        : "var(--n-600)",
                }}
              >
                {war.winner === "мы"
                  ? "Победа"
                  : war.winner === "они"
                    ? "Поражение"
                    : "Ничья"}
              </b>{" "}
              против {war.them.name} — {war.us.score}:{war.them.score}
              <span className="muted">
                {war.winner === "мы"
                  ? `, +${war.prize} в казну`
                  : war.winner === "они"
                    ? `, −${war.stake}`
                    : ", ставки вернулись"}
              </span>
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
