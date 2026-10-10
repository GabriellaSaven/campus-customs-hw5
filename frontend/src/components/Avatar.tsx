import { AGENTS } from "../agents";
import type { AgentName } from "../types";

/** A little ID-badge photo circle: the person's initial on their color. */
export function Avatar({ agent, size = 34 }: { agent: AgentName; size?: number }) {
  const meta = AGENTS[agent];
  return (
    <span
      className={`avatar avatar-${agent}`}
      style={{ width: size, height: size, background: meta.color, fontSize: size * 0.46 }}
      title={`${meta.name} · ${meta.role}`}
    >
      {meta.mono}
    </span>
  );
}
