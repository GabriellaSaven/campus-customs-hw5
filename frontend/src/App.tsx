import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { STATUS_LABEL, money } from "./agents";
import { describe, rosterFromEvents } from "./feed";
import type { AgentEvent, Briefing, Cash, Health, PaymentRequest, Queue, Run, Ticket, TicketDetail, TicketSummary } from "./types";
import { AgentRoster } from "./components/AgentRoster";
import { AgentSummaryPanel } from "./components/AgentSummaryPanel";
import { ApprovalQueue } from "./components/ApprovalQueue";
import { BoardPanel } from "./components/BoardPanel";
import { CashCard } from "./components/CashCard";
import { LiveFeed } from "./components/LiveFeed";
import { QuotesBoard } from "./components/QuotesBoard";
import { EmployeeOfTheMonth } from "./components/EmployeeOfTheMonth";
import { WaffleBreak } from "./components/WaffleBreak";
import { Whiteboard } from "./components/Whiteboard";
import { TicketBrief } from "./components/TicketBrief";
import { TicketRail } from "./components/TicketRail";

interface Toast {
  id: number;
  text: string;
  tone: "good" | "warn" | "bad";
}

const POLL_BOARD_MS = 4000;
const POLL_RUN_MS = 1200;

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [summary, setSummary] = useState<TicketSummary | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [cash, setCash] = useState<Cash | null>(null);
  const [queue, setQueue] = useState<Queue | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [allEvents, setAllEvents] = useState<AgentEvent[]>([]);
  const [offline, setOffline] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [approver, setApprover] = useState(() => localStorage.getItem("cc-approver") ?? "");
  const selectedRef = useRef<number | null>(null);
  selectedRef.current = selectedId;

  const toast = useCallback((text: string, tone: Toast["tone"] = "good") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5200);
  }, []);

  // ---- data loading -----------------------------------------------------
  const refreshBoard = useCallback(async () => {
    try {
      const [t, c, q, h, b, ev] = await Promise.all([
        api.tickets(),
        api.cash(),
        api.queue(),
        api.health(),
        api.briefing(),
        api.events({ limit: 500 }),
      ]);
      setTickets(t.tickets);
      setBriefing(b);
      setAllEvents(ev.events);
      setCash(c);
      setQueue(q);
      setHealth(h);
      setOffline(null);
      if (h.running) setRun((r) => (r?.run_id === h.running!.run_id ? r : h.running));
      return t.tickets;
    } catch (e) {
      setOffline((e as Error).message);
      return null;
    }
  }, []);

  const loadTicket = useCallback(async (id: number) => {
    try {
      const [d, s] = await Promise.all([api.ticket(id), api.summary(id)]);
      if (selectedRef.current !== id) return;
      setDetail(d);
      setSummary(s);
      const ev = s.run_id ? (await api.events({ runId: s.run_id })).events : [];
      if (selectedRef.current === id) setEvents(ev);
    } catch (e) {
      setOffline((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refreshBoard().then((t) => {
      if (!t?.length || selectedRef.current !== null) return;
      // Deep link: http://localhost:5173/#ticket=103 opens that file.
      const linked = Number(new URLSearchParams(location.hash.slice(1)).get("ticket"));
      setSelectedId(t.some((x) => x.id === linked) ? linked : t[0].id);
    });
    const timer = setInterval(refreshBoard, POLL_BOARD_MS);
    return () => clearInterval(timer);
  }, [refreshBoard]);

  useEffect(() => {
    if (selectedId !== null) loadTicket(selectedId);
  }, [selectedId, loadTicket]);

  // If the open file's status changes elsewhere (approval, close, reset), refresh the memo.
  const selectedStatus = tickets.find((t) => t.id === selectedId)?.status;
  useEffect(() => {
    if (selectedId !== null && detail && selectedStatus && detail.ticket.status !== selectedStatus) loadTicket(selectedId);
  }, [selectedStatus, selectedId, detail, loadTicket]);

  // ---- live run polling ------------------------------------------------
  const runningId = run?.status === "running" ? run.run_id : null;
  useEffect(() => {
    if (!runningId) return;
    let stopped = false;
    const tick = async () => {
      try {
        const [r, ev] = await Promise.all([api.run(runningId), api.events({ runId: runningId })]);
        if (stopped) return;
        if (selectedRef.current === r.ticket_id) setEvents(ev.events);
        if (r.status !== "running") {
          setRun(r);
          await refreshBoard();
          if (selectedRef.current !== null) await loadTicket(selectedRef.current);
          const d = r.result?.decision;
          if (r.status === "done" && d) toast(`File #${r.ticket_id}: Ron made the call. ${STATUS_LABEL[d.status]}.`);
          else toast(`File #${r.ticket_id}: the run stopped. ${r.error ?? "Unknown error."}`, "bad");
        }
      } catch {
        /* keep polling; the board poll reports offline state */
      }
    };
    tick();
    const timer = setInterval(tick, POLL_RUN_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [runningId, refreshBoard, loadTicket, toast]);

  // ---- actions -----------------------------------------------------------
  async function startRun() {
    if (selectedId === null) return;
    setBusy(true);
    try {
      const r = await api.runTicket(selectedId);
      setRun(r);
      setEvents([]);
      setSummary(null);
      toast(`File #${selectedId} is on Ron's desk.`);
      refreshBoard();
    } catch (e) {
      toast((e as Error).message, "bad");
    } finally {
      setBusy(false);
    }
  }

  async function approve(r: PaymentRequest): Promise<string | null> {
    try {
      const res = await api.approve(r.id, approver.trim());
      toast(`Paid ${money(res.amount)} to ${r.payee}. Checking is now ${money(res.balance_after)}.`);
      if (res.ticket_resolved) toast(`File #${res.ticket_id} closed. Nothing left waiting on you.`);
      await refreshBoard();
      if (selectedId !== null) loadTicket(selectedId);
      return null;
    } catch (e) {
      toast((e as Error).message, "bad");
      return (e as Error).message;
    }
  }

  async function reject(r: PaymentRequest): Promise<string | null> {
    try {
      await api.reject(r.id, approver.trim(), "Declined on the dashboard.");
      toast(`Declined ${money(r.amount)} to ${r.payee}. No money moved.`, "warn");
      await refreshBoard();
      if (selectedId !== null) loadTicket(selectedId);
      return null;
    } catch (e) {
      return (e as Error).message;
    }
  }

  async function resolve() {
    if (selectedId === null) return;
    setBusy(true);
    try {
      await api.resolve(selectedId, approver.trim());
      toast(`File #${selectedId} closed and initialed by ${approver.trim()}.`);
      await refreshBoard();
      loadTicket(selectedId);
    } catch (e) {
      toast((e as Error).message, "bad");
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    if (!window.confirm("Start a fresh day? The shop goes back to its original data: payments, requests, drafts and notes made since are wiped. The audit trail is kept.")) return;
    setBusy(true);
    try {
      await api.reset();
      setRun(null);
      setEvents([]);
      setSummary(null);
      await refreshBoard();
      if (selectedId !== null) loadTicket(selectedId);
      toast("Fresh day at the desk. The shop is back to its original data.", "warn");
    } catch (e) {
      toast((e as Error).message, "bad");
    } finally {
      setBusy(false);
    }
  }

  async function pinNote(note: string): Promise<string | null> {
    if (selectedId === null) return "Pick a file first.";
    try {
      await api.addNote(selectedId, approver.trim(), note);
      toast(`Pinned a note on file #${selectedId}. The team will see it next time.`);
      loadTicket(selectedId);
      return null;
    } catch (e) {
      return (e as Error).message;
    }
  }

  function changeApprover(name: string) {
    setApprover(name);
    localStorage.setItem("cc-approver", name);
  }

  // ---- derived -----------------------------------------------------------
  const roster = useMemo(() => rosterFromEvents(events), [events]);
  const liveRun = run?.status === "running" ? run : null;
  const showingLive = !!liveRun && liveRun.ticket_id === selectedId;
  const now = events.length ? describe(events[events.length - 1]) : liveRun ? "Ron is reading the file" : null;

  return (
    <div className={`app ${new URLSearchParams(location.hash.slice(1)).get("expand") ? "expanded" : ""}`}>
      <header className="topbar">
        <div className="plaque">
          <span className="plaque-small">Department of</span>
          <span className="plaque-big">Campus Customs</span>
          <span className="plaque-small">Operations Desk</span>
        </div>
        <div className="topbar-mid">
          <span className="desk-calendar" title="desk.date_today — the shop's 'today'">
            <span className="cal-month">{cash ? new Date(cash.as_of + "T12:00").toLocaleString("en-US", { month: "short" }) : "—"}</span>
            <span className="cal-day">{cash ? Number(cash.as_of.slice(8, 10)) : "—"}</span>
          </span>
          <span className="meta">
            Shop date <b>{cash?.as_of ?? "—"}</b>
          </span>
          <span className="meta">
            Everyone runs on <b>{health?.model ?? "—"}</b>
          </span>
          <span className={`conn ${offline ? "down" : "up"}`}>{offline ? "Backend's out" : "Lights on"}</span>
        </div>
        <button className="btn ghost light" onClick={reset} disabled={busy || !!liveRun}>
          Start a fresh day
        </button>
      </header>

      {offline && <div className="offline-bar">{offline} Turn it on with: <code>uvicorn main:app --reload --port 8000</code> from <code>backend/</code>.</div>}

      <Whiteboard briefing={briefing} />

      <main className="layout">
        <aside className="col left">
          <TicketRail tickets={tickets} selectedId={selectedId} runningId={liveRun?.ticket_id ?? null} onSelect={setSelectedId} />
          <AgentRoster roster={roster} live={showingLive} />
          <EmployeeOfTheMonth events={allEvents} />
          <QuotesBoard />
        </aside>

        <section className="col center">
          <TicketBrief
            detail={detail}
            run={run}
            anyRunning={!!liveRun}
            approver={approver.trim()}
            onRun={startRun}
            onResolve={resolve}
            busy={busy}
          />
          <LiveFeed events={events} running={showingLive} now={now} />
          <AgentSummaryPanel summary={summary} />
        </section>

        <aside className="col right">
          <CashCard cash={cash} />
          <ApprovalQueue
            requests={queue?.requests ?? []}
            balance={cash?.balance ?? null}
            approver={approver}
            onApproverChange={changeApprover}
            onApprove={approve}
            onReject={reject}
          />
          <BoardPanel detail={detail} approver={approver.trim()} onPin={pinNote} />
        </aside>
      </main>

      <WaffleBreak allClear={tickets.length ? tickets.every((t) => !t.is_open) : null} />

      <div className="toasts">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.tone}`}>
            {t.text}
          </div>
        ))}
      </div>
    </div>
  );
}
