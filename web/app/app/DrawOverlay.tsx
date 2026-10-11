"use client";

import { useEffect, useRef, useState } from "react";
import { Eraser, PenLine, Undo2, X } from "lucide-react";
import type { Stroke } from "./DrawingPad";

const COLORS = ["#14171c", "#0088b0", "#d6006c", "#1f9d55"];

/**
 * Рисование поверх всей страницы: можно чертить прямо на условии, на графике
 * и на своих ответах, не переводя взгляд на отдельный лист.
 *
 * Холст растянут на весь экран и ловит указатель только при включённом режиме —
 * иначе он перехватывал бы клики по кнопкам под собой. Штрихи, как и в листе,
 * хранит родитель: свои для каждой задачи.
 */
export default function DrawOverlay({
  strokes,
  onChange,
  onClose,
}: {
  strokes: Stroke[];
  onChange: (next: Stroke[]) => void;
  onClose: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const strokesRef = useRef(strokes);
  strokesRef.current = strokes;

  const [color, setColor] = useState(COLORS[0]);

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

  // Размер холста привязан к окну: при повороте и изменении размера рисунок
  // перерисовываем, иначе он растянется вместе с растяжением холста.
  useEffect(() => {
    function resize() {
      const canvas = canvasRef.current;
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      repaint();
    }

    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  function point(event: React.PointerEvent) {
    const canvas = canvasRef.current!;
    const box = canvas.getBoundingClientRect();
    return { x: event.clientX - box.left, y: event.clientY - box.top };
  }

  return (
    <>
      <canvas
        ref={canvasRef}
        className="fixed inset-0 z-40 touch-none"
        style={{ cursor: "crosshair" }}
        onPointerDown={(e) => {
          (e.target as HTMLCanvasElement).setPointerCapture(e.pointerId);
          drawing.current = true;
          onChange([
            ...strokesRef.current,
            { points: [point(e)], color, width: 3 },
          ]);
        }}
        onPointerMove={(e) => {
          if (!drawing.current) return;
          const list = strokesRef.current;
          const last = list[list.length - 1];
          onChange([
            ...list.slice(0, -1),
            { ...last, points: [...last.points, point(e)] },
          ]);
        }}
        onPointerUp={() => (drawing.current = false)}
        onPointerLeave={() => (drawing.current = false)}
      />

      <div
        className="card fixed z-50 flex items-center gap-2 p-2"
        style={{ right: 24, bottom: 24, boxShadow: "var(--shadow-md)" }}
      >
        <PenLine size={15} style={{ color: "var(--accent)" }} />

        {COLORS.map((value) => (
          <button
            key={value}
            aria-label={value}
            onClick={() => setColor(value)}
            className="h-6 w-6 rounded-full"
            style={{
              background: value,
              outline: color === value ? "2px solid var(--text)" : "none",
              outlineOffset: 2,
            }}
          />
        ))}

        <button
          className="muted p-1.5"
          title="Отменить штрих"
          aria-label="Отменить штрих"
          onClick={() => onChange(strokes.slice(0, -1))}
        >
          <Undo2 size={15} />
        </button>
        <button
          className="muted p-1.5"
          title="Стереть всё"
          aria-label="Стереть всё"
          onClick={() => onChange([])}
        >
          <Eraser size={15} />
        </button>
        <button className="btn-ghost text-sm" onClick={onClose}>
          <X size={14} /> Готово
        </button>
      </div>
    </>
  );
}
