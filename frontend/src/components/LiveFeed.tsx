import { useEffect, useRef } from "react";
import { AGENTS, STATUS_LABEL } from "../agents";
import { describe, toolVerb } from "../feed";
import type { AgentEvent, TicketStatus } from "../types";
import { Avatar } from "./Avatar";

function ToolChips({ e }: { e: AgentEvent }) {
  const calls = (e.tool_calls ?? []).filter((c) => c.tool !== "ask_agent");
  if (!calls.length) return null;
  return (
    <div className="chips">
      {calls.map((c) => (
        <span key={c.call_id} className="chip" title={`${c.tool}(${JSON.stringify(c.args)})`}>
          <span className="chip-verb">{toolVerb(c.tool)}</span>
          <span className="chip-tool">{c.tool}</span>
        </span>
      ))}
    </div>
  );
}

function pretty(s: string) {
  try {
    return JSON.stringify(JSON.parse(s), null, 2);
  } catch {
    return s;
  }
}

function Results({ e }: { e: AgentEvent }) {
  const results = (e.results ?? []).filter((r) => r.tool !== "ask_agent");
  if (!results.length) return null;
  return (
    <details className="carbon" style={{ marginLeft: e.depth * 30 + 50 }}>
      <summary>carbon copy · {results.map((r) => r.tool).join(", ")}</summary>
      {results.map((r) => (
        <pre key={r.call_id}>
          <b>{r.tool}</b>
          {"\n"}
          {pretty(r.result)}
        </pre>
      ))}
    </details>
  );
}

function FeedItem({ e }: { e: AgentEvent }) {
  const meta = AGENTS[e.agent];
  const indent = { marginLeft: e.depth * 30 };

  if (e.event === "run_start") {
    if (e.depth > 0) return null; // the routing slip already shows this
    return (
      <div className="feed-divider" style={indent}>
        <span /> {describe(e)} · {new Date(e.timestamp).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} <span />
      </div>
    );
  }

  if (e.event === "delegation" && e.to) {
    const to = AGENTS[e.to];
    return (
      <div className="routing-slip" style={indent}>
        <div className="slip-head">
          <span className="slip-label">Routing slip</span>
          <Avatar agent={e.agent} size={22} />
          <span className="slip-arrow" style={{ ["--from" as string]: meta.color, ["--to" as string]: to.color }} />
          <Avatar agent={e.to} size={22} />
          <span className="slip-names">
            {meta.name} → {to.name}
          </span>
        </div>
        <q>{e.said}</q>
      </div>
    );
  }

  if (e.event === "delegation_cached" || e.event === "delegation_refused") {
    return (
      <div className="feed-guard" style={indent}>
        {describe(e)}
        {e.reason ? ` — ${e.reason}` : ""}
      </div>
    );
  }

  if (e.event === "tool_results") return <Results e={e} />;

  if (e.event === "run_error") {
    return (
      <div className="card card-error" style={indent}>
        <b>{meta.name} had to stop:</b> {e.said}
      </div>
    );
  }

  if (e.event === "run_end" && e.depth === 0 && e.agent === "boss") {
    const out = (e.output ?? {}) as { status?: TicketStatus; decision?: string; waiting_on_human?: string[] };
    return (
      <div className="decision">
        <div className="decision-letterhead">
          <Avatar agent="boss" size={32} />
          <div>
            <div className="decision-from">From the desk of Ron</div>
            <div className="hand small">{e.tokens_so_far?.toLocaleString()} tokens, whole team</div>
          </div>
          {out.status && <span className={`stamp-inline stamp-${out.status}`}>{STATUS_LABEL[out.status]}</span>}
        </div>
        <p className="decision-body">{out.decision}</p>
        {!!out.waiting_on_human?.length && (
          <ul className="decision-todo">
            {out.waiting_on_human.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (e.event === "run_end") {
    const boss = AGENTS[e.chain[e.chain.length - 2]];
    return (
      <div className="msg" style={indent}>
        <Avatar agent={e.agent} />
        <div className="card reply" style={{ background: meta.tint, ["--agent" as string]: meta.color }}>
          <div className="card-who" style={{ color: meta.color }}>
            {meta.name} <span className="card-sub">reports back to {boss?.name ?? "the team"}</span>
          </div>
          <div className={`voice voice-${e.agent}`}>{e.said}</div>
        </div>
      </div>
    );
  }

  if (e.event === "model_response") {
    const hasTools = (e.tool_calls ?? []).some((c) => c.tool !== "ask_agent");
    if (!e.said && !hasTools) return null; // only walk-overs: the routing slips show those
    return (
      <div className="msg" style={indent}>
        <Avatar agent={e.agent} />
        <div className="card" style={{ background: meta.tint, ["--agent" as string]: meta.color }}>
          <div className="card-who" style={{ color: meta.color }}>
            {meta.name} <span className="card-sub">{meta.speaks}</span>
          </div>
          {e.said && <div className={`voice voice-${e.agent}`}>{e.said}</div>}
          <ToolChips e={e} />
        </div>
      </div>
    );
  }
  return null;
}

/** The bullpen: everyone's notes, handoffs and the final call, in order. */
export function LiveFeed({ events, running, now }: { events: AgentEvent[]; running: boolean; now: string | null }) {
  const end = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 160;
    if (nearBottom || running) end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length, running]);

  return (
    <section className="bullpen">
      <header className="section-title">
        <h2>The bullpen</h2>
        {running && now && (
          <span className="ticker">
            <span className="typing">
              <i />
              <i />
              <i />
            </span>
            {now}
          </span>
        )}
      </header>
      <div className="feed" ref={box}>
        {events.length === 0 ? (
          <div className="empty">
            <div className="empty-mug">☕</div>
            <p className="hand">Quiet in here. Nobody's touched this file yet.</p>
            <p className="small muted">Hand it to Ron and you'll see every walk-over, every lookup and the final call.</p>
          </div>
        ) : (
          events.map((e) => <FeedItem key={e.index} e={e} />)
        )}
        <div ref={end} />
      </div>
    </section>
  );
}
