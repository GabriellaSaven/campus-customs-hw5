import { useState } from "react";
import { AGENTS, money } from "../agents";
import type { AgentName, TicketDetail } from "../types";

const HUMAN_MARK = "[From the human desk]";

interface Props {
  detail: TicketDetail | null;
  approver: string;
  onPin: (note: string) => Promise<string | null>;
}

/** The corkboard: drafts and notes pinned up for this file, plus the suggestion box. Nothing here is sent. */
export function BoardPanel({ detail, approver, onPin }: Props) {
  const [text, setText] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  if (!detail) return null;
  const { drafts, notes } = detail.board;

  async function pin() {
    setSaving(true);
    const e = await onPin(text.trim());
    setErr(e);
    if (!e) setText("");
    setSaving(false);
  }

  return (
    <section className="corkboard">
      <header className="section-title on-cork">
        <h2>The corkboard</h2>
        <span className="hand small">drafts stay pinned · nothing gets sent</span>
      </header>
      {!drafts.length && !notes.length && <p className="hand cork-empty">Nothing pinned for file #{detail.ticket.id} yet.</p>}
      <div className="pins">
        {drafts.map((d, i) => {
          const author = AGENTS[d.author as AgentName];
          return (
            <div key={d.id} className={`pinned draft-${d.kind}`} style={{ ["--tilt" as string]: `${i % 2 ? 1.2 : -1}deg` }}>
              <span className="pin" />
              <div className="pinned-kind">{d.kind === "customer_message" ? "Draft letter" : "Draft purchase order"}</div>
              <div className="pinned-subject">{d.subject}</div>
              <div className="small muted">
                to {d.recipient} · by {author?.name ?? d.author}
                {d.total != null && <> · {money(d.total)}</>} · {d.status}
              </div>
            </div>
          );
        })}
        {notes.map((n, i) => {
          const author = AGENTS[n.author as AgentName];
          const human = n.note.startsWith(HUMAN_MARK);
          return (
            <div
              key={i}
              className={`sticky ${human ? "from-human" : ""}`}
              style={{ ["--tilt" as string]: `${[-1.4, 1, -0.6, 1.5][i % 4]}deg` }}
            >
              <b style={{ color: author?.color ?? "#3a2c1a" }}>{author?.name ?? n.author}:</b>{" "}
              {human ? n.note.slice(HUMAN_MARK.length).trim() : n.note}
            </div>
          );
        })}
      </div>

      <div className="suggestion-box">
        <div className="sb-slot" aria-hidden />
        <label className="hand small" htmlFor="suggestion">
          Suggestion box: pin a note for the team on file #{detail.ticket.id}
        </label>
        <textarea
          id="suggestion"
          rows={2}
          maxLength={500}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Offer the sizes we do have in stock."
        />
        {err && <div className="check-warn">{err}</div>}
        <div className="sb-row">
          <span className="hand small">
            {approver ? (
              <>
                signed, <span className="script">{approver}</span>
              </>
            ) : (
              "Sign your name on the clipboard first."
            )}
          </span>
          <button className="btn ghost small" disabled={!approver || !text.trim() || saving} onClick={pin}>
            {saving ? "Pinning…" : "Pin it up"}
          </button>
        </div>
        <p className="hand small sb-fine">The team reads it next time they work this file. It never overrides shop rules.</p>
      </div>
    </section>
  );
}
