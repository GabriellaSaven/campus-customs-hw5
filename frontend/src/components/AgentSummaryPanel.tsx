import { AGENTS } from "../agents";
import type { TicketSummary } from "../types";
import { Avatar } from "./Avatar";

/** End-of-shift reports: one index card per person who worked the file. */
export function AgentSummaryPanel({ summary }: { summary: TicketSummary | null }) {
  if (!summary?.run_id || summary.status === "running") return null;
  return (
    <section className="reports">
      <header className="section-title">
        <h2>End-of-shift reports</h2>
        <span className="hand small">{summary.total_tokens?.toLocaleString()} tokens on this file</span>
      </header>
      <div className="report-grid">
        {summary.agents.map((a, i) => {
          const meta = AGENTS[a.agent];
          const tools = Object.entries(a.tools);
          return (
            <article
              key={a.agent}
              className="index-card"
              style={{ ["--agent" as string]: meta.color, ["--tilt" as string]: `${[0.5, -0.6, 0.3, -0.4, 0.6][i % 5]}deg` }}
            >
              <div className="index-head">
                <Avatar agent={a.agent} size={30} />
                <div>
                  <div className="index-name">
                    {meta.name} <span className="badge-role">{meta.role}</span>
                  </div>
                  <div className="hand small">
                    {a.asked_by.length
                      ? `${a.asked_by.map((x) => AGENTS[x].name).join(", ")} stopped by`
                      : "Took the file"}
                    {a.asked.length ? ` · went to ${a.asked.map((x) => AGENTS[x].name).join(", ")}` : ""}
                  </div>
                </div>
                {a.needs_human && <span className="sticker sticker-awaiting_approval">needs you</span>}
              </div>
              <p className={`index-text voice voice-${a.agent}`}>{a.summary ?? "—"}</p>
              {tools.length > 0 && (
                <div className="chips">
                  {tools.map(([tool, n]) => (
                    <span key={tool} className="chip small">
                      <span className="chip-tool">{tool}</span>
                      {n > 1 && <span className="chip-count">×{n}</span>}
                    </span>
                  ))}
                </div>
              )}
              {a.actions_taken.length > 0 && (
                <ul className="index-list">
                  {a.actions_taken.map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
