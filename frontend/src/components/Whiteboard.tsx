import type { Briefing } from "../types";

/** The office whiteboard: today's to-do list in marker, straight from shop data. */
export function Whiteboard({ briefing }: { briefing: Briefing | null }) {
  if (!briefing) return null;
  const date = new Date(briefing.today + "T12:00").toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  return (
    <section className="whiteboard">
      <div className="wb-title">
        <span className="wb-today">Today: {date}</span>
        <span className="wb-count">
          {briefing.open_files} open file{briefing.open_files === 1 ? "" : "s"}
          {briefing.untouched_files ? ` · ${briefing.untouched_files} untouched` : ""}
        </span>
      </div>
      <ul className="wb-items">
        {briefing.items.length === 0 ? (
          <li className="wb-green">Nothing on fire. Enjoy it.</li>
        ) : (
          briefing.items.map((it, i) => (
            <li key={i} className={`wb-${it.tone}`}>
              {it.text}
            </li>
          ))
        )}
      </ul>
      <span className="wb-marker" aria-hidden />
      <span className="wb-eraser" aria-hidden />
    </section>
  );
}
