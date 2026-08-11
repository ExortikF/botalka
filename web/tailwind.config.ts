import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0F172A",
        accent: "#6366F1",
        correct: "#16A34A",
        wrong: "#DC2626",
      },
    },
  },
} satisfies Config;
