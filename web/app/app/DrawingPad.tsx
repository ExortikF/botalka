"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Eraser, Redo2, Undo2 } from "lucide-react";

/**
 * Черновик: большой лист в клетку под задачей.
 *
 * Штрихи храним списком точек, а не картинкой, — только так работают «назад»
 * и «вернуть»: отменённый штрих просто перестаёт рисоваться при перерисовке.
 *
 * Состояние живёт **снаружи**, в родителе: иначе черновик стирался бы при
 * переходе к следующей задаче, когда компонент размонтируется.
 */

export type Point = { x: number; y: number };
export type Stroke = { points: Point[]; color: string; width: number };

const COLORS = ["#14171c", "#0088b0", "#d6006c", "#1f9d55", "#e0a800"];
const WIDTHS = [2, 4, 8];
const CELL = 24; // размер клетки, как в тетради

export default function DrawingPad({
  strokes,
  onChange,
  onClose,
  height = 820,
}: {
  strokes: Stroke[];
  onChange: (next: Stroke[]) => void;
  onClose?: () => void;
  height?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [undone, setUndone] = useState<Stroke[]>([]);
  const [color, setColor] = useState(COLORS[0]);
  const [width, setWidth] = useState(WIDTHS[1]);
  const drawing = useRef(false);
  const strokesRef = useRef(strokes);
  strokesRef.current = strokes;

  /**
   * Рисуем из strokesRef, а не из пропса: перерисовку зовёт и ResizeObserver,
   * чей колбэк создан на первом рендере. С замыканием на `strokes` он рисовал бы
   * пустой список, и при изменении ширины черновик стирался бы.
   */
  function repaint() {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (const stroke of strokesRef.current) {
      // Точка — это тоже след: одиночное касание раньше не оставляло ничего,
      // потому что путь из одной точки не рисуется.
      if (stroke.points.length === 1) {
        const [p] = stroke.points;
        ctx.beginPath();
        ctx.fillStyle = stroke.color;
        ctx.arc(p.x, p.y, stroke.width / 2, 0, Math.PI * 2);
        ctx.fill();
        continue;
      }

      ctx.beginPath();
      ctx.strokeStyle = stroke.color;
      ctx.lineWidth = stroke.width;
      stroke.points.forEach((p, i) =>
        i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y),
      );
      ctx.stroke();
    }
  }

  useEffect(repaint, [strokes]);

  /**
   * Подгонка холста под ширину контейнера.
   *
   * Одного ResizeObserver мало: его первый вызов может прийти с нулевой шириной,
   * пока элемент не разложен, а второго не будет — размер-то больше не меняется.
   * Холст так и оставался 300×150 по умолчанию, и черновик, вернувшийся из
   * состояния, просто не рисовался. Поэтому меряем сами и, если рано, повторяем
   * на следующем кадре.
   */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    function fit(): boolean {
      const width = Math.round(canvas!.getBoundingClientRect().width);
      if (width <= 0) return false;
      if (canvas!.width !== width || canvas!.height !== height) {
        canvas!.width = width;
        canvas!.height = height;
      }
      repaint();
      return true;
    }

    if (!fit()) requestAnimationFrame(fit);

    const observer = new ResizeObserver(() => fit());
    observer.observe(canvas);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height]);

  /**
   * Координаты берём у самого холста через ref, а не у e.currentTarget:
   * внутри асинхронного обновления состояния currentTarget уже равен null.
   */
  function pointAt(clientX: number, clientY: number): Point | null {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  }

  function start(e: React.PointerEvent<HTMLCanvasElement>) {
    const point = pointAt(e.clientX, e.clientY);
    if (!point) return;
    canvasRef.current?.setPointerCapture(e.pointerId);
    drawing.current = true;
    setUndone([]); // новая линия обрывает цепочку «вернуть»
    onChange([...strokesRef.current, { points: [point], color, width }]);
  }

  function move(e: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) return;
    const point = pointAt(e.clientX, e.clientY);
    if (!point) return;

    const current = strokesRef.current;
    const last = current[current.length - 1];
    if (!last) return;
    onChange([
      ...current.slice(0, -1),
      { ...last, points: [...last.points, point] },
    ]);
  }

  function stop() {
    drawing.current = false;
  }

  function undo() {
    const current = strokesRef.current;
    if (current.length === 0) return;
    setUndone((u) => [...u, current[current.length - 1]]);
    onChange(current.slice(0, -1));
  }

  function redo() {
    if (undone.length === 0) return;
    onChange([...strokesRef.current, undone[undone.length - 1]]);
    setUndone((u) => u.slice(0, -1));
  }

  return (
    <section className="card space-y-3 p-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1.5">
          {COLORS.map((c) => (
            <button
              key={c}
              onClick={() => setColor(c)}
              aria-label={`Цвет ${c}`}
              className="h-6 w-6 rounded-full transition"
              style={{
                background: c,
                outline: color === c ? `2px solid ${c}` : "none",
                outlineOffset: 2,
              }}
            />
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          {WIDTHS.map((w) => (
            <button
              key={w}
              onClick={() => setWidth(w)}
              aria-label={`Толщина ${w}`}
              className="flex h-7 w-7 items-center justify-center rounded-lg border"
              style={{
                borderColor: width === w ? "var(--accent)" : "var(--divider)",
                background: width === w ? "var(--accent-100)" : "var(--card)",
              }}
            >
              <span
                className="block rounded-full"
                style={{
                  width: w + 2,
                  height: w + 2,
                  background: "var(--text)",
                }}
              />
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button
            className="btn-ghost px-3 py-1.5"
            onClick={undo}
            disabled={strokes.length === 0}
            title="Отменить"
            aria-label="Отменить"
          >
            <Undo2 size={15} />
          </button>
          <button
            className="btn-ghost px-3 py-1.5"
            onClick={redo}
            disabled={undone.length === 0}
            title="Вернуть"
            aria-label="Вернуть"
          >
            <Redo2 size={15} />
          </button>
          <button
            className="btn-ghost px-3 py-1.5"
            onClick={() => {
              onChange([]);
              setUndone([]);
            }}
            disabled={strokes.length === 0}
            title="Очистить"
            aria-label="Очистить"
          >
            <Eraser size={15} />
          </button>
          {onClose && (
            <button
              className="btn-ghost px-3 py-1.5"
              onClick={onClose}
              title="Свернуть черновик"
              aria-label="Свернуть черновик"
            >
              <ChevronDown size={15} />
            </button>
          )}
        </div>
      </div>

      <div
        className="rounded-xl border"
        style={{
          borderColor: "var(--divider)",
          // лист в клетку: две сетки линий поверх белого
          background: `
            repeating-linear-gradient(to right, #dbe6f0 0 1px, transparent 1px ${CELL}px),
            repeating-linear-gradient(to bottom, #dbe6f0 0 1px, transparent 1px ${CELL}px),
            #ffffff`,
        }}
      >
        <canvas
          ref={canvasRef}
          className="block w-full touch-none"
          style={{ height }}
          onPointerDown={start}
          onPointerMove={move}
          onPointerUp={stop}
          onPointerLeave={stop}
          onPointerCancel={stop}
        />
      </div>

      <p className="muted text-xs">
        У каждого задания свой черновик — он сохраняется, пока идёт квиз.
      </p>
    </section>
  );
}
