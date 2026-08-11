"use client";

import katex from "katex";
import { useMemo } from "react";

/**
 * Рендерит текст с формулами в долларах: «Найдите $x$, если $2x=4$».
 * Всё, что вне долларов, остаётся обычным текстом и не интерпретируется как HTML —
 * условие задачи приходит из банка, но подставлять сырой HTML всё равно не будем.
 */
export default function MathText({ text, className }: { text: string; className?: string }) {
  const parts = useMemo(() => {
    const chunks: { math: boolean; value: string }[] = [];
    // нечётные куски между одиночными $ — формулы
    text.split("$").forEach((chunk, i) => chunks.push({ math: i % 2 === 1, value: chunk }));
    return chunks;
  }, [text]);

  return (
    <span className={className}>
      {parts.map((part, i) =>
        part.math ? (
          <span
            key={i}
            dangerouslySetInnerHTML={{
              __html: katex.renderToString(part.value, {
                throwOnError: false,
                displayMode: false,
              }),
            }}
          />
        ) : (
          <span key={i}>{part.value}</span>
        ),
      )}
    </span>
  );
}
