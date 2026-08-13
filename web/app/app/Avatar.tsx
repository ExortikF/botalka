"use client";

import { avatarEmoji, avatarStyle, frameStyle } from "@/lib/cosmetics";
import { initials } from "@/lib/format";

/**
 * Аватарка с рамкой. Одна на всё приложение: профиль, сайдбар, лидерборд,
 * друзья, дуэли — иначе косметика в одних местах применяется, в других нет.
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
      className={`flex shrink-0 items-center justify-center ${rounded} ${look.className} ${ring.className}`}
      style={{
        width: size,
        height: size,
        fontSize: emoji ? size * 0.5 : size * 0.36,
        fontWeight: 700,
        ...look.style,
        ...ring.style,
      }}
    >
      {emoji ?? initials(name)}
    </span>
  );
}
