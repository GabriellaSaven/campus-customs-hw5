import { useState } from "react";
import { AGENTS, money } from "../agents";
import type { AgentName, PaymentRequest } from "../types";
import { Avatar } from "./Avatar";

const KIND_LABEL: Record<PaymentRequest["kind"], string> = {
  invoice: "Vendor invoice",
  rent: "Rent",
  purchase_order: "Purchase order",
};

interface Props {
  requests: PaymentRequest[];
  balance: number | null;
  approver: string;
  onApproverChange: (name: string) => void;
  onApprove: (r: PaymentRequest) => Promise<string | null>;
  onReject: (r: PaymentRequest) => Promise<string | null>;
}

/** The clipboard: everything waiting on a human signature. */
export function ApprovalQueue({ requests, balance, approver, onApproverChange, onApprove, onReject }: Props) {
  const [errors, setErrors] = useState<Record<number, string>>({});
  const [working, setWorking] = useState<number | null>(null);

  async function act(r: PaymentRequest, fn: (r: PaymentRequest) => Promise<string | null>) {
    setWorking(r.id);
    const err = await fn(r);
    setErrors((e) => ({ ...e, [r.id]: err ?? "" }));
    setWorking(null);
  }

  return (
    <section className="clipboard">
      <div className="clip" />
      <header className="section-title">
        <h2>Needs your signature</h2>
        <span className={`count ${requests.length ? "has" : ""}`}>{requests.length}</span>
      </header>

      <label className="signature">
        <span className="hand small">Sign here (your name goes on every payment)</span>
        <input value={approver} onChange={(e) => onApproverChange(e.target.value)} placeholder="Your name" spellCheck={false} />
      </label>

      {requests.length === 0 ? (
        <p className="hand empty-queue">Nothing to sign. The team prepares payments here; only you can pay them.</p>
      ) : (
        <ul className="checks">
          {requests.map((r) => {
            const short = balance !== null && r.amount > balance;
            const prepper = AGENTS[r.requested_by as AgentName];
            return (
              <li key={r.id} className="check">
                <div className="check-top">
                  <span className="check-kind">{KIND_LABEL[r.kind]}</span>
                  <span className="check-no">No. {String(r.id).padStart(4, "0")}</span>
                </div>
                <div className="check-pay">
                  <span className="check-label">Pay to</span>
                  <b>{r.payee}</b>
                  <span className="check-amount">{money(r.amount)}</span>
                </div>
                <div className="check-memo">
                  <span className="check-label">Memo</span> {r.reason || "—"}
                  {r.ticket_id && <> · file #{r.ticket_id}</>}
                </div>
                <div className="check-by">
                  {prepper && <Avatar agent={r.requested_by as AgentName} size={18} />} prepared by {prepper?.name ?? r.requested_by}
                </div>
                {short && <div className="check-warn">Not enough in checking. The pay tool will refuse this one.</div>}
                {errors[r.id] && <div className="check-warn">{errors[r.id]}</div>}
                <div className="check-actions">
                  <button
                    className="btn pay"
                    disabled={!approver.trim() || working !== null}
                    onClick={() => act(r, onApprove)}
                    title={approver.trim() ? "" : "Sign your name above first"}
                  >
                    {working === r.id ? "Paying…" : `Sign & pay ${money(r.amount)}`}
                  </button>
                  <button className="btn ghost small" disabled={!approver.trim() || working !== null} onClick={() => act(r, onReject)}>
                    Decline
                  </button>
                </div>
                <div className="check-sigline">{approver.trim() && <span className="script">{approver}</span>}</div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
