"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Plus, Shield, Users } from "lucide-react";
import { api } from "@/lib/api";
import type { Clan, ClanRow, War as WarType } from "./types";
import { MIN_FOR_BOARD, POLICY } from "./types";
import MyClan from "./MyClan";
import War from "./War";
import WarPanel from "./WarPanel";

const COLORS = ["#0088b0", "#d6006c", "#7c3aed", "#1f9d55", "#c98a00", "#1b1f3b"];

export default function ClansPage() {
  const [rows, setRows] = useState<ClanRow[] | null>(null);
  const [mine, setMine] = useState<Clan | null>(null);
  const [wars, setWars] = useState<WarType[]>([]);
  const [creating, setCreating] = useState(false);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    const params = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
    api<ClanRow[]>(`/api/clans${params}`)
      .then(setRows)
      .catch(() => setRows([]));
    api<Clan | null>("/api/clans/my")
      .then(setMine)
      .catch(() => setMine(null));
    api<WarType[]>("/api/clans/wars")
      .then(setWars)
      .catch(() => setWars([]));
  }, [query]);

  // Ищем не на каждую букву: пауза после ввода экономит запросы.
  useEffect(() => {
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
  }, [load]);

  async function join(id: number) {
    setError("");
    try {
      await api(`/api/clans/${id}/join`, { method: "POST" });
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const active = wars.find((war) => war.state === "active") ?? null;

  return (
    <div className="page">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Users size={22} style={{ color: "var(--accent-2)" }} />
          <div>
            <h1 className="page-title">Кланы</h1>
            <p className="page-subtitle">
              Команда с тегом рядом с ником. Место в таблице — по среднему числу
              решённых задач на активного участника, а не по сумме: иначе большой
              клан побеждал бы просто размером.
            </p>
          </div>
        </div>

        {!mine && !creating && (
          <button className="btn" onClick={() => setCreating(true)}>
            <Plus size={16} /> Создать клан
          </button>
        )}
      </header>

      {error && (
        <p className="text-sm" style={{ color: "var(--accent-2)" }}>
          {error}
        </p>
      )}

      {creating && (
        <CreateForm
          colors={COLORS}
          onClose={() => setCreating(false)}
          onDone={() => {
            setCreating(false);
            load();
          }}
        />
      )}

      {mine && <MyClan clan={mine} onChange={load} />}

      {mine && (
        <WarPanel clan={mine} wars={wars} rows={rows ?? []} onChange={load} />
      )}

      {active && <War war={active} onChange={load} />}

      <section className="space-y-3">
        <div className="section-head">
          <h2 className="section-title">
            {query.trim() ? "Найденные кланы" : "Таблица кланов"}
          </h2>
          <span className="section-note">
            в зачёт идут кланы от {MIN_FOR_BOARD} человек
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          <input
            className="input min-w-[220px] flex-1"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Найти клан по названию или тегу"
          />
          {query && (
            <button className="btn-ghost text-sm" onClick={() => setQuery("")}>
              Сбросить
            </button>
          )}
        </div>

        {rows === null ? (
          <p className="muted">Загрузка…</p>
        ) : rows.length === 0 ? (
          <p className="muted text-sm">
            {query.trim()
              ? "Ничего не нашлось — попробуй другое название или тег."
              : "Кланов пока нет — можно создать первый."}
          </p>
        ) : (
          <ul className="space-y-2">
            {rows.map((row) => (
              <li key={row.id}>
                <article
                  className="row-card"
                  style={{
                    background: row.is_yours ? "var(--accent-100)" : undefined,
                    borderLeft: `4px solid ${row.color}`,
                    opacity: row.members_count >= MIN_FOR_BOARD ? 1 : 0.65,
                  }}
                >
                  {!query.trim() && (
                    <span className="h w-7 shrink-0 text-center">{row.place}</span>
                  )}

                  <span
                    className="h shrink-0 rounded-lg px-2 py-1 text-xs"
                    style={{ background: `${row.color}1a`, color: row.color }}
                  >
                    {row.tag}
                  </span>

                  <Link
                    className="min-w-0 flex-1 truncate hover:underline"
                    href={`/app/clans/${row.id}`}
                  >
                    {row.name}
                  </Link>

                  <span className="muted shrink-0 text-xs">
                    {row.members_count} чел. · казна {row.coins}
                    {row.members_count < MIN_FOR_BOARD && " · вне зачёта"}
                  </span>

                  <span className="shrink-0 text-right">
                    <span className="h block">{row.average_week}</span>
                    <span className="muted block text-[11px]">
                      в среднем
                    </span>
                  </span>

                  {!mine && (
                    <button
                      className="btn-ghost shrink-0 text-sm"
                      onClick={() => join(row.id)}
                    >
                      Вступить
                    </button>
                  )}
                </article>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function CreateForm({
  colors,
  onClose,
  onDone,
}: {
  colors: string[];
  onClose: () => void;
  onDone: () => void;
}) {
  const [name, setName] = useState("");
  const [tag, setTag] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState(colors[0]);
  const [policy, setPolicy] = useState("open");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/clans", {
        method: "POST",
        body: JSON.stringify({
          name,
          tag,
          description: description || null,
          color,
          join_policy: policy,
        }),
      });
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card space-y-5 p-7" onSubmit={submit} noValidate>
      <div className="section-head">
        <h2 className="section-title">Новый клан</h2>
        <button type="button" className="muted text-sm" onClick={onClose}>
          отмена
        </button>
      </div>

      <div className="flex flex-wrap gap-4">
        <label className="min-w-[220px] flex-1">
          <span className="eyebrow">Название</span>
          <input
            className="input mt-1.5 w-full"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ботаны 11А"
          />
        </label>

        <label style={{ width: 140 }}>
          <span className="eyebrow">Тег</span>
          <input
            className="input mt-1.5 w-full uppercase"
            value={tag}
            maxLength={5}
            onChange={(e) => setTag(e.target.value.toUpperCase())}
            placeholder="БОТ"
          />
        </label>

        <label style={{ width: 200 }}>
          <span className="eyebrow">Кого пускать</span>
          <select
            className="input mt-1.5 w-full"
            value={policy}
            onChange={(e) => setPolicy(e.target.value)}
          >
            <option value="open">{POLICY.open}</option>
            <option value="request">{POLICY.request}</option>
            <option value="closed">{POLICY.closed}</option>
          </select>
        </label>
      </div>

      <label className="block">
        <span className="eyebrow">Описание</span>
        <input
          className="input mt-1.5 w-full"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Кого ищете и зачем"
        />
      </label>

      <div>
        <span className="eyebrow">Цвет тега</span>
        <div className="mt-1.5 flex gap-2">
          {colors.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setColor(value)}
              aria-label={value}
              className="h-8 w-8 rounded-lg"
              style={{
                background: value,
                outline: color === value ? "2px solid var(--text)" : "none",
                outlineOffset: 2,
              }}
            />
          ))}
        </div>
      </div>

      {error && (
        <p className="text-sm" style={{ color: "var(--accent-2)" }}>
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button className="btn" disabled={busy || !name || !tag}>
          <Shield size={16} /> {busy ? "Создаём…" : "Создать"}
        </button>
        <span className="muted text-sm">
          Тег будет виден рядом с твоим ником. Клан у человека один.
        </span>
      </div>
    </form>
  );
}
