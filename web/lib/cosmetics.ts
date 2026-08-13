/**
 * Разбор косметики из магазина.
 *
 * Формат `value` задаёт бэкенд (backend/app/cli/seed_shop.py). Здесь он
 * превращается в стили. Держим всё в одном месте: ник рисуется в профиле,
 * лидерборде, друзьях и дуэлях — расхождения в отрисовке сразу заметны.
 */

export type Cosmetics = {
  nick_color: string | null;
  prefix: string | null;
  frame: string | null;
  avatar: string | null;
  card_bg: string | null;
  name_plate: string | null;
};

export const EMPTY_COSMETICS: Cosmetics = {
  nick_color: null,
  prefix: null,
  frame: null,
  avatar: null,
  card_bg: null,
  name_plate: null,
};

/** Стиль для текста ника: цвет, градиент, свечение или радуга. */
export function nickStyle(value: string | null | undefined): {
  style: React.CSSProperties;
  className: string;
} {
  if (!value) return { style: {}, className: "" };

  if (value === "rainbow") {
    return { style: {}, className: "nick-rainbow" };
  }

  if (value === "matrix") {
    return { style: {}, className: "nick-matrix" };
  }

  if (value.startsWith("gradient:")) {
    const [from, to] = value.slice(9).split(",");
    return {
      style: {
        backgroundImage: `linear-gradient(90deg, ${from}, ${to})`,
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
      },
      className: "",
    };
  }

  if (value.startsWith("glow:")) {
    const color = value.slice(5);
    return {
      style: { color, ["--glow" as string]: color },
      className: "nick-glow",
    };
  }

  if (value.startsWith("shine:")) {
    const color = value.slice(6);
    return {
      style: {
        backgroundImage: `linear-gradient(100deg, ${color} 20%, #fff8d8 45%, ${color} 70%)`,
        WebkitBackgroundClip: "text",
        backgroundClip: "text",
        color: "transparent",
      },
      className: "nick-shine",
    };
  }

  return { style: { color: value }, className: "" };
}

/** Стиль рамки вокруг аватарки. */
export function frameStyle(value: string | null | undefined): {
  style: React.CSSProperties;
  className: string;
} {
  if (!value || value === "none") return { style: {}, className: "" };

  if (value.startsWith("solid:")) {
    return { style: { border: `4px solid ${value.slice(6)}` }, className: "" };
  }

  if (value.startsWith("gradient:")) {
    const [from, to] = value.slice(9).split(",");
    return {
      style: {
        border: "4px solid transparent",
        backgroundImage: `linear-gradient(var(--card), var(--card)), linear-gradient(135deg, ${from}, ${to})`,
        backgroundOrigin: "border-box",
        backgroundClip: "padding-box, border-box",
      },
      className: "",
    };
  }

  if (value.startsWith("pulse:")) {
    const color = value.slice(6);
    return {
      style: { border: `4px solid ${color}`, ["--pulse" as string]: color },
      className: "frame-pulse",
    };
  }

  if (value.startsWith("rotate:")) {
    const [from, to] = value.slice(7).split(",");
    return {
      style: {
        border: "4px solid transparent",
        backgroundImage: `linear-gradient(var(--card), var(--card)), conic-gradient(from var(--angle), ${from}, ${to}, ${from})`,
        backgroundOrigin: "border-box",
        backgroundClip: "padding-box, border-box",
      },
      className: "frame-rotate",
    };
  }

  return { style: { border: `4px solid ${value}` }, className: "" };
}

/** Фон карточки профиля. Возвращает и цвет текста: на тёмных фонах он светлый. */
export function cardBackground(value: string | null | undefined): {
  style: React.CSSProperties;
  dark: boolean;
} {
  if (!value || value === "none") return { style: {}, dark: false };

  if (value.startsWith("gradient:")) {
    const [from, to] = value.slice(9).split(",");
    return {
      style: { backgroundImage: `linear-gradient(135deg, ${from}, ${to})` },
      dark: isDark(from),
    };
  }

  if (value.startsWith("aurora:")) {
    const colors = value.slice(7).split(",");
    return {
      style: {
        backgroundImage: `linear-gradient(120deg, ${colors.join(", ")}, ${colors[0]})`,
        backgroundSize: "300% 300%",
      },
      dark: true,
    };
  }

  return { style: { background: value }, dark: isDark(value) };
}

