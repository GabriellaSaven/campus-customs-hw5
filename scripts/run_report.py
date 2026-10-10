"""Collect the facts of the latest full run (since the last shop reset).

Sources (no direct database access, no AI calls):
- output/audit_trail.json  -> who worked, who delegated to whom, which tools each agent used
- the FastAPI backend       -> tickets, boards, payment requests, cash (all read through MCP)

Writes output/resolved_tickets.json and returns the same data for the HTML builder.
Usage:  .venv/bin/python scripts/run_report.py   (backend must be running on :8000)
"""

import json
import urllib.request
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "output" / "audit_trail.json"
OUT = ROOT / "output" / "resolved_tickets.json"
API = "http://localhost:8000/api"
NAMES = {"boss": "Ron (Boss)", "inventory": "April (Inventory)", "accounting": "Ben (Accounting)",
         "facilities": "Chris (Facilities)", "customer_service": "Leslie (Customer Service)"}


def get(path: str):
    with urllib.request.urlopen(f"{API}{path}") as r:
        return json.load(r)


def collect() -> dict:
    entries = json.loads(AUDIT.read_text())
    reset_idx = max(i for i, e in enumerate(entries) if e["event"] == "shop_reset")
    reset = entries[reset_idx]
    start_cash = next(a["balance"] for a in reset["detail"]["result"]["cash"] if a["name"] == "checking")
    since = entries[reset_idx + 1:]

    requests = get("/payment-requests?status=all")["requests"]
    cash = get("/cash")
    tickets = {t["id"]: t for t in get("/tickets")["tickets"]}

    out_tickets = []
    for tid in sorted(tickets):
        starts = [e for e in since if e["ticket_id"] == tid and e["event"] == "run_start" and e["depth"] == 0]
        run_id = starts[-1]["run_id"]
        run = [e for e in since if e["run_id"] == run_id]

        agents: "OrderedDict[str, dict]" = OrderedDict()
        delegations = []
        for e in run:
            a = agents.setdefault(e["agent"], {"agent": e["agent"], "name": NAMES[e["agent"]], "asked_by": [],
                                               "tools": Counter(), "summary": None, "actions_taken": []})
            d = e.get("detail") or {}
            if e["event"] == "run_start" and len(e["chain"]) > 1:
                a["asked_by"].append(e["chain"][-2])
            elif e["event"] == "delegation":
                delegations.append({"from": e["agent"], "to": d["to"], "question": d["question"]})
            elif e["event"] in ("delegation_refused", "delegation_cached"):
                delegations.append({"from": e["agent"], "to": d.get("to"), "question": d.get("question"),
                                    "note": e["event"] + (f": {d.get('reason')}" if d.get("reason") else "")})
            elif e["event"] == "model_response":
                for c in d.get("tool_calls", []):
                    if c["tool"] not in ("final_result", "ask_agent"):
                        a["tools"][c["tool"]] += 1
            elif e["event"] == "run_end":
                o = d.get("output") or {}
                a["summary"] = o.get("decision") or o.get("summary")
                a["actions_taken"] = o.get("actions_taken") or o.get("drafts_created") or []
                if e["depth"] == 0:
                    boss_output = o
        ends = [e for e in run if e["event"] in ("run_end", "run_error") and e["depth"] == 0]
        usage = ends[-1]["usage"] if ends else {}

        board = get(f"/tickets/{tid}")["board"]
        t_reqs = [r for r in requests if r["ticket_id"] == tid]
        approvals = [
            {"request_id": r["id"], "kind": r["kind"], "ref_id": r["ref_id"], "payee": r["payee"],
             "amount": r["amount"], "prepared_by": NAMES.get(r["requested_by"], r["requested_by"]),
             "decision": r["status"], "approved_by": r["decided_by"], "decided_at": r["decided_at"],
             "payment_id": r["payment_id"]}
            for r in t_reqs
        ]
        resolution_notes = [n for n in board["notes"] if n["note"].startswith("Status -> resolved")]
        paid = [a for a in approvals if a["decision"] == "paid"]
        out_tickets.append({
            "id": tid,
            "subject": tickets[tid]["subject"],
            "requester": tickets[tid]["requester"],
            "final_status": tickets[tid]["status"],
            "boss_status_at_end_of_run": boss_output.get("status"),
            "short_outcome": boss_output.get("decision"),
            "run_id": run_id,
            "model": "gpt-6-luna",
            "usage": {"model_calls": usage.get("requests"), "tool_calls": usage.get("tool_calls"),
                      "total_tokens": usage.get("total_tokens")},
            "agents": [
                {**{k: v for k, v in a.items() if k != "tools"}, "tools": dict(a["tools"]),
                 "contribution": a["summary"]}
                for a in agents.values()
            ],
            "delegations": delegations,
            "drafts": board["drafts"],
            "human_approvals": approvals,
            "resolved_by": [{"author": n["author"], "note": n["note"], "at": n["created_at"]} for n in resolution_notes],
            "cash_change": -round(sum(a["amount"] for a in paid), 2),
        })

    total_out = round(sum(-t["cash_change"] for t in out_tickets), 2)
    report = {
        "run_started_after_reset_at": reset["timestamp"],
        "shop_date": cash["as_of"],
        "starting_checking_balance": start_cash,
        "tickets": out_tickets,
        "total_paid_out": total_out,
        "computed_ending_balance": round(start_cash - total_out, 2),
        "ending_checking_balance_cash_accounts": cash["balance"],
        "math_checks_out": round(start_cash - total_out, 2) == cash["balance"],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    r = collect()
    print(f"start {r['starting_checking_balance']}  paid out {r['total_paid_out']}  "
          f"computed end {r['computed_ending_balance']}  cash_accounts {r['ending_checking_balance_cash_accounts']}  "
          f"ok={r['math_checks_out']}")
    for t in r["tickets"]:
        print(f"\n#{t['id']} {t['final_status']} | {t['short_outcome']} | {t['usage']}")
        for d in t["delegations"]:
            print(f"   {d['from']} -> {d['to']}  {d.get('note','')}")
        for a in t["agents"]:
            print(f"   {a['name']}: {a['tools']}")
        for ap in t["human_approvals"]:
            print(f"   approval: #{ap['request_id']} {ap['kind']} ${ap['amount']} -> {ap['decision']} by {ap['approved_by']}")
        print("   resolved:", [x["author"] for x in t["resolved_by"]], "cash change", t["cash_change"])
