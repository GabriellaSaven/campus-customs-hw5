"""Build output/resolved_board.html: a double-clickable page with a screenshot of
the React board for each resolved ticket (101, 102, 103). Images are embedded
(base64), so the page works offline and can be moved anywhere.

Screenshots come from output/screenshots/board_ticket_<id>.jpg (headless Chrome of
http://localhost:5173/#ticket=<id>&expand=1 after the run).
Usage:  .venv/bin/python scripts/build_resolved_board.py
"""

import base64
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "resolved_board.html"
SHOTS = ROOT / "output" / "screenshots"
DATA = json.loads((ROOT / "output" / "resolved_tickets.json").read_text())


def card(t: dict) -> str:
    img = base64.b64encode((SHOTS / f"board_ticket_{t['id']}.jpg").read_bytes()).decode()
    approvals = ", ".join(
        f"#{a['request_id']} {a['kind']} ${a['amount']:,.2f} ({a['decision']} by {a['approved_by']})"
        for a in t["human_approvals"]
    ) or "none needed"
    change = t["cash_change"]
    return f"""
<section class="ticket" id="t{t['id']}">
  <header>
    <div>
      <div class="eyebrow">File #{t['id']} · {html.escape(t['requester'])}</div>
      <h2>{html.escape(t['subject'])}</h2>
      <p class="outcome">“{html.escape(t['short_outcome'] or '')}” <span>— Ron</span></p>
    </div>
    <div class="stamp">{t['final_status']}</div>
  </header>
  <dl class="facts">
    <div><dt>Agents</dt><dd>{', '.join(a['name'].split(' ')[0] for a in t['agents'])}</dd></div>
    <div><dt>Handoffs</dt><dd>{len(t['delegations'])}</dd></div>
    <div><dt>Human approvals</dt><dd>{html.escape(approvals)}</dd></div>
    <div><dt>Cash change</dt><dd class="{'neg' if change < 0 else ''}">{'−$' + format(-change, ',.2f') if change else '$0.00'}</dd></div>
    <div><dt>Tokens</dt><dd>{t['usage']['total_tokens']:,}</dd></div>
  </dl>
  <a class="shot" href="screenshots/board_ticket_{t['id']}.jpg" target="_blank" title="Open full size">
    <img alt="React board for ticket {t['id']} after it was resolved" src="data:image/jpeg;base64,{img}">
  </a>
  <p class="caption">The live React dashboard (Operations Desk) with file #{t['id']} open after the run and human approval: the memo, the bullpen conversation, Ron's decision, end-of-shift reports, the ledger and the corkboard. Click to open full size.</p>
</section>"""


def main() -> None:
    tabs = "".join(f'<a href="#t{t["id"]}">#{t["id"]} · {html.escape(t["subject"])}</a>' for t in DATA["tickets"])
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Customs · Resolved Board</title>
<style>
  :root {{ --wall:#efe5d2; --ink:#2b2118; --muted:#7a6a58; --line:#e2d5bd; --paper:#fffdf7; --walnut:#5b3a22; --green:#2f7a4b; --red:#b23a2b; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:var(--wall); color:var(--ink); font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  .top {{ background:linear-gradient(180deg,#6a4428,var(--walnut)); color:#f7ecd9; padding:26px 36px 18px; }}
  .top .eyebrow {{ opacity:.75; }}
  .top h1 {{ margin:4px 0 6px; font-family:Georgia,serif; font-size:30px; }}
  .top p {{ margin:0; opacity:.9; }}
  .summary {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:16px; }}
  .summary div {{ background:rgba(255,255,255,.1); border-radius:8px; padding:8px 14px; font-size:13.5px; }}
  .summary b {{ display:block; font-size:18px; font-family:Georgia,serif; }}
  nav {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:16px; }}
  nav a {{ color:#3a2810; background:linear-gradient(160deg,#e6c878,#c9a24f); padding:6px 12px; border-radius:6px; text-decoration:none; font-weight:650; font-size:13.5px; }}
  main {{ max-width:1180px; margin:0 auto; padding:28px 24px 60px; }}
  .ticket {{ background:var(--paper); border:1px solid var(--line); border-radius:6px; padding:22px 24px; margin-bottom:28px; box-shadow:0 6px 18px rgba(60,40,20,.09); }}
  .ticket header {{ display:flex; justify-content:space-between; gap:20px; align-items:flex-start; }}
  .eyebrow {{ font-family:"American Typewriter","Courier New",monospace; font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }}
  h2 {{ margin:2px 0 6px; font-family:Georgia,serif; font-size:24px; }}
  .outcome {{ margin:0; font-size:15px; }} .outcome span {{ color:var(--muted); }}
  .stamp {{ transform:rotate(-8deg); border:3px double var(--green); color:var(--green); padding:2px 12px; border-radius:6px; font-family:"American Typewriter","Courier New",monospace; font-weight:700; letter-spacing:.18em; text-transform:uppercase; white-space:nowrap; margin-top:8px; }}
  .facts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:10px; margin:16px 0; }}
  .facts div {{ background:#f5eddc; border-radius:6px; padding:8px 11px; }}
  .facts dt {{ font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }}
  .facts dd {{ margin:2px 0 0; font-size:13.5px; }} .facts dd.neg {{ color:var(--red); font-weight:700; }}
  .shot {{ display:block; max-height:820px; overflow:auto; border:1px solid var(--line); border-radius:4px; background:#e9e1cf; }}
  .shot img {{ width:100%; display:block; }}
  .caption {{ color:var(--muted); font-size:13px; margin:8px 0 0; }}
  .top .eyebrow {{ color:#f7ecd9; opacity:.7; }}
  footer {{ text-align:center; color:var(--muted); font-size:12.5px; padding-bottom:30px; }}
</style>
</head>
<body>
<div class="top">
  <div class="eyebrow">Department of Campus Customs · Operations Desk</div>
  <h1>The Resolved Board</h1>
  <p>Full run after a clean reset · shop date {DATA['shop_date']} · every agent on gpt-6-luna · payments approved by a human</p>
  <div class="summary">
    <div>Starting checking<b>${DATA['starting_checking_balance']:,.2f}</b></div>
    <div>Paid out<b>${DATA['total_paid_out']:,.2f}</b></div>
    <div>Ending checking<b>${DATA['ending_checking_balance_cash_accounts']:,.2f}</b></div>
    <div>Files resolved<b>{sum(t['final_status'] == 'resolved' for t in DATA['tickets'])} of {len(DATA['tickets'])}</b></div>
  </div>
  <nav>{tabs}</nav>
</div>
<main>
{''.join(card(t) for t in DATA['tickets'])}
</main>
<footer>Screenshots: headless Chrome of http://localhost:5173/#ticket=&lt;id&gt;&amp;expand=1 after the run · data: output/resolved_tickets.json</footer>
</body>
</html>
"""
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
