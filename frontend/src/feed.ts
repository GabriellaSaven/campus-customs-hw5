import { AGENTS, AGENT_ORDER, TOOL_VERBS } from "./agents";
import type { AgentEvent, AgentName } from "./types";

export type AgentState = "idle" | "working" | "waiting" | "done" | "error";

export interface RosterEntry {
  state: AgentState;
  detail: string;
}

const verb = (tool: string) => TOOL_VERBS[tool] ?? tool.replaceAll("_", " ");

/** Replay a run's events to work out what each agent is doing right now. */
export function rosterFromEvents(events: AgentEvent[]): Record<AgentName, RosterEntry> {
  const roster = Object.fromEntries(
    AGENT_ORDER.map((a) => [a, { state: "idle", detail: AGENTS[a].idle }]),
  ) as Record<AgentName, RosterEntry>;

  for (const e of events) {
    const me = roster[e.agent];
    if (!me) continue;
    switch (e.event) {
      case "run_start":
        roster[e.agent] = {
          state: "working",
          detail: e.depth === 0 ? "Picked up the file" : `${AGENTS[e.chain[e.chain.length - 2]]?.name ?? "Someone"} stopped by`,
        };
        break;
      case "model_response": {
        const tools = (e.tools ?? []).filter((t) => t !== "ask_agent");
        if (tools.length) roster[e.agent] = { state: "working", detail: cap(verb(tools[tools.length - 1])) };
        break;
      }
      case "delegation":
        if (e.to) roster[e.agent] = { state: "waiting", detail: `Waiting on ${AGENTS[e.to].name}` };
        break;
      case "tool_results":
        if ((e.tools ?? []).includes("ask_agent")) roster[e.agent] = { state: "working", detail: "Got an answer, back at it" };
        break;
      case "run_end":
        roster[e.agent] = { state: "done", detail: "Done. Back at their desk." };
        break;
      case "run_error":
        roster[e.agent] = { state: "error", detail: "Stopped with an error" };
        break;
    }
  }
  return roster;
}

/** One plain-English line for the "right now" ticker. */
export function describe(e: AgentEvent): string {
  const who = AGENTS[e.agent]?.name ?? e.agent;
  switch (e.event) {
    case "run_start":
      return e.depth === 0 ? `${who} picked up file #${e.ticket_id}` : `${who} is on it`;
    case "model_response": {
      const tools = (e.tools ?? []).filter((t) => t !== "ask_agent");
      return tools.length ? `${who} ${tools.map(verb).join(", ")}` : `${who} is thinking`;
    }
    case "tool_results":
      return `${who} got results back`;
    case "delegation":
      return `${who} walked over to ${e.to ? AGENTS[e.to].name : "a teammate"}'s desk`;
    case "delegation_cached":
      return `${who} reused an earlier answer`;
    case "delegation_refused":
      return `${who}'s handoff was declined (guardrail)`;
    case "run_end":
      return e.depth === 0 ? `${who} made the call` : `${who} reported back`;
    case "run_error":
      return `${who} hit an error`;
    default:
      return `${who}: ${e.event}`;
  }
}

export const toolVerb = verb;

function cap(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
