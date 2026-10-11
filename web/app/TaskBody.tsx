"use client";

import MathText from "./Math";

/**
 * Условие задачи целиком: текст с формулами, картинки внутри предложения и
 * чертёж под условием.
 *
 * Зачем отдельный компонент: у задач из открытого банка ФИПИ часть чисел
 * вставлена картинками прямо в текст («температура ниже чем [36,8 °C]»), а
 * чертежи к планиметрии и графики к производной — обязательная часть условия.
 * Без них задача просто нерешаема, поэтому показывать их надо везде, где
 * показывается условие: в квизе, пробнике, задаче дня и турнире.
 *
 * Встроенные картинки размечены в тексте как `[[img:имя-файла]]` — разметку
 * ставит tools/fipi_parse.py.
 */

const INLINE = /\[\[img:([^\]]+)\]\]/g;

/** Путь к файлу картинки. Относительные пути ведут в /content, который
 *  раздаёт бэкенд (в проде — nginx), абсолютные оставляем как есть. */
function src(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return path.startsWith("/content/") ? path : `/content/${path.replace(/^\/+/, "")}`;
}

export default function TaskBody({
  statement,
  imageUrl,
  className,
}: {
  statement: string;
  imageUrl?: string | null;
  className?: string;
}) {
  const parts = statement.split(INLINE);
  // split с группой чередует куски: текст, имя файла, текст, имя файла, …
  const inlineNames = new Set<string>();

  return (
    <div className={className}>
      <p className="leading-relaxed">
        {parts.map((part, index) => {
          if (index % 2 === 0) return <MathText key={index} text={part} />;
          inlineNames.add(part);
          return (
            <img
              key={index}
              src={src(part)}
              alt=""
              className="mx-1 inline-block align-middle"
              style={{ maxHeight: "1.4em" }}
            />
          );
        })}
      </p>

      {/* Чертёж под условием. Если эта же картинка уже вставлена в текст,
          второй раз не показываем. */}
      {imageUrl && !inlineNames.has(imageUrl) && (
        <img
          src={src(imageUrl)}
          alt="Рисунок к задаче"
          className="mt-4 rounded-[var(--radius-md)]"
          style={{ maxWidth: "100%", maxHeight: 320 }}
        />
      )}
    </div>
  );
}
