"use client";

import { avatarEmoji, avatarStyle, frameStyle } from "@/lib/cosmetics";
import { initials } from "@/lib/format";

/**
 * Аватарка с рамкой. Одна на всё приложение: профиль, сайдбар, лидерборд,
 * друзья, дуэли — иначе косметика в одних местах применяется, в других нет.
 *
 * Рамка и подложка живут на разных элементах намеренно. Градиентные рамки
 * рисуются двумя фонами с обрезкой по padding-box, и на одном элементе такой
 * фон затирал бы цвет аватарки — вместо купленной подложки был бы цвет карточки.
 */
export default function Avatar({
  name,
  avatar,
  frame,
  size = 44,
  rounded = "rounded-2xl",
}: {
  name: string;
  avatar?: string | null;
  frame?: string | null;
  size?: number;
  rounded?: string;
}) {
  const look = avatarStyle(avatar);
  const ring = frameStyle(frame);
  const emoji = avatarEmoji(avatar);

  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center ${rounded} ${ring.className}`}
      style={{ width: size, height: size, boxSizing: "border-box", ...ring.style }}
    >
      <span
        className={`flex h-full w-full items-center justify-center ${rounded} ${look.className}`}
        style={{
          fontSize: emoji ? size * 0.5 : size * 0.36,
          fontWeight: 700,
          lineHeight: 1,
          ...look.style,
        }}
      >
        {emoji ?? initials(name)}
      </span>
    </span>
  );
}
