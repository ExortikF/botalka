import type { Config } from "tailwindcss";

/* Цвета живут в CSS-переменных (app/globals.css, см. docs/DESIGN.md).
   Здесь их дублировать нельзя: раньше тут лежала вторая палитра
   (accent: #6366F1 и др.), не совпадающая с токенами. Классов из неё
   в коде не было, но любой новый `bg-accent` покрасил бы кнопку мимо системы. */
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
} satisfies Config;
