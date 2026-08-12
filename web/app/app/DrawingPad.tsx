"use client";

import { useEffect, useRef, useState } from "react";
import { Eraser, Redo2, Undo2 } from "lucide-react";

/**
 * Черновик к задаче: рисовать чертёж прямо в браузере.
 *
 * Штрихи храним списком точек, а не картинкой, — только так работают «назад»
 * и «вернуть»: отменённый штрих просто перестаёт рисоваться при перерисовке.
 * Никуда не сохраняется: черновик живёт, пока открыта задача.
 */

type Point = { x: number; y: number };
type Stroke = { points: Point[]; color: string; width: number };

const COLORS = ["#14171c", "#0088b0", "#d6006c", "#1f9d55", "#e0a800"];
const WIDTHS = [2, 4, 8];

export default function DrawingPad({ height = 320 }: { height?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [undone, setUndone] = useState<Stroke[]>([]);
  const [color, setColor] = useState(COLORS[0]);
  const [width, setWidth] = useState(WIDTHS[1]);
  const drawing = useRef(false);

  function repaint() {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (const stroke of strokes) {
      ctx.beginPath();
      ctx.strokeStyle = stroke.color;
      ctx.lineWidth = stroke.width;
      stroke.points.forEach((point, i) =>
        i === 0 ? ctx.moveTo(point.x, point.y) : ctx.lineTo(point.x, point.y),
      );
      ctx.stroke();
    }
  }

  useEffect(repaint, [strokes]);

  // холст тянется по ширине карточки — размер в пикселях выставляем вручную
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = height;
      repaint();
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height]);

  function pointFrom(e: React.PointerEvent<HTMLCanvasElement>): Point {
    const rect = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function start(e: React.PointerEvent<HTMLCanvasElement>) {
    e.currentTarget.setPointerCapture(e.pointerId);
    drawing.current = true;
    setUndone([]); // новая линия обрывает цепочку «вернуть»
    setStrokes((prev) => [...prev, { points: [pointFrom(e)], color, width }]);
  }

  function move(e: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) return;
    const point = pointFrom(e);
    setStrokes((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      next[next.length - 1] = { ...last, points: [...last.points, point] };
      return next;
    });
  }

  function stop() {
    drawing.current = false;
  }

  function undo() {
    setStrokes((prev) => {
      if (prev.length === 0) return prev;
      setUndone((u) => [...u, prev[prev.length - 1]]);
      return prev.slice(0, -1);
    });
  }

  function redo() {
    setUndone((prev) => {
      if (prev.length === 0) return prev;
      setStrokes((s) => [...s, prev[prev.length - 1]]);
      return prev.slice(0, -1);
    });
  }

  return (
    <div className="space-y-3">
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
                style={{ width: w + 2, height: w + 2, background: "var(--text)" }}
              />
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button
            className="btn-ghost px-3 py-1.5 text-sm"
            onClick={undo}
            disabled={strokes.length === 0}
            title="Отменить"
          >
            <Undo2 size={15} />
          </button>
          <button
            className="btn-ghost px-3 py-1.5 text-sm"
            onClick={redo}
            disabled={undone.length === 0}
            title="Вернуть"
          >
            <Redo2 size={15} />
          </button>
          <button
            className="btn-ghost px-3 py-1.5 text-sm"
            onClick={() => {
              setStrokes([]);
              setUndone([]);
            }}
            disabled={strokes.length === 0}
            title="Очистить"
          >
            <Eraser size={15} />
          </button>
        </div>
      </div>

      <canvas
        ref={canvasRef}
        className="w-full touch-none rounded-xl border"
        style={{ height, borderColor: "var(--divider)", background: "var(--card)" }}
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={stop}
        onPointerLeave={stop}
      />
      <p className="muted text-xs">
        Черновик виден только тебе и стирается при переходе к следующей задаче.
      </p>
    </div>
  );
}
