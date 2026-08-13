"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Tournament } from "../../tournaments/types";

type RuleDraft = {
  event: string;
  points: number;
  daily_cap: number | null;
  task_numbers: string; // строкой: «1, 2, 7» — так удобнее вводить
  min_difficulty: number | null;
  max_difficulty: number | null;
  exclude_hints: boolean;
};

type PrizeDraft = {
  place_from: number;
  place_to: number;
  coins: number;
  item_code: string;
};

const EVENTS = [
  { value: "task_solved", label: "Решена задача (первое верное)" },
  { value: "daily_solved", label: "Решена задача дня" },
  { value: "quiz_finished", label: "Пройден квиз" },
  { value: "quiz_perfect", label: "Квиз без ошибок" },
  { value: "duel_win", label: "Победа в онлайн-дуэли" },
  { value: "duel_played", label: "Сыгран онлайн-матч" },
  { value: "mock_finished", label: "Сдан пробник" },
];

/** Фильтры по задачам имеют смысл только там, где событие — про задачу. */
const TASK_EVENTS = ["task_solved", "daily_solved"];

const COLORS = ["#0088b0", "#d6006c", "#7c3aed", "#1f9d55", "#c98a00", "#1b1f3b"];

function emptyRule(): RuleDraft {
  return {
    event: "task_solved",
    points: 1,
    daily_cap: 30,
    task_numbers: "",
    min_difficulty: null,
    max_difficulty: null,
    exclude_hints: false,
  };
}

/** По умолчанию — неделя с ближайшего понедельника: самый частый случай. */
function defaultPeriod(): [string, string] {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  return [toLocal(start), toLocal(end)];
}

