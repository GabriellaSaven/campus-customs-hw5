import { useEffect, useRef, useState } from "react";
import { money } from "../agents";
import type { Cash } from "../types";
import { Avatar } from "./Avatar";

/** Rolls the number from its old value to the new one, like an adding machine. */
function useRolling(target: number | undefined, ms = 1100) {
  const [value, setValue] = useState(target ?? 0);
  const from = useRef<number | null>(target ?? null);
  useEffect(() => {
    if (target === undefined) return;
    if (from.current === null) {
      // First real balance: show it as-is, only animate later changes.
      from.current = target;
      setValue(target);
      return;
    }
    const start = performance.now();
    const begin = from.current;
    let frame = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(begin + (target - begin) * eased);
      if (p < 1) frame = requestAnimationFrame(tick);
      else from.current = target;
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, ms]);
  return value;
}

/** The ledger: Ben's checking account page. */
export function CashCard({ cash }: { cash: Cash | null }) {
  const shown = useRolling(cash?.balance);
  const prev = useRef<number | null>(null);
  const [delta, setDelta] = useState<number | null>(null);

  useEffect(() => {
    if (cash === null) return;
    if (prev.current !== null && cash.balance !== prev.current) {
      setDelta(cash.balance - prev.current);
      const t = setTimeout(() => setDelta(null), 4000);
      prev.current = cash.balance;
      return () => clearTimeout(t);
    }
    prev.current = cash.balance;
  }, [cash]);

  if (!cash) return <section className="ledger">Opening the ledger…</section>;
  const pendingPct = cash.balance > 0 ? Math.min(100, (cash.pending_requests_total / cash.balance) * 100) : 0;
  const over = cash.available_after_pending < 0;

  return (
    <section className={`ledger ${delta && delta < 0 ? "dropped" : ""}`}>
      <div className="ledger-head">
        <div>
          <div className="ledger-title">Checking</div>
          <div className="hand small">kept by Ben · as of {cash.as_of}</div>
        </div>
        <Avatar agent="accounting" size={28} />
      </div>
      <div className="ledger-amount">
        {money(shown)}
        {delta !== null && (
          <span className={`ledger-delta ${delta < 0 ? "down" : "up"}`}>
            {delta < 0 ? "−" : "+"}
            {money(Math.abs(delta))}
          </span>
        )}
      </div>
      <div className="ledger-bar" title="Share of cash already promised to pending requests">
        <span className={`ledger-bar-fill ${over ? "over" : ""}`} style={{ width: `${pendingPct}%` }} />
      </div>
      <div className="ledger-rows">
        <div>
          <span>Promised to pending requests</span>
          <b>{money(cash.pending_requests_total)}</b>
        </div>
        <div className={over ? "neg" : ""}>
          <span>Left after you sign them</span>
          <b>{money(cash.available_after_pending)}</b>
        </div>
      </div>
      <div className="hand small ledger-note">Money only goes out this term. No revenue. Ben is aware.</div>
    </section>
  );
}
