"""Fill the Actual sections and the Cash tab of output/desk_tickets.html from
output/resolved_tickets.json (made by scripts/run_report.py). The Expected
sections are left untouched. Re-running replaces only what this script wrote.

Usage:  .venv/bin/python scripts/build_desk_tickets.py
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "output" / "desk_tickets.html"
DATA = json.loads((ROOT / "output" / "resolved_tickets.json").read_text())

AV = {"boss": ("a-boss", "R"), "inventory": ("a-inv", "A"), "accounting": ("a-acc", "B"),
      "facilities": ("a-fac", "C"), "customer_service": ("a-cs", "L")}
SHORT = {"boss": "Ron (Boss)", "inventory": "April (Inventory)", "accounting": "Ben (Accounting)",
         "facilities": "Chris (Facilities)", "customer_service": "Leslie (Customer Service)"}

# My comparison of Actual vs Expected for each ticket (✓ = matches, △ = differs, ✗ = miss).
COMPARE = {
    101: [
        ("ok", "Boss called <b>Inventory first</b>, as expected (and asked Accounting in the same step, in parallel)."),
        ("diff", "Expected <b>Inventory → Accounting</b>. Actually the Boss asked Accounting directly, twice: first to confirm the invoice, then to file the request. Hub-and-spoke instead of a specialist handoff."),
        ("ok", "Accounting → Boss came back as a <i>reply</i>, as planned. Facilities was not involved."),
        ("ok", "$840 request for invoice #501 filed and left <b>pending for a human</b>. No restock date promised while the vendor was blocked."),
        ("ok", "Customer draft to Tauhid: size S unavailable, offers an alternative size, no internal details. Not sent."),
        ("ok", "No purchase order drafted (optional in Expected), so no money was committed before the open invoice was settled."),
        ("diff", "The data gap from Expected (is the rush reprint on #501 already made?) was <b>not flagged</b> by any agent."),
        ("ok", "Boss set <code>awaiting_approval</code>. After the human paid #501, the ticket auto-resolved."),
    ],
    102: [
        ("ok", "Boss called <b>Facilities first</b>, as expected. Chris confirmed $2,400 due 2026-09-02, <b>urgent</b> (within 3 days) but not overdue."),
        ("diff", "Expected <b>Facilities → Accounting</b>. Actually the Boss asked Accounting directly, and <b>Accounting → Facilities</b> (Ben asked Chris to re-verify the lease record), which was one extra round trip."),
        ("ok", "Inventory and Customer Service were not involved, as expected."),
        ("ok", "Rent request #2 for $2,400 filed. Ben's math matched Expected: $3,400 − $840 pending − $2,400 = <b>$160</b> left."),
        ("ok", "Boss set <code>awaiting_approval</code>. After the human paid, the ticket auto-resolved and <code>leases.next_due</code> moved to 2026-10-02."),
    ],
    103: [
        ("ok", "Boss called <b>Inventory first</b> (and Accounting in parallel). April found 8 on hand, 12 short; the vendor was blocked by #501."),
        ("ok", "Boss asked Accounting <b>one combined question</b> (margin, restock cost, cash), as Expected planned."),
        ("diff", "<b>Accounting → Inventory</b>: Ben asked April to re-confirm stock and the vendor ID for the restock cost. That's a specialist handoff not in the plan."),
        ("ok", "Ben's numbers match Expected exactly: margin $720 at list price, $604 at 10% off, $488 at 20% off; restock 12 × $22 = <b>$264</b>; $160 available, so <b>$104 short</b>."),
        ("ok", "No duplicate request for #501 and no $264 request filed despite the shortfall. No money moved."),
        ("diff", "Expected a PO draft (12 × $22). Ben reported the cost but drafted no PO, which is reasonable since it couldn't be funded."),
        ("diff", "Expected: a discount within the floor plus 8 now. Actually Ron chose <b>no discount and no promise yet</b> (more conservative) and set <code>awaiting_approval</code> (Expected said <code>escalated</code>). The human then reviewed it and closed the file as held."),
        ("bad", "Leslie's draft to the club mentions “the outstanding vendor invoice and funding” and “until a human resolves”. That shares internal vendor-debt and funding details with a customer, a red flag from Expected. It stays an unsent draft for human editing."),
        ("note", "First attempt (before the final clean reset) stopped at the 40-tool-call guardrail: Leslie re-asked teammates for facts she'd been given, and Ron asked for a letter before deciding. Prompts were tightened (decide first, one draft, handed-over facts count) and the limits raised to 40 model calls / 50 tool calls. Then the whole run was redone from a fresh reset."),
    ],
}


def money(x: float) -> str:
    return f"−${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def node(agent: str) -> str:
    cls, _ = AV[agent]
    return f'<span class="node {cls}">{SHORT[agent].split(" ")[0]}</span>'


def actual_section(t: dict) -> str:
    first = next((d["to"] for d in t["delegations"] if d["from"] == "boss"), None)
    flow = "".join(
        f'<li>{node(d["from"])}<span class="arrow">→ asks</span>{node(d["to"])}'
        f'<span class="q">“{html.escape((d["question"] or "")[:170])}{"…" if len(d["question"] or "") > 170 else ""}”</span></li>'
        for d in t["delegations"]
    )
    rows = ""
    for a in t["agents"]:
        cls, mono = AV[a["agent"]]
        asked = ", ".join(SHORT[x].split(" ")[0] for x in dict.fromkeys(a["asked_by"])) or "—"
        tools = "".join(
            f'<span class="tool">{k}{f" ×{v}" if v > 1 else ""}</span>' for k, v in a["tools"].items()
        )
        rows += (
            f'<tr><td><span class="avatar-sm {cls}">{mono}</span> <b>{SHORT[a["agent"]]}</b></td>'
            f'<td>{asked}</td><td><div class="tools">{tools}</div></td>'
            f'<td>{html.escape(a["contribution"] or "—")}</td></tr>'
        )
    approvals = "".join(
        f'<li>Request #{ap["request_id"]} · {ap["kind"].replace("_", " ")} → {html.escape(ap["payee"])} · '
        f'<b>${ap["amount"]:,.2f}</b> · prepared by {html.escape(ap["prepared_by"])} · '
        f'<b>{ap["decision"]}</b> by {html.escape(ap["approved_by"] or "—")} (payment #{ap["payment_id"]})</li>'
        for ap in t["human_approvals"]
    ) or "<li>No payment requested on this ticket. Nothing to approve.</li>"
    resolved = "; ".join(f'{html.escape(r["author"])}: “{html.escape(r["note"])}”' for r in t["resolved_by"])
    drafts = "".join(
        f'<li>Draft #{d["id"]} ({d["kind"].replace("_", " ")}) to {html.escape(d["recipient"])}: “{html.escape(d["subject"])}” · {d["status"]}</li>'
        for d in t["drafts"]
    ) or "<li>No drafts.</li>"
    compare = "".join(
        f'<li class="cmp-{k}"><span class="cmp-mark">{ {"ok": "✓", "diff": "△", "bad": "✗", "note": "ℹ"}[k] }</span> {txt}</li>'
        for k, txt in COMPARE[t["id"]]
    )
    u = t["usage"]
    return f"""<!-- ACTUAL-{t['id']}-START -->
  <div class="card actual-card">
    <div class="actual-head">
      <div>
        <h3>What actually happened · run <code>{t['run_id']}</code></h3>
        <div class="result">gpt-6-luna · {u['model_calls']} model calls · {u['tool_calls']} tool calls · {u['total_tokens']:,} tokens</div>
      </div>
      <div class="status-trail"><span class="pill amber">Boss left it: {t['boss_status_at_end_of_run']}</span><span class="arrow">→ human →</span><span class="pill green">Final: {t['final_status']}</span></div>
    </div>
    <p class="outcome"><b>Ron's call:</b> “{html.escape(t['short_outcome'] or '')}”</p>
    <h3>Who the Boss called first</h3>
    <p>{SHORT[first] if first else '—'}</p>
    <h3>Delegations, in order</h3>
    <ol class="deleg">{flow}</ol>
    <p class="flow-note">Every answer travelled back up the chain as a reply (not shown as separate arrows).</p>
    <h3>Agents, tools and contributions</h3>
    <table class="agents-table">
      <thead><tr><th>Agent</th><th>Asked by</th><th>MCP tools used (count)</th><th>What they contributed</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <div class="grid2" style="margin-top:14px">
      <div><h3>Human approvals</h3><ul class="clean">{approvals}</ul><p class="result"><b>Resolved:</b> {resolved}</p></div>
      <div><h3>Left on the board</h3><ul class="clean">{drafts}</ul></div>
    </div>
  </div>
  <div class="card">
    <h3>Expected vs. actual</h3>
    <ul class="compare">{compare}</ul>
  </div>
  <!-- ACTUAL-{t['id']}-END -->"""


def cash_section() -> str:
    start = DATA["starting_checking_balance"]
    running = start
    rows = f'<tr class="start"><td>Starting checking balance (after the reset)</td><td>—</td><td class="num"></td><td class="num"><b>${start:,.2f}</b></td></tr>'
    for t in DATA["tickets"]:
        paid = [a for a in t["human_approvals"] if a["decision"] == "paid"]
        change = t["cash_change"]
        running = round(running + change, 2)
        if paid:
            why = "<br>".join(
                f'Payment #{a["payment_id"]}: {a["kind"]} '
                f'{"#" + str(a["ref_id"]) if a["kind"] == "invoice" else "for lease #" + str(a["ref_id"])} → {html.escape(a["payee"])}, '
                f'<b>${a["amount"]:,.2f}</b> (request #{a["request_id"]} prepared by {html.escape(a["prepared_by"])}, approved by {html.escape(a["approved_by"])})'
                for a in paid
            )
        else:
            why = ("No payment. The 12-hoodie restock (12 × $22 = $264) was <b>not funded</b>: only $160 was left after the other "
                   "two approvals, so it would have been $104 short. No discount was given, so nothing to pay.")
        rows += (f'<tr><td>Ticket #{t["id"]} resolved · {html.escape(t["subject"])}</td><td>{why}</td>'
                 f'<td class="num {"neg" if change < 0 else ""}">{money(change) if change else "$0.00"}</td>'
                 f'<td class="num">${running:,.2f}</td></tr>')
    end = DATA["ending_checking_balance_cash_accounts"]
    parts = " − ".join([f"${start:,.2f}"] + [f"${-t['cash_change']:,.2f}" for t in DATA["tickets"]])
    ok = DATA["math_checks_out"] and abs(running - end) < 0.005
    rows += f'<tr class="end"><td><b>Ending checking balance</b></td><td>Matches <code>cash_accounts.checking</code> in <code>data/campus_customs_new.db</code></td><td class="num"><b>{money(-DATA["total_paid_out"])}</b></td><td class="num"><b>${end:,.2f}</b></td></tr>'
    return f"""<!-- CASH-START -->
  <div class="card">
    <div class="ticket-head">
      <div>
        <h2>Cash · checking account</h2>
        <div class="sub">Shop date {DATA['shop_date']} · full run after a clean reset · cash only goes out (no revenue modeled)</div>
      </div>
      <div><span class="pill {'green' if ok else 'red'}">{'✓ Math checks out' if ok else '✗ Math does not match'}</span></div>
    </div>
    <div class="facts">
      <div class="fact"><b>Starting balance</b>${DATA['starting_checking_balance']:,.2f}</div>
      <div class="fact"><b>Paid out (2 approvals)</b>${DATA['total_paid_out']:,.2f}</div>
      <div class="fact"><b>Ending balance</b>${end:,.2f}</div>
      <div class="fact"><b>Pending after run</b>$0.00</div>
    </div>
  </div>
  <div class="card">
    <h3>Itemized</h3>
    <table class="cash-table">
      <thead><tr><th>Step</th><th>Why (which payment and amount)</th><th class="num">Change</th><th class="num">Checking after</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p class="math"><b>Check:</b> {parts} = <b>${running:,.2f}</b> = <code>cash_accounts.checking</code> (<b>${end:,.2f}</b>) {'✓' if ok else '✗'}</p>
    <p class="result">Every payment row in <code>payments</code> has <code>approved_by = Gabriella Saven</code>. No agent moved money, no balance went negative, and invoice #501 is now <code>paid</code>, <code>leases.next_due</code> = 2026-10-02.</p>
  </div>
  <!-- CASH-END -->"""


EXTRA_CSS = """
  /* ---- Actual + Cash (Problem 9) ---- */
  .actual-card { border-left: 4px solid var(--green); }
  .actual-head { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; align-items: flex-start; }
  .actual-head h3 { margin-bottom: 2px; }
  .status-trail { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .outcome { background: var(--navy-soft); border-radius: 10px; padding: 10px 14px; margin: 12px 0 16px; }
  ol.deleg { margin: 0 0 6px; padding-left: 20px; }
  ol.deleg li { margin: 8px 0; }
  ol.deleg .node { font-size: 12px; padding: 4px 9px; }
  ol.deleg .q { display: block; color: var(--muted); font-size: 13px; margin-top: 4px; }
  .agents-table td { font-size: 13.5px; }
  .agents-table td:first-child { white-space: nowrap; }
  .avatar-sm { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; color: #fff; font-size: 11px; font-weight: 700; vertical-align: middle; }
  ul.compare { list-style: none; margin: 0; padding: 0; }
  ul.compare li { display: flex; gap: 10px; padding: 8px 0; border-top: 1px solid var(--line); font-size: 14px; }
  ul.compare li:first-child { border-top: 0; }
  .cmp-mark { flex: none; width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; font-weight: 800; font-size: 12px; }
  .cmp-ok .cmp-mark { background: var(--green-soft); color: var(--green); }
  .cmp-diff .cmp-mark { background: var(--amber-soft); color: var(--amber); }
  .cmp-bad .cmp-mark { background: var(--red-soft); color: var(--red); }
  .cmp-note .cmp-mark { background: var(--navy-soft); color: var(--navy); }
  .cash-table tr.start td, .cash-table tr.end td { background: var(--bg); }
  .cash-table td.neg { color: var(--red); font-weight: 650; }
  .cash-table td.num, .cash-table th.num { white-space: nowrap; }
  .math { font-size: 15px; background: var(--green-soft); border-radius: 10px; padding: 12px 14px; margin: 16px 0 8px; font-variant-numeric: tabular-nums; }
"""


def main() -> None:
    s = PAGE.read_text()
    for t in DATA["tickets"]:
        block = actual_section(t)
        marker = re.compile(rf"<!-- ACTUAL-{t['id']}-START -->.*?<!-- ACTUAL-{t['id']}-END -->", re.S)
        placeholder = f'<div class="actual-box">Filled in after the agent team runs ticket {t["id"]}.</div>'
        if marker.search(s):
            s = marker.sub(lambda _: block, s)
        else:
            assert placeholder in s, f"placeholder for {t['id']} not found"
            s = s.replace(placeholder, block)
    cash_block = cash_section()
    cash_marker = re.compile(r"<!-- CASH-START -->.*?<!-- CASH-END -->", re.S)
    if cash_marker.search(s):
        s = cash_marker.sub(lambda _: cash_block, s)
    else:
        old = '<div class="card coming">\n    <h2>Cash</h2>\n    <p>Coming later.</p>\n  </div>'
        assert old in s, "Cash placeholder not found"
        s = s.replace(old, cash_block)
    if "/* ---- Actual + Cash (Problem 9) ---- */" not in s:
        s = s.replace("</style>", EXTRA_CSS + "</style>", 1)
    PAGE.write_text(s)
    print("desk_tickets.html updated: Actual for", [t["id"] for t in DATA["tickets"]], "+ Cash tab")


if __name__ == "__main__":
    main()
