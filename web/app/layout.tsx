import type { Metadata } from "next";
import { Inter_Tight, Nunito } from "next/font/google";
import "katex/dist/katex.min.css";
import "./globals.css";

const heading = Nunito({
  subsets: ["latin", "cyrillic"],
  weight: ["600", "700"],
  variable: "--font-heading",
});

const body = Inter_Tight({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "Боталка — тренажёр для подготовки к ЕГЭ",
  description:
    "Короткие квизы вместо многочасовых занятий, разбор каждой ошибки и дуэли 1 на 1.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={`${heading.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