/** Тёмный ли цвет — по яркости, чтобы понять, каким цветом писать поверх. */
function isDark(hex: string): boolean {
  const clean = hex.replace("#", "");
  if (clean.length < 6) return false;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 < 128;
}

export function auroraClass(value: string | null | undefined): string {
  return value?.startsWith("aurora:") ? "bg-aurora" : "";
}

/**
 * Аватарка: не эмодзи, а подложка с монограммой. Одинаково выглядит на всех
 * системах и не выбивается из интерфейса.
 *
 *   mono:#bg,#fg      спокойная подложка
 *   grad:#a,#b        градиент, буквы белым
 *   holo · admin      анимированные, для дорогих и эксклюзивных
 */
export function avatarStyle(value: string | null | undefined): {
  style: React.CSSProperties;
  className: string;
  light: boolean;
} {
  if (!value || value === "initials" || value.startsWith("mono:")) {
    const [bg, fg] = (
      value?.startsWith("mono:") ? value.slice(5) : "#e9f8ff,#0088b0"
    ).split(",");
    return {
      style: { background: bg, color: fg },
      className: "",
      light: false,
    };
  }

  if (value.startsWith("grad:")) {
    const [from, to] = value.slice(5).split(",");
    return {
      style: {
        backgroundImage: `linear-gradient(135deg, ${from}, ${to})`,
        color: "#fff",
      },
      className: "",
      light: true,
    };
  }

  if (value === "holo")
    return { style: { color: "#fff" }, className: "avatar-holo", light: true };

  if (value === "admin")
    return {
      style: { color: "#0b3d2e" },
      className: "avatar-admin",
      light: false,
    };

  if (value.startsWith("shineav:")) {
    const [from, to] = value.slice(8).split(",");
    return {
      style: {
        backgroundImage: `linear-gradient(120deg, ${from}, ${to}, ${from})`,
        backgroundSize: "200% auto",
        color: "#3a2c00",
      },
      className: "avatar-shine",
      light: false,
    };
  }

  // старые эмодзи-аватарки: остаются у тех, кто успел купить
  return {
    style: { background: "var(--accent-100)" },
    className: "",
    light: false,
  };
}

/** Эмодзи ли это (старые аватарки) — тогда рисуем символ, а не инициалы. */
export function avatarEmoji(value: string | null | undefined): string | null {
  if (!value) return null;
  const known = ["initials", "holo", "admin"];
  if (known.includes(value) || value.includes(":")) return null;
  return value;
}

/** Декор плиты с ником: полоска, уголки, стекло, неон, звёзды. */
export function plateStyle(value: string | null | undefined): {
  style: React.CSSProperties;
  className: string;
} {
  if (!value || value === "none") return { style: {}, className: "" };

  if (value.startsWith("bar:"))
    return {
      style: { borderLeft: `6px solid ${value.slice(4)}` },
      className: "",
    };

  if (value.startsWith("corner:")) {
    const color = value.slice(7);
    return {
      style: {
        borderTop: `3px solid ${color}`,
        borderRight: `3px solid ${color}`,
        borderTopRightRadius: 0,
      },
      className: "",
    };
  }

  if (value.startsWith("grid:"))
    return {
      style: { ["--gridc" as string]: value.slice(5) },
      className: "plate-grid",
    };

  if (value.startsWith("neon:")) {
    const color = value.slice(5);
    return { style: { ["--neon" as string]: color }, className: "plate-neon" };
  }

  if (value.startsWith("stars:")) {
    const color = value.slice(6);
    return { style: { ["--star" as string]: color }, className: "plate-stars" };
  }

  if (value === "matrixplate") return { style: {}, className: "plate-matrix" };

  return { style: {}, className: "" };
}
