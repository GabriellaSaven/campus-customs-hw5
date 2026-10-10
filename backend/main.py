"""FastAPI backend for the Campus Customs dashboard.

Start it from the backend/ folder:

    uvicorn main:app --reload --port 8000

Every shop fact and every change goes through the MCP server (one connection,
opened when the app starts). Agents only *prepare* payments; the approve route
below is the only thing that moves cash, and it needs a named human.
"""

import asyncio
import json
from collections import Counter
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal

# Allow `uvicorn main:app` from inside backend/ as well as `backend.main:app` from the root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from backend.agents import CampusCustomsTeam, new_run_id  # noqa: E402
from backend.config import AUDIT_PATH, MODEL_NAME  # noqa: E402

team: CampusCustomsTeam | None = None
runs: dict[str, dict] = {}  # run_id -> status/result, newest last
run_lock = asyncio.Lock()  # one agent run at a time (keeps cash decisions in order, caps spend)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global team
    async with CampusCustomsTeam() as t:  # starts the MCP server once
        team = t
        yield
        for r in runs.values():
            if (task := r.get("_task")) and not task.done():
                task.cancel()
    team = None


app = FastAPI(title="Campus Customs Agent Desk", version="1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # the Vite dashboard (npm run dev)
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",  # ...and Vite's fallback ports
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------- helpers


def _team() -> CampusCustomsTeam:
    if team is None:
        raise HTTPException(503, "Agent team is not ready yet.")
    return team


def _check(result: dict) -> dict:
    """Turn an MCP tool's {'error': ...} into a proper HTTP error."""
    if isinstance(result, dict) and "error" in result:
        status = 404 if "not found" in result["error"].lower() else 400
        raise HTTPException(status, result)
    return result


def _public(run: dict) -> dict:
    return {k: v for k, v in run.items() if not k.startswith("_")}


def _busy() -> dict | None:
    return next((r for r in runs.values() if r["status"] == "running"), None)


def _summarize(index: int, e: dict) -> dict:
    """Reshape one audit entry into what the board shows: who, what they said, which tools."""
    d = e.get("detail") or {}
    out = {
        "index": index,
        "timestamp": e["timestamp"],
        "run_id": e["run_id"],
        "ticket_id": e["ticket_id"],
        "agent": e["agent"],
        "depth": e["depth"],
        "chain": e["chain"],
        "step": e["step"],
        "event": e["event"],
        "tokens_so_far": (e.get("usage") or {}).get("total_tokens"),
    }
    ev = e["event"]
    if ev == "run_start":
        out["said"] = d.get("user_prompt")
        out["model"] = e.get("model")
    elif ev == "model_response":
        calls = [c for c in d.get("tool_calls", []) if c["tool"] != "final_result"]
        out["said"] = d.get("text")
        out["tools"] = [c["tool"] for c in calls]
        out["tool_calls"] = calls
        out["model"] = e.get("model")
        out["provider_model"] = d.get("provider_model")
    elif ev == "tool_results":
        results = [r for r in d.get("results", []) if r["tool"] != "final_result"]
        out["tools"] = [r["tool"] for r in results]
        out["results"] = results
        out["retries"] = d.get("retries", [])
    elif ev.startswith("delegation"):
        out["to"] = d.get("to")
        out["said"] = d.get("question")
        out["reason"] = d.get("reason")
    elif ev == "run_end":
        output = d.get("output") or {}
        out["said"] = output.get("decision") or output.get("summary")
        out["output"] = output
    elif ev == "run_error":
        out["said"] = d.get("error")
    return out


NOISY_EVENTS = {"user_prompt", "model_request", "end"}


def _audit_entries() -> list[dict]:
    return json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []


def _last_reset_index(entries: list[dict]) -> int:
    """Index of the most recent shop reset in the trail (-1 if none)."""
    return max((i for i, e in enumerate(entries) if e["event"] == "shop_reset"), default=-1)


# ---------------------------------------------------------------------- routes


@app.get("/api/health")
async def health() -> dict:
    return {"ok": team is not None, "model": MODEL_NAME, "running": _public(r) if (r := _busy()) else None}


@app.get("/api/tickets")
async def list_tickets() -> dict:
    """(1) Every ticket with its status and whether it is open or resolved."""
    return _check(await _team().read("list_tickets"))


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: int) -> dict:
    """One ticket plus its board: notes, drafts and payment requests."""
    return _check(await _team().read("get_ticket", {"ticket_id": ticket_id}))


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int, wait: bool = False) -> dict:
    """(2) Run the agent team on one ticket. Returns at once with a run_id
    (poll /api/runs/{run_id} and /api/events); pass ?wait=true to block until done."""
    t = _team()
    _check(await t.read("get_ticket", {"ticket_id": ticket_id}))  # 404 if no such ticket
    if busy := _busy():
        raise HTTPException(409, {"error": "Another run is in progress.", "run": _public(busy)})

    run_id = new_run_id()
    run = {
        "run_id": run_id,
        "ticket_id": ticket_id,
        "status": "running",
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": None,
        "result": None,
        "error": None,
    }
    runs[run_id] = run

    async def work() -> None:
        async with run_lock:
            try:
                result = await t.run_ticket(ticket_id, run_id=run_id)
                run["result"] = result.model_dump()
                run["status"] = "error" if result.error else "done"
                run["error"] = result.error
            except Exception as exc:  # recorded in the audit trail too
                run["status"] = "error"
                run["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                run["finished_at"] = datetime.now().isoformat(timespec="seconds")

    run["_task"] = asyncio.create_task(work())
    if wait:
        await run["_task"]
    return _public(run)


@app.get("/api/runs")
async def list_runs() -> dict:
    return {"runs": [_public(r) for r in reversed(list(runs.values()))]}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    if run_id not in runs:
        raise HTTPException(404, {"error": f"Run {run_id} not found (runs are kept in memory until restart)."})
    return _public(runs[run_id])


@app.get("/api/events")
async def recent_events(
    limit: int = Query(50, ge=1, le=500),
    after: int | None = Query(None, description="Only events with index > after (for polling)."),
    ticket_id: int | None = None,
    run_id: str | None = None,
    verbose: bool = False,
    since_reset: bool = Query(True, description="Only events after the last shop reset."),
) -> dict:
    """(3) Recent agent events from output/audit_trail.json: who spoke, what they
    said, which tools they called and what came back. Newest last."""
    entries = _audit_entries()
    floor = _last_reset_index(entries) if since_reset else -1
    events = [
        _summarize(i, e)
        for i, e in enumerate(entries)
        if i > floor
        and e["event"] != "shop_reset"
        and (after is None or i > after)
        and (ticket_id is None or e["ticket_id"] == ticket_id)
        and (run_id is None or e["run_id"] == run_id)
        and (verbose or e["event"] not in NOISY_EVENTS)
    ]
    if not verbose:  # drop steps with nothing to show (e.g. the final-answer call; run_end has it)
        events = [
            ev for ev in events
            if ev["event"] not in ("model_response", "tool_results") or ev.get("tools") or ev.get("said")
        ]
    return {"total_in_file": len(entries), "last_index": len(entries) - 1, "events": events[-limit:]}


@app.get("/api/payment-requests")
async def payment_requests(status: Literal["pending", "paid", "rejected", "all"] = "pending") -> dict:
    """The human approval queue (what agents have prepared)."""
    return _check(await _team().read("list_payment_requests", {"status": status}))


class Approval(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human approving the payment.")


class Rejection(BaseModel):
    decided_by: str = Field(min_length=1)
    reason: str = ""


@app.post("/api/payment-requests/{request_id}/approve")
async def approve_payment(request_id: int, body: Approval) -> dict:
    """(4) A human approves a prepared payment or purchase order. This is the ONLY
    route that moves cash: it updates payments, cash_accounts and the invoice /
    lease / PO. Refused if cash is short, the approver is an agent, or the vendor is blocked.
    If that was the ticket's last pending approval and the Boss left it
    'awaiting_approval', the ticket is marked resolved (nothing is left for a human)."""
    t = _team()
    paid = _check(
        await t.human_call("pay_approved_request", {"request_id": request_id, "approved_by": body.approved_by})
    )
    queue = await t.read("list_payment_requests", {"status": "all"})
    ticket_id = next((r["ticket_id"] for r in queue["requests"] if r["id"] == request_id), None)
    paid["ticket_id"] = ticket_id
    paid["ticket_resolved"] = False
    if ticket_id is not None:
        detail = await t.read("get_ticket", {"ticket_id": ticket_id})
        still_pending = [r for r in detail["board"]["payment_requests"] if r["status"] == "pending"]
        if detail["ticket"]["status"] == "awaiting_approval" and not still_pending:
            res = await t.human_call(
                "resolve_ticket",
                {"ticket_id": ticket_id, "resolved_by": body.approved_by, "note": "All approvals done."},
            )
            paid["ticket_resolved"] = res.get("status") == "resolved"
    return paid


@app.post("/api/payment-requests/{request_id}/reject")
async def reject_payment(request_id: int, body: Rejection) -> dict:
    """A human turns a prepared payment down. No money moves."""
    return _check(
        await _team().human_call(
            "reject_payment_request",
            {"request_id": request_id, "decided_by": body.decided_by, "reason": body.reason},
        )
    )


class Resolution(BaseModel):
    resolved_by: str = Field(min_length=1, description="Name of the human closing the ticket.")
    note: str = ""


@app.post("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: int, body: Resolution) -> dict:
    """A human marks a reviewed ticket resolved (e.g. an escalated one). Refused while a payment is pending."""
    return _check(
        await _team().human_call(
            "resolve_ticket", {"ticket_id": ticket_id, "resolved_by": body.resolved_by, "note": body.note}
        )
    )


@app.get("/api/tickets/{ticket_id}/summary")
async def ticket_summary(ticket_id: int) -> dict:
    """A short per-agent summary of the latest team run on this ticket, built
    from the audit trail: who was asked, which tools they used, what they concluded."""
    entries = _audit_entries()
    floor = _last_reset_index(entries)
    starts = [
        e for i, e in enumerate(entries)
        if i > floor
        and e["ticket_id"] == ticket_id and e["event"] == "run_start" and e["depth"] == 0 and e["agent"] == "boss"
    ]
    if not starts:
        return {"ticket_id": ticket_id, "run_id": None, "agents": []}
    run_id = starts[-1]["run_id"]
    run = [e for e in entries if e["run_id"] == run_id]

    agents: dict[str, dict] = {}
    for e in run:
        a = agents.setdefault(
            e["agent"],
            {"agent": e["agent"], "asked_by": [], "asked": [], "tools": Counter(), "summary": None,
             "needs_human": None, "actions_taken": [], "open_questions": [], "output": None},
        )
        d = e.get("detail") or {}
        if e["event"] == "run_start" and len(e["chain"]) > 1:
            a["asked_by"].append(e["chain"][-2])
        elif e["event"] == "delegation":
            a["asked"].append(d.get("to"))
        elif e["event"] == "model_response":
            for c in d.get("tool_calls", []):
                if c["tool"] not in ("final_result", "ask_agent"):
                    a["tools"][c["tool"]] += 1
        elif e["event"] == "run_end":
            out = d.get("output") or {}
            a["output"] = out
            a["summary"] = out.get("decision") or out.get("summary")
            a["needs_human"] = out.get("needs_human", bool(out.get("waiting_on_human")))
            a["actions_taken"] = out.get("actions_taken") or out.get("drafts_created") or []
            a["open_questions"] = out.get("open_questions") or out.get("waiting_on_human") or []
    for a in agents.values():
        a["tools"] = dict(a["tools"])

    ended = [e for e in run if e["depth"] == 0 and e["event"] in ("run_end", "run_error")]
    return {
        "ticket_id": ticket_id,
        "run_id": run_id,
        "started_at": run[0]["timestamp"],
        "finished_at": ended[-1]["timestamp"] if ended else None,
        "status": ("done" if ended[-1]["event"] == "run_end" else "error") if ended else "running",
        "total_tokens": max(((e.get("usage") or {}).get("total_tokens") or 0) for e in run),
        "agents": list(agents.values()),
    }


class HumanNote(BaseModel):
    author: str = Field(min_length=1, description="The person pinning the note.")
    note: str = Field(min_length=1, max_length=500)


@app.post("/api/tickets/{ticket_id}/notes")
async def add_note(ticket_id: int, body: HumanNote) -> dict:
    """The suggestion box: a person pins a signed note to a ticket. Agents read it
    on the board the next time they work the ticket. It never overrides shop rules."""
    return _check(
        await _team().human_call("add_human_note", {"ticket_id": ticket_id, "author": body.author, "note": body.note})
    )


@app.get("/api/briefing")
async def briefing() -> dict:
    """The whiteboard: today's to-do list, computed from shop data through MCP
    (overdue invoices, blocked vendors, rent coming due, signatures waiting, cash)."""
    t = _team()
    today = (await t.read("get_today"))["date_today"]
    tickets = (await t.read("list_tickets"))["tickets"]
    vendors = (await t.read("list_vendors"))["vendors"]
    cash = await t.read("get_cash_position")
    queue = await t.read("list_payment_requests", {"status": "pending"})
    items: list[dict] = []

    for v in vendors:
        for inv_id in v["open_invoice_ids"]:
            inv = await t.read("get_invoice", {"invoice_id": inv_id})
            pending = any(r["status"] == "pending" for r in inv["payment_requests"])
            days = inv["days_overdue"]
            items.append({
                "tone": "red" if days else "amber",
                "text": f"{v['name']} is on hold: invoice #{inv_id} (${inv['amount']:,.2f}) "
                + (f"is {days} day{'s' if days != 1 else ''} overdue" if days else f"is due {inv['due_date']}")
                + (" · payment request waiting for you" if pending else "") + ".",
            })
    for lease_id in sorted({tk["lease_id"] for tk in tickets if tk["lease_id"] is not None}):
        lease = await t.read("get_lease_rent_status", {"lease_id": lease_id})
        d = lease["days_until_due"]
        when = f"{abs(d)} days overdue" if d < 0 else "today" if d == 0 else f"in {d} day{'s' if d != 1 else ''}"
        items.append({
            "tone": "red" if d < 0 else "amber" if d <= 3 else "green",
            "text": f"Rent for {lease['space_name']}: ${lease['monthly_rent']:,.2f} due {lease['next_due']} ({when}).",
        })
    if queue["count"]:
        items.append({
            "tone": "amber",
            "text": f"{queue['count']} check{'s' if queue['count'] != 1 else ''} on the clipboard "
            f"(${queue['pending_total']:,.2f}) waiting for your signature.",
        })
    checking = next((a for a in cash["accounts"] if a["name"] == "checking"), None)
    if checking and checking["overcommitted"]:
        items.append({
            "tone": "red",
            "text": f"Promised more than we have: checking would be ${checking['available_after_pending']:,.2f} after every pending request.",
        })
    open_files = [tk for tk in tickets if tk["is_open"]]
    if not open_files:
        items.append({"tone": "green", "text": "Every file is closed. Waffle break."})
    return {
        "today": today,
        "open_files": len(open_files),
        "untouched_files": sum(1 for tk in open_files if tk["status"] == "open"),
        "items": items,
    }


@app.get("/api/cash")
async def cash() -> dict:
    """(5) The current checking balance from cash_accounts (plus what's pending)."""
    pos = _check(await _team().read("get_cash_position"))
    checking = next((a for a in pos["accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, {"error": "No 'checking' account in cash_accounts."})
    return {
        "account": "checking",
        "balance": checking["balance"],
        "as_of": checking["date"],
        "pending_requests_total": checking["pending_requests_total"],
        "available_after_pending": checking["available_after_pending"],
        "accounts": pos["accounts"],
    }


@app.post("/api/reset")
async def reset() -> dict:
    """(6) Restore data/campus_customs_new.db from the original for a fresh run.
    The audit trail is kept (append-only) and gets a 'shop_reset' marker; the
    dashboard's events and summaries only look at runs after the latest marker."""
    if busy := _busy():
        raise HTTPException(409, {"error": "Can't reset while a run is in progress.", "run": _public(busy)})
    t = _team()
    result = _check(await t.human_call("reset_shop_database", {"confirm": True}))
    await t.audit.record_system("shop_reset", {"result": result})
    runs.clear()
    return result
