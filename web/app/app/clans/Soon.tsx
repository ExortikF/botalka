import { Castle } from "lucide-react";

/** Заглушка на время заморозки кланов, см. `web/lib/features.ts`. */
export default function ClansSoon() {
  return (
    <div className="page">
      <section className="card flex flex-col items-center gap-3 p-12 text-center">
        <Castle size={30} style={{ color: "var(--accent)" }} />
        <h1 className="page-title">Кланы скоро появятся</h1>
        <p className="page-subtitle mx-auto">
          Команды с тегом рядом с ником, общая казна и войны кланов уже готовы,
          но включим их, когда наберётся достаточно людей: клан из одного
          человека — это грустно, а война двух таких кланов ничем не отличается
          от обычной дуэли.
        </p>
        <p className="muted text-sm">А пока есть дуэли, турниры и задача дня.</p>
      </section>
    </div>
  );
}
