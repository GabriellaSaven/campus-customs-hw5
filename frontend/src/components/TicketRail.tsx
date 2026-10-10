import { STATUS_LABEL } from "../agents";
import type { Ticket } from "../types";

const TYPE_LABEL: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Price override",
};

function ticketLine(t: Ticket) {
  if (t.sku) return `${t.qty ?? "?"} × ${t.sku} · ${t.size}`;
  if (t.lease_id) return `Lease #${t.lease_id}`;
  return t.notes ?? "";
}

interface Props {
  tickets: Ticket[];
  selectedId: number | null;
  runningId: number | null;
  onSelect: (id: number) => void;
}

/** The filing cabinet: one manila folder per ticket, tab sticking up. */
export function TicketRail({ tickets, selectedId, runningId, onSelect }: Props) {
  const open = tickets.filter((t) => t.is_open).length;
  return (
    <section className="cabinet">
      <header className="section-title">
        <h2>The filing cabinet</h2>
        <span className="hand small">
          {open} open · {tickets.length - open} done
        </span>
      </header>
      <div className="folders">
        {tickets.map((t, i) => (
          <button
            key={t.id}
            className={`folder status-${t.status} ${t.id === selectedId ? "selected" : ""}`}
            onClick={() => onSelect(t.id)}
            style={{ ["--tab-offset" as string]: `${14 + i * 64}px` }}
          >
            <span className="folder-tab">#{t.id}</span>
            <div className="folder-body">
              <div className="folder-subject">{t.subject}</div>
              <div className="folder-meta">
                {TYPE_LABEL[t.type] ?? t.type} · {t.requester}
              </div>
              <div className="folder-line">{ticketLine(t)}</div>
              <span className={`sticker sticker-${t.status}`}>
                {t.id === runningId ? "Team's on it…" : STATUS_LABEL[t.status]}
              </span>
            </div>
            {t.id === runningId && <div className="folder-progress" />}
            {t.status === "resolved" && <div className="stamp">Resolved</div>}
          </button>
        ))}
      </div>
    </section>
  );
}