function toLocal(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export default function TournamentForm({
  id,
  onClose,
}: {
  id: number | null;
  onClose: () => void;
}) {
  const [period] = useState(defaultPeriod);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState(COLORS[0]);
  const [startsAt, setStartsAt] = useState(period[0]);
  const [endsAt, setEndsAt] = useState(period[1]);
  const [minRating, setMinRating] = useState<number | null>(null);
  const [rules, setRules] = useState<RuleDraft[]>([emptyRule()]);
  const [prizes, setPrizes] = useState<PrizeDraft[]>([
    { place_from: 1, place_to: 1, coins: 500, item_code: "" },
    { place_from: 2, place_to: 3, coins: 200, item_code: "" },
  ]);

  const [preview, setPreview] = useState<Tournament | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (id === null) return;
    api<Tournament>(`/api/admin/tournaments/${id}`)
      .then((data) => {
        setTitle(data.title);
        setDescription(data.description ?? "");
        setColor(data.color);
        setStartsAt(toLocal(new Date(data.starts_at)));
        setEndsAt(toLocal(new Date(data.ends_at)));
        setMinRating(data.min_rating);
        setRules(
          data.rules.map((rule) => ({
            event: rule.event,
            points: rule.points,
            daily_cap: rule.daily_cap,
            task_numbers: rule.task_numbers.join(", "),
            min_difficulty: null,
            max_difficulty: null,
            exclude_hints: rule.exclude_hints,
          })),
        );
        setPrizes(
          data.prizes.map((prize) => ({
            place_from: prize.place_from,
            place_to: prize.place_to,
            coins: prize.coins,
            item_code: prize.item_code ?? "",
          })),
        );
        setPreview(data);
      })
      .catch((e: Error) => setError(e.message));
  }, [id]);

  function payload() {
    return {
      title,
      description: description || null,
      color,
      starts_at: new Date(startsAt).toISOString(),
      ends_at: new Date(endsAt).toISOString(),
      min_rating: minRating,
      rules: rules.map((rule) => ({
        event: rule.event,
        points: rule.points,
        daily_cap: rule.daily_cap,
        task_numbers: TASK_EVENTS.includes(rule.event)
          ? rule.task_numbers
              .split(/[\s,]+/)
              .filter(Boolean)
              .map(Number)
              .filter((n) => Number.isFinite(n))
          : [],
        min_difficulty: TASK_EVENTS.includes(rule.event) ? rule.min_difficulty : null,
        max_difficulty: TASK_EVENTS.includes(rule.event) ? rule.max_difficulty : null,
        exclude_hints: TASK_EVENTS.includes(rule.event) ? rule.exclude_hints : false,
      })),
      prizes: prizes.map((prize) => ({
        ...prize,
        item_code: prize.item_code || null,
      })),
    };
  }

  async function save() {
    setBusy(true);
    setError("");
    try {
      const saved = await api<Tournament>(
        id === null ? "/api/admin/tournaments" : `/api/admin/tournaments/${id}`,
        { method: id === null ? "POST" : "PUT", body: JSON.stringify(payload()) },
      );
      setPreview(saved);
      if (id === null) onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function patchRule(index: number, patch: Partial<RuleDraft>) {
    setRules((list) =>
      list.map((rule, i) => (i === index ? { ...rule, ...patch } : rule)),
    );
  }

  function patchPrize(index: number, patch: Partial<PrizeDraft>) {
    setPrizes((list) =>
      list.map((prize, i) => (i === index ? { ...prize, ...patch } : prize)),
    );
  }

  return (
    <div className="page">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="page-title">
          {id === null ? "Новый турнир" : "Настройка турнира"}
        </h1>
        <button className="btn-ghost" onClick={onClose}>
          <ArrowLeft size={15} /> К списку
        </button>
      </header>

      {error && (
        <p className="text-sm" style={{ color: "var(--accent-2)" }}>
          {error}
        </p>
      )}

      <section className="card space-y-5" style={{ padding: "26px 28px" }}>
        <h2 className="section-title">Общее</h2>

        <label className="block">
          <span className="eyebrow">Название</span>
          <input
            className="input mt-1.5 w-full"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Марафон планиметрии"
          />
        </label>

        <label className="block">
          <span className="eyebrow">Описание</span>
          <textarea
            className="input mt-1.5 min-h-20 w-full"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Зачем и для кого — это видят ученики"
          />
        </label>

        <div className="grid gap-5 sm:grid-cols-3">
          <label className="block">
            <span className="eyebrow">Начало</span>
            <input
              className="input mt-1.5 w-full"
              type="datetime-local"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="eyebrow">Конец</span>
            <input
              className="input mt-1.5 w-full"
              type="datetime-local"
              value={endsAt}
              onChange={(e) => setEndsAt(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="eyebrow">Рейтинг от (необязательно)</span>
            <input
              className="input mt-1.5 w-full"
              type="number"
              value={minRating ?? ""}
              onChange={(e) =>
                setMinRating(e.target.value ? Number(e.target.value) : null)
              }
              placeholder="все"
            />
          </label>
        </div>

        <div>
          <span className="eyebrow">Цвет баннера</span>
          <div className="mt-1.5 flex gap-2">
            {COLORS.map((value) => (
              <button
                key={value}
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
      </section>

      <section className="card space-y-4" style={{ padding: "26px 28px" }}>
        <div className="section-head">
          <h2 className="section-title">Правила начисления</h2>
          <span className="section-note">
            потолок в день защищает от фарма одного действия
          </span>
        </div>

        {rules.map((rule, index) => (
          <div
            key={index}
            className="space-y-3 rounded-xl p-4"
            style={{ background: "var(--surface)" }}
          >
            <div className="flex flex-wrap items-end gap-3">
              <label className="min-w-[240px] flex-1">
                <span className="eyebrow">Событие</span>
                <select
                  className="input mt-1.5 w-full"
                  value={rule.event}
                  onChange={(e) => patchRule(index, { event: e.target.value })}
                >
                  {EVENTS.map((event) => (
                    <option key={event.value} value={event.value}>
                      {event.label}
                    </option>
                  ))}
                </select>
              </label>

              <label style={{ width: 110 }}>
                <span className="eyebrow">Очков</span>
                <input
                  className="input mt-1.5 w-full"
                  type="number"
                  min={0}
                  value={rule.points}
                  onChange={(e) =>
                    patchRule(index, { points: Number(e.target.value) })
                  }
                />
              </label>

              <label style={{ width: 140 }}>
                <span className="eyebrow">Кап в день</span>
                <input
                  className="input mt-1.5 w-full"
                  type="number"
                  min={1}
                  value={rule.daily_cap ?? ""}
                  placeholder="без кап."
                  onChange={(e) =>
                    patchRule(index, {
                      daily_cap: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                />
              </label>

              <button
                className="muted p-2"
                title="Убрать правило"
                onClick={() =>
                  setRules((list) => list.filter((_, i) => i !== index))
                }
              >
                <Trash2 size={15} />
              </button>
            </div>

            {TASK_EVENTS.includes(rule.event) && (
              <div className="flex flex-wrap items-end gap-3">
                <label className="min-w-[200px] flex-1">
                  <span className="eyebrow">Только номера (через запятую)</span>
                  <input
                    className="input mt-1.5 w-full"
                    value={rule.task_numbers}
                    onChange={(e) =>
                      patchRule(index, { task_numbers: e.target.value })
                    }
                    placeholder="все"
                  />
                </label>

                <label style={{ width: 120 }}>
                  <span className="eyebrow">Сложность от</span>
                  <input
                    className="input mt-1.5 w-full"
                    type="number"
                    min={1}
                    max={5}
                    value={rule.min_difficulty ?? ""}
                    onChange={(e) =>
                      patchRule(index, {
                        min_difficulty: e.target.value
                          ? Number(e.target.value)
                          : null,
                      })
                    }
                  />
                </label>

                <label style={{ width: 120 }}>
                  <span className="eyebrow">до</span>
                  <input
                    className="input mt-1.5 w-full"
                    type="number"
                    min={1}
                    max={5}
                    value={rule.max_difficulty ?? ""}
                    onChange={(e) =>
                      patchRule(index, {
                        max_difficulty: e.target.value
                          ? Number(e.target.value)
                          : null,
                      })
                    }
                  />
                </label>

                <label className="flex items-center gap-2 pb-2.5 text-sm">
                  <input
                    type="checkbox"
                    checked={rule.exclude_hints}
                    onChange={(e) =>
                      patchRule(index, { exclude_hints: e.target.checked })
                    }
                  />
                  не считать с подсказкой
                </label>
              </div>
            )}
          </div>
        ))}

        <button
          className="btn-ghost text-sm"
          onClick={() => setRules((list) => [...list, emptyRule()])}
        >
          <Plus size={15} /> Ещё правило
        </button>
      </section>

      <section className="card space-y-4" style={{ padding: "26px 28px" }}>
        <div className="section-head">
          <h2 className="section-title">Награды</h2>
          <span className="section-note">
            код предмета — из магазина, например frame_gold
          </span>
        </div>

        {prizes.map((prize, index) => (
          <div key={index} className="flex flex-wrap items-end gap-3">
            <label style={{ width: 110 }}>
              <span className="eyebrow">Место с</span>
              <input
                className="input mt-1.5 w-full"
                type="number"
                min={1}
                value={prize.place_from}
                onChange={(e) =>
                  patchPrize(index, { place_from: Number(e.target.value) })
                }
              />
            </label>
            <label style={{ width: 110 }}>
              <span className="eyebrow">по</span>
              <input
                className="input mt-1.5 w-full"
                type="number"
                min={1}
                value={prize.place_to}
                onChange={(e) =>
                  patchPrize(index, { place_to: Number(e.target.value) })
                }
              />
            </label>
            <label style={{ width: 140 }}>
              <span className="eyebrow">Монет</span>
              <input
                className="input mt-1.5 w-full"
                type="number"
                min={0}
                value={prize.coins}
                onChange={(e) =>
                  patchPrize(index, { coins: Number(e.target.value) })
                }
              />
            </label>
            <label className="min-w-[180px] flex-1">
              <span className="eyebrow">Код предмета</span>
              <input
                className="input mt-1.5 w-full"
                value={prize.item_code}
                onChange={(e) => patchPrize(index, { item_code: e.target.value })}
                placeholder="без предмета"
              />
            </label>
            <button
              className="muted p-2"
              title="Убрать награду"
              onClick={() =>
                setPrizes((list) => list.filter((_, i) => i !== index))
              }
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}

        <button
          className="btn-ghost text-sm"
          onClick={() =>
            setPrizes((list) => [
              ...list,
              { place_from: 1, place_to: 1, coins: 0, item_code: "" },
            ])
          }
        >
          <Plus size={15} /> Ещё награда
        </button>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <button className="btn" onClick={save} disabled={busy || !title}>
          {busy ? "Сохраняем…" : id === null ? "Создать черновик" : "Сохранить"}
        </button>
        <span className="muted text-sm">
          Турнир создаётся черновиком — опубликовать можно из списка.
        </span>
      </div>

      {preview && (
        <section className="card" style={{ padding: "26px 28px" }}>
          <div className="section-head">
            <h2 className="section-title">Как выглядит таблица сейчас</h2>
            <span className="section-note">
              по текущим правилам и уже накопленным данным
            </span>
          </div>

          {preview.rows.length === 0 ? (
            <p className="muted mt-3 text-sm">
              По этим правилам очков пока ни у кого нет. Если это неожиданно —
              проверь период: события считаются только внутри него.
            </p>
          ) : (
            <ul className="mt-3 space-y-1.5 text-sm">
              {preview.rows.slice(0, 10).map((row) => (
                <li key={row.user_id} className="flex items-center gap-3">
                  <span className="muted w-6 text-right">{row.place}</span>
                  <span className="min-w-0 flex-1 truncate">
                    {row.display_name}
                  </span>
                  {row.prize_coins > 0 && (
                    <span className="muted text-xs">приз {row.prize_coins}</span>
                  )}
                  <b>{row.points}</b>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
