"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Check, Plus, Trash2 } from "lucide-react";
import { api, getTaskTypes, type TaskType } from "@/lib/api";
import MathText from "../../../Math";
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

type ProblemDraft = {
  task_id: number;
  points: number;
  number: number;
  statement: string;
};

type PickRow = {
  id: number;
  task_type_number: number;
  statement: string;
  answer_value: string;
  difficulty: number;
};

const DIFFICULTY = ["", "очень лёгкая", "лёгкая", "средняя", "сложная", "очень сложная"];

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
  const [format, setFormat] = useState<"contest" | "marathon">("contest");
  const [penaltyMinutes, setPenaltyMinutes] = useState(10);
  const [problems, setProblems] = useState<ProblemDraft[]>([]);
  const [pickType, setPickType] = useState<number | null>(null);
  const [pickQuery, setPickQuery] = useState("");
  const [picks, setPicks] = useState<PickRow[]>([]);
  const [types, setTypes] = useState<TaskType[]>([]);
  const [searching, setSearching] = useState(false);

  // Своя задача: пишем прямо здесь, в банк она попадает черновиком.
  const [ownOpen, setOwnOpen] = useState(false);
  const [ownType, setOwnType] = useState<number | null>(null);
  const [ownStatement, setOwnStatement] = useState("");
  const [ownAnswer, setOwnAnswer] = useState("");
  const [ownAnswerType, setOwnAnswerType] = useState("number");
  const [ownSolution, setOwnSolution] = useState("");
  const [ownDifficulty, setOwnDifficulty] = useState(3);
  const [ownBusy, setOwnBusy] = useState(false);
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
        setFormat(data.format);
        setPenaltyMinutes(data.penalty_minutes);
        setProblems(
          data.problems.map((problem) => ({
            task_id: problem.task_id,
            points: problem.points,
            number: problem.task_type_number,
            statement: problem.statement || "(условие скрыто до старта)",
          })),
        );
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
      format,
      penalty_minutes: penaltyMinutes,
      problems: problems.map((problem) => ({
        task_id: problem.task_id,
        points: problem.points,
      })),
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

  function move(index: number, delta: number) {
    setProblems((list) => {
      const next = [...list];
      const target = index + delta;
      if (target < 0 || target >= next.length) return list;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  // Поиск идёт по всему банку: заранее знать номер задания незачем, а
  // «покажи задачи номера 7» — это про пробники, не про контест.
  useEffect(() => {
    let alive = true;
    setSearching(true);

    const timer = setTimeout(() => {
      const params = new URLSearchParams({ limit: "40", task_status: "live" });
      if (pickQuery.trim()) params.set("q", pickQuery.trim());
      if (pickType !== null) params.set("task_type_id", String(pickType));

      api<{ items: PickRow[] }>(`/api/admin/tasks?${params}`)
        .then((data) => alive && setPicks(data.items))
        .catch(() => alive && setPicks([]))
        .finally(() => alive && setSearching(false));
    }, 250);

    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [pickQuery, pickType]);

  useEffect(() => {
    getTaskTypes()
      .then(setTypes)
      .catch(() => setTypes([]));
  }, []);

  /** Баллы по возрастанию: 100, 200, 300… Ровно то, что делаешь руками. */
  function spreadPoints() {
    setProblems((list) =>
      list.map((problem, index) => ({ ...problem, points: (index + 1) * 100 })),
    );
  }

  /** Готовые окна: контест обычно ставят на вечер или на выходные. */
  function setWindow(hours: number, startHour?: number) {
    const start = new Date();
    if (startHour !== undefined) {
      start.setHours(startHour, 0, 0, 0);
      if (start < new Date()) start.setDate(start.getDate() + 1);
    }
    const end = new Date(start.getTime() + hours * 3600_000);
    setStartsAt(toLocal(start));
    setEndsAt(toLocal(end));
  }

  /**
   * Создаёт задачу и сразу ставит её в набор.
   *
   * Статус — черновик: своя задача контеста не должна до старта всплыть
   * в квизе у того, кто в нём участвует. После контеста её можно опубликовать
   * в банк из админки задач.
   */
  async function createOwn() {
    if (ownType === null || !ownStatement.trim() || !ownAnswer.trim()) {
      setError("Для своей задачи нужны тема, условие и ответ");
      return;
    }

    setOwnBusy(true);
    setError("");
    try {
      const task = await api<{ id: number; task_type_number: number; statement: string }>(
        "/api/admin/tasks",
        {
          method: "POST",
          body: JSON.stringify({
            task_type_id: ownType,
            statement: ownStatement,
            answer_type: ownAnswerType,
            answer_value: ownAnswer,
            solution: ownSolution || null,
            difficulty: ownDifficulty,
            status: "draft",
          }),
        },
      );

      setProblems((list) => [
        ...list,
        {
          task_id: task.id,
          points: (list.length + 1) * 100,
          number: task.task_type_number,
          statement: task.statement,
        },
      ]);
      setOwnStatement("");
      setOwnAnswer("");
      setOwnSolution("");
      setOwnOpen(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setOwnBusy(false);
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

  const minutes = Math.max(
    0,
    Math.round((new Date(endsAt).getTime() - new Date(startsAt).getTime()) / 60000),
  );
  const duration =
    minutes >= 1440
      ? `${Math.round(minutes / 1440)} дн.`
      : minutes >= 60
        ? `${Math.floor(minutes / 60)} ч ${minutes % 60 || ""}`.trim() + " мин"
        : `${minutes} мин`;

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
        <h2 className="section-title">Формат</h2>

        <div className="flex flex-wrap gap-2">
          <button
            className={`pill ${format === "contest" ? "pill-active" : "pill-idle"}`}
            style={{ border: "1px solid var(--divider)" }}
            onClick={() => setFormat("contest")}
          >
            Контест — набор задач
          </button>
          <button
            className={`pill ${format === "marathon" ? "pill-active" : "pill-idle"}`}
            style={{ border: "1px solid var(--divider)" }}
            onClick={() => setFormat("marathon")}
          >
            Марафон — очки за активность
          </button>
        </div>

        <p className="muted text-sm leading-relaxed">
          {format === "contest"
            ? "Задачи закрыты до старта и открываются у всех одновременно. Место — по сумме баллов, при равенстве выигрывает меньшее штрафное время."
            : "Отдельно садиться не нужно: очки капают за обычную активность за период по правилам ниже."}
        </p>
      </section>

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

        <div className="flex flex-wrap items-center gap-2">
          <span className="eyebrow">Когда:</span>
          <button className="btn-ghost text-sm" onClick={() => setWindow(2, 18)}>
            Сегодня 18:00, 2 часа
          </button>
          <button className="btn-ghost text-sm" onClick={() => setWindow(3, 12)}>
            Завтра 12:00, 3 часа
          </button>
          <button className="btn-ghost text-sm" onClick={() => setWindow(48)}>
            Двое суток
          </button>
          <button className="btn-ghost text-sm" onClick={() => setWindow(168)}>
            Неделя
          </button>
        </div>

        <div className="grid gap-5 sm:grid-cols-3">
          <label className="block">
            <span className="eyebrow">Начало, МСК</span>
            <input
              className="input mt-1.5 w-full"
              type="datetime-local"
              value={startsAt}
              onChange={(e) => setStartsAt(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="eyebrow">Конец, МСК</span>
            <input
              className="input mt-1.5 w-full"
              type="datetime-local"
              value={endsAt}
              onChange={(e) => setEndsAt(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="eyebrow">Пускать с рейтингом от</span>
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

        <p className="muted text-sm">
          Идёт {duration}. Время московское — и здесь, и у участников.
        </p>

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

      {format === "contest" && (
        <section className="card space-y-4" style={{ padding: "26px 28px" }}>
          <div className="section-head">
            <h2 className="section-title">Задачи контеста</h2>
            <span className="section-note">
              порядок = буквы A, B, C — ставь их по возрастанию сложности
            </span>
          </div>

          {problems.length === 0 ? (
            <p className="muted text-sm">Пока ни одной задачи.</p>
          ) : (
            <ul className="space-y-2">
              {problems.map((problem, index) => (
                <li
                  key={problem.task_id}
                  className="flex flex-wrap items-center gap-3 rounded-xl p-3"
                  style={{ background: "var(--surface)" }}
                >
                  <span className="h w-6 text-center">
                    {String.fromCharCode(65 + index)}
                  </span>
                  <span className="muted w-12 shrink-0 text-xs">
                    № {problem.number}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm">
                    {problem.statement}
                  </span>
                  <label className="flex items-center gap-2 text-sm">
                    баллов
                    <input
                      className="input"
                      style={{ width: 90 }}
                      type="number"
                      min={1}
                      value={problem.points}
                      onChange={(e) =>
                        setProblems((list) =>
                          list.map((item, i) =>
                            i === index
                              ? { ...item, points: Number(e.target.value) }
                              : item,
                          ),
                        )
                      }
                    />
                  </label>
                  <button
                    className="muted p-1"
                    title="Вверх"
                    onClick={() => move(index, -1)}
                    disabled={index === 0}
                  >
                    ↑
                  </button>
                  <button
                    className="muted p-1"
                    title="Вниз"
                    onClick={() => move(index, 1)}
                    disabled={index === problems.length - 1}
                  >
                    ↓
                  </button>
                  <button
                    className="muted p-2"
                    title="Убрать"
                    onClick={() =>
                      setProblems((list) => list.filter((_, i) => i !== index))
                    }
                  >
                    <Trash2 size={15} />
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <button
              className="btn-ghost text-sm"
              onClick={spreadPoints}
              disabled={problems.length === 0}
            >
              Расставить баллы по возрастанию
            </button>
            <label className="flex items-center gap-2 text-sm">
              Штраф за неверную попытку
              <input
                className="input"
                style={{ width: 80 }}
                type="number"
                min={0}
                value={penaltyMinutes}
                onChange={(e) => setPenaltyMinutes(Number(e.target.value))}
              />
              мин
            </label>
          </div>

          <div
            className="space-y-3 rounded-xl p-4"
            style={{ background: "var(--surface)" }}
          >
            <p className="eyebrow">Добавить из банка</p>

            <div className="flex flex-wrap gap-3">
              <input
                className="input min-w-[220px] flex-1"
                value={pickQuery}
                onChange={(e) => setPickQuery(e.target.value)}
                placeholder="Поиск по условию: «трапеция», «производная»…"
              />
              <select
                className="input"
                style={{ minWidth: 260 }}
                value={pickType ?? ""}
                onChange={(e) =>
                  setPickType(e.target.value ? Number(e.target.value) : null)
                }
              >
                <option value="">Любая тема</option>
                {types.map((type) => (
                  <option key={type.id} value={type.id}>
                    № {type.number} · {type.title} ({type.tasks_count})
                  </option>
                ))}
              </select>
            </div>

            {searching ? (
              <p className="muted text-sm">Ищем…</p>
            ) : picks.length === 0 ? (
              <p className="muted text-sm">Ничего не нашлось — измени запрос.</p>
            ) : (
              <ul className="max-h-80 space-y-1 overflow-y-auto">
                {picks.map((row) => {
                  const added = problems.some((p) => p.task_id === row.id);
                  return (
                    <li key={row.id}>
                      <button
                        className="flex w-full items-center gap-3 rounded-lg p-2 text-left text-sm disabled:opacity-40"
                        style={{ background: "var(--card)" }}
                        disabled={added}
                        onClick={() =>
                          setProblems((list) => [
                            ...list,
                            {
                              task_id: row.id,
                              points: (list.length + 1) * 100,
                              number: row.task_type_number,
                              statement: row.statement,
                            },
                          ])
                        }
                      >
                        {added ? (
                          <Check size={14} className="shrink-0" />
                        ) : (
                          <Plus size={14} className="shrink-0" />
                        )}
                        <span
                          className="muted shrink-0 text-xs"
                          style={{ width: 34 }}
                        >
                          № {row.task_type_number}
                        </span>
                        <span className="min-w-0 flex-1 truncate">
                          {row.statement}
                        </span>
                        <span className="muted shrink-0 text-xs">
                          {DIFFICULTY[row.difficulty] ?? row.difficulty} · ответ{" "}
                          {row.answer_value}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {ownOpen ? (
            <div
              className="space-y-4 rounded-xl p-4"
              style={{ background: "var(--surface)" }}
            >
              <div className="section-head">
                <p className="eyebrow">Своя задача</p>
                <button className="muted text-sm" onClick={() => setOwnOpen(false)}>
                  свернуть
                </button>
              </div>

              <div className="flex flex-wrap gap-3">
                <label className="min-w-[240px] flex-1">
                  <span className="eyebrow">Тема</span>
                  <select
                    className="input mt-1.5 w-full"
                    value={ownType ?? ""}
                    onChange={(e) =>
                      setOwnType(e.target.value ? Number(e.target.value) : null)
                    }
                  >
                    <option value="">Выбери номер задания</option>
                    {types.map((type) => (
                      <option key={type.id} value={type.id}>
                        № {type.number} · {type.title}
                      </option>
                    ))}
                  </select>
                </label>

                <label style={{ width: 170 }}>
                  <span className="eyebrow">Тип ответа</span>
                  <select
                    className="input mt-1.5 w-full"
                    value={ownAnswerType}
                    onChange={(e) => setOwnAnswerType(e.target.value)}
                  >
                    <option value="number">Число</option>
                    <option value="string">Слово</option>
                    <option value="digits">Цифры по порядку</option>
                    <option value="multi">Числа в любом порядке</option>
                  </select>
                </label>

                <label style={{ width: 150 }}>
                  <span className="eyebrow">Сложность 1–5</span>
                  <input
                    className="input mt-1.5 w-full"
                    type="number"
                    min={1}
                    max={5}
                    value={ownDifficulty}
                    onChange={(e) => setOwnDifficulty(Number(e.target.value))}
                  />
                </label>
              </div>

              <label className="block">
                <span className="eyebrow">Условие</span>
                <textarea
                  className="input mt-1.5 min-h-24 w-full"
                  value={ownStatement}
                  onChange={(e) => setOwnStatement(e.target.value)}
                  placeholder="Формулы в TeX: $\\frac{3}{4}$"
                />
              </label>

              {ownStatement && (
                <div className="rounded-xl p-3" style={{ background: "var(--card)" }}>
                  <p className="eyebrow mb-1.5">Как увидит участник</p>
                  <MathText text={ownStatement} />
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                <label style={{ width: 200 }}>
                  <span className="eyebrow">Ответ</span>
                  <input
                    className="input mt-1.5 w-full"
                    value={ownAnswer}
                    onChange={(e) => setOwnAnswer(e.target.value)}
                    placeholder="как в бланке"
                  />
                </label>
                <label className="min-w-[240px] flex-1">
                  <span className="eyebrow">Разбор (не обязательно)</span>
                  <input
                    className="input mt-1.5 w-full"
                    value={ownSolution}
                    onChange={(e) => setOwnSolution(e.target.value)}
                    placeholder="покажем после контеста"
                  />
                </label>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button className="btn text-sm" onClick={createOwn} disabled={ownBusy}>
                  {ownBusy ? "Создаём…" : "Создать и добавить в контест"}
                </button>
                <span className="muted text-xs">
                  Задача сохранится черновиком: в квизах до публикации не появится.
                </span>
              </div>
            </div>
          ) : (
            <button className="btn-ghost text-sm" onClick={() => setOwnOpen(true)}>
              <Plus size={15} /> Своя задача
            </button>
          )}
        </section>
      )}

      {format === "marathon" && (
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
      )}

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
