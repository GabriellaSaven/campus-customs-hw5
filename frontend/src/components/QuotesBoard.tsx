import { AGENTS } from "../agents";
import { QUOTES, SHOW } from "../quotes";
import { Avatar } from "./Avatar";

/** The break-room quotes board: one famous line per person, pinned up. */
export function QuotesBoard() {
  return (
    <section className="quotes-board">
      <header className="section-title on-cork">
        <h2>Break-room quotes board</h2>
        <span className="hand small">as heard on {SHOW}</span>
      </header>
      <div className="quote-cards">
        {QUOTES.map((q, i) => {
          const meta = AGENTS[q.agent];
          return (
            <figure
              key={q.agent}
              className={`quote-card ${q.text ? "" : "empty"}`}
              style={{ ["--agent" as string]: meta.color, ["--tilt" as string]: `${[-1.6, 1.2, -0.8, 1.6, -1.1][i % 5]}deg` }}
            >
              <span className="pin" />
              {q.text ? (
                <blockquote>“{q.text}”</blockquote>
              ) : (
                <blockquote className="hand">Tack your favorite {q.character.split(" ")[0]} line here.</blockquote>
              )}
              <figcaption>
                <Avatar agent={q.agent} size={20} />
                <span>
                  <b>{q.character}</b> <span className="muted">· our {meta.role}</span>
                </span>
              </figcaption>
            </figure>
          );
        })}
      </div>
    </section>
  );
}
