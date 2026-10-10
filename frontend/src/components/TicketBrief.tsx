import { STATUS_LABEL } from "../agents";
import type { Run, TicketDetail } from "../types";

interface Props {
  detail: TicketDetail | null;
  run: Run | null;
  anyRunning: boolean;
  approver: string;
  onRun: () => void;
  onResolve: () => void;
  busy: boolean;
}

/** The open ticket, typed up as an inter-office memo. */
export function TicketBrief({ detail, run, anyRunning, approver, onRun, onResolve, busy }: Props) {
  if (!detail) {
    return (
      <section className="memo">
        <p className="hand">Pull a folder from the cabinet to get started.</p>
      </section>
    );
  }
  const t = detail.ticket;
  const running = run?.status === "running" && run.ticket_id === t.id;
  const pending = detail.board.payment_requests.filter((r) => r.status === "pending").length;
  const canResolve = !running && t.status !== "resolved" && t.status !== "open" && pending === 0;
  const finished = run && run.ticket_id === t.id && run.status !== "running";

  return (
    <section className={`memo status-${t.status}`}>
      <div className="memo-top">
        <div className="memo-title">Memorandum</div>
        <div className="memo-file">File #{t.id}</div>
      </div>
      <dl className="memo-fields">
        <dt>To</dt>
        <dd>The Campus Customs team</dd>
        <dt>From</dt>
        <dd>{t.requester}</dd>
        <dt>Date</dt>
        <dd>{t.created_at.slice(0, 10)}</dd>
        <dt>Re</dt>
        <dd className="memo-re">{t.subject}</dd>
      </dl>
      <div className="memo-body">
        <p>“{t.notes}”</p>
        <div className="facts">
          {t.sku && (
            <span className="fact">
              {t.qty} × {t.sku} · size {t.size}
            </span>
          )}
          {t.lease_id && <span className="fact">Lease #{t.lease_id}</span>}
          {t.invoice_id && <span className="fact">Linked invoice #{t.invoice_id}</span>}
          <span className="fact">{t.type.replaceAll("_", " ")}</span>
        </div>
      </div>

      <div className="memo-actions">
        <button className="btn primary" onClick={onRun} disabled={anyRunning || busy}>
          {running ? "Ron's on it…" : t.status === "open" ? "Hand it to Ron →" : "Run it by the team again"}
        </button>
        {canResolve && (
          <button
            className="btn ghost"
            onClick={onResolve}
            disabled={!approver || busy}
            title={approver ? "" : "Sign your name on the clipboard first"}
          >
            Close the file
          </button>
        )}
        {anyRunning && !running && <span className="hand small">Another file is on Ron's desk right now.</span>}
        <span className={`stamp-inline stamp-${t.status}`}>{STATUS_LABEL[t.status]}</span>
      </div>

      {finished && (
        <div className={`run-banner ${run.status}`}>
          {run.status === "done" ? "✓ The team's done with this one" : "⚠ The run stopped"}
          {run.result?.usage && (
            <>
              {" "}· {run.result.usage.total_tokens.toLocaleString()} tokens · {run.result.usage.requests} model calls
            </>
          )}
          {run.error && <> · {run.error}</>}
          {run.status === "done" && t.status !== "resolved" && pending > 0 && <> · it just needs your signature on the clipboard →</>}
        </div>
      )}
    </section>
  );
}
