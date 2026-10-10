import { AGENTS, AGENT_ORDER } from "../agents";
import type { AgentEvent, AgentName } from "../types";
import { Avatar } from "./Avatar";

interface Score {
  agent: AgentName;
  jobs: number;
  files: number;
  slips: number;
}

/** Tally who's done the most since the last fresh day (from the audit trail). */
function tally(events: AgentEvent[]): Score[] {
  const s = Object.fromEntries(
    AGENT_ORDER.map((a) => [a, { agent: a, jobs: 0, files: new Set<number>(), slips: 0, first: Infinity }]),
  );
  for (const e of events) {
    const row = s[e.agent];
    if (!row) continue;
    if (e.event === "run_end") {
      row.jobs += 1;
      row.first = Math.min(row.first, e.index);
      if (e.ticket_id != null) row.files.add(e.ticket_id);
    }
    if (e.event === "run_error") row.slips += 1;
  }
  return Object.values(s)
    .sort((a, b) => b.jobs - a.jobs || a.slips - b.slips || a.first - b.first)
    .map((r) => ({ agent: r.agent as AgentName, jobs: r.jobs, files: r.files.size, slips: r.slips }));
}

/** A framed portrait on the wall, with a little brass plaque. */
export function EmployeeOfTheMonth({ events }: { events: AgentEvent[] }) {
  const [top, runnerUp] = tally(events);
  const won = top && top.jobs > 0;
  const meta = won ? AGENTS[top.agent] : null;

  return (
    <section className="eotm" style={{ ["--agent" as string]: meta?.color ?? "#9c8b72" }}>
      <div className="eotm-frame">
        <div className="eotm-portrait">
          {won ? <Avatar agent={top.agent} size={64} /> : <span className="eotm-empty">?</span>}
        </div>
        <div className="eotm-plaque">
          <div className="eotm-label">Employee of the Month</div>
          <div className="eotm-name">{won ? `${meta!.name} · ${meta!.role}` : "Position open"}</div>
        </div>
      </div>
      <p className="hand small eotm-note">
        {won
          ? `${top.jobs} job${top.jobs === 1 ? "" : "s"} done on ${top.files} file${top.files === 1 ? "" : "s"}, ${
              top.slips ? `${top.slips} slip${top.slips === 1 ? "" : "s"}` : "zero dropped balls"
            }.${runnerUp && runnerUp.jobs ? ` ${AGENTS[runnerUp.agent].name} is right behind.` : ""}`
          : "Hand Ron a file. Someone's going to earn this frame."}
      </p>
    </section>
  );
}
