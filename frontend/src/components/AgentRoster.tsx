import { AGENTS, AGENT_ORDER } from "../agents";
import type { RosterEntry } from "../feed";
import type { AgentName } from "../types";
import { Avatar } from "./Avatar";

const STATE_LABEL = { idle: "at desk", working: "on it", waiting: "waiting", done: "done", error: "uh oh" } as const;

/** The staff directory: one ID badge per person, live status underneath. */
export function AgentRoster({ roster, live }: { roster: Record<AgentName, RosterEntry>; live: boolean }) {
  return (
    <section className="directory">
      <header className="section-title">
        <h2>Staff directory</h2>
        <span className={`live-dot ${live ? "on" : ""}`}>{live ? "On the clock" : "Quiet"}</span>
      </header>
      <ul className="badges">
        {AGENT_ORDER.map((a, i) => {
          const r = roster[a];
          const m = AGENTS[a];
          return (
            <li
              key={a}
              className={`badge state-${r.state}`}
              style={{ ["--agent" as string]: m.color, ["--tilt" as string]: `${[-0.6, 0.4, -0.3, 0.5, -0.4][i]}deg` }}
            >
              <span className="badge-clip" />
              <div className="badge-photo">
                <Avatar agent={a} size={40} />
                {r.state === "working" && <span className="pulse-ring" />}
              </div>
              <div className="badge-text">
                <div className="badge-name">
                  {m.name} <span className="badge-role">{m.role}</span>
                </div>
                <div className="badge-tagline">{m.tagline}</div>
                <div className="badge-status">
                  <span className={`state-chip chip-${r.state}`}>{STATE_LABEL[r.state]}</span> {r.detail}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
