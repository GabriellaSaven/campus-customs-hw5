# Campus Customs Agent Harness

The shared reference for the Campus Customs multi-agent operations desk. It covers the tables, the MCP tools, the five agents, the API routes, the dashboard, the full-run results and the safety rules.

## Quick start

```bash
# once, from Homework 5/
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd frontend && npm install && cd ..
# backend (FastAPI + agent team; starts the MCP server from .mcp.json)
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000
# dashboard (second terminal)
cd frontend && npm run dev        # http://localhost:5173
```

| Piece | Where | What it is |
|---|---|---|
| MCP server | `mcp_server/server.py` (+ `.mcp.json`) | The only door to `data/campus_customs_new.db`: 23 tools |
| Agent team | `backend/agents.py`, `backend/prompts/*.md`, `backend/models.py`, `backend/config.py` | Five PydanticAI agents on `gpt-6-luna` via Portkey, with full delegation |
| API | `backend/main.py` | FastAPI routes for the dashboard |
| Dashboard | `frontend/` | React + Vite + TypeScript "Operations Desk" |
| Evidence | `output/` | harness, audit trail, desk tickets, resolved tickets and board, design |
| Checks | `tests/`, `scripts/` | MCP smoke test, prompt/tool check, run report builders |

## Database files

| File | Role |
|---|---|
| `data/campus_customs.db` | The original database as handed out. Never written to. Used to reset before every full run. |
| `data/campus_customs_new.db` | Working copy. The MCP tools read and write this one. |

Reset: before every full run, restore `campus_customs_new.db` from `campus_customs.db` with the human-only MCP tool `reset_shop_database` (`.venv/bin/python -m backend.run_team --reset`). It also recreates the empty board tables.

## Tables and fields

### `desk` (1 row)
Fields: `date_today` (TEXT), `notes` (TEXT)
**Why it matters:** `date_today` = **2026-08-31** is the shop's "today". Every overdue and due-soon check uses it, never the computer's clock.

### `tickets` (3 rows)
Fields: `id` (PK), `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id` (FK → leases), `invoice_id` (FK → invoices), `status`, `notes`, `created_at`
**Why it matters:** This is the board the Boss reads. `type` decides which specialist gets the ticket, and the `sku`/`size`/`lease_id`/`invoice_id` fields point to the rows the agents need.

### `inventory` (10 rows)
Fields: `sku`, `name`, `size`, `qty`, `location` (PK = `sku` + `size`)
**Why it matters:** Inventory checks stock by SKU **and** size here to find shortfalls (`qty` below what was requested).

### `pricing` (4 rows)
Fields: `sku` (PK), `unit_cost`, `list_price`
**Why it matters:** Accounting uses it to check margins on discount requests and to price restock purchase orders (`unit_cost` × qty).

### `vendors` (3 rows)
Fields: `id` (PK), `name`, `specialty`, `lead_days`
**Why it matters:** Inventory picks a restock vendor by `specialty`. `lead_days` is the only source for delivery timing.

### `invoices` (1 row)
Fields: `id` (PK), `vendor_id` (FK → vendors), `amount`, `due_date`, `status`, `description`
**Why it matters:** These are unpaid bills. An `open` invoice blocks that vendor from shipping, and it is overdue when `due_date` < `desk.date_today`.

### `leases` (1 row)
Fields: `id` (PK), `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
**Why it matters:** Facilities uses it for rent amount and due date. After rent is paid, `next_due` should move forward one month.

### `cash_accounts` (1 row)
Fields: `name` (PK), `balance`, `date`
**Why it matters:** This is the only cash the shop has. The pay tool must refuse any payment larger than `balance`, and the balance can never go negative. Cash only goes out; no revenue comes in.

### `payments` (0 rows)
Fields: `id` (PK), `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
**Why it matters:** This is the audit trail. Every approved payment writes one row, and `approved_by` records the human who approved it, as the rules require.

## Board tables (added to the working copy by the MCP server)

The MCP server creates these on startup in `campus_customs_new.db` only. The original database never changes. They hold the team's work so that drafts and requests stay on the board.

| Table | Fields | Why it matters |
|---|---|---|
| `payment_requests` | `id`, `ticket_id`, `kind` (invoice/rent/purchase_order), `ref_id`, `payee`, `amount`, `account`, `reason`, `requested_by`, `status` (pending/paid/rejected), `created_at`, `decided_at`, `decided_by`, `decision_note`, `payment_id` | Agents prepare payments here. Only a human turns one into a real payment. |
| `drafts` | `id`, `ticket_id`, `kind` (customer_message/purchase_order), `author`, `recipient`, `subject`, `body`, `vendor_id`, `sku`, `size`, `qty`, `unit_cost`, `total`, `status`, `created_at` | Customer messages and purchase orders wait here for human review. Nothing is sent. |
| `board_notes` | `id`, `ticket_id`, `author`, `note`, `created_at` | Findings, handoffs and the Boss's decisions, visible to the whole team and the dashboard. |

## Starting data (snapshot of the original database)

- **Cash:** checking = **$3,400.00** (as of 2026-08-31)
- **Vendors:**

  | id | Name | Specialty | Lead days |
  |---|---|---|---|
  | 1 | Bulldog Print Co | apparel reprint | 5 |
  | 2 | Elm City Gifts | mugs and small goods | 3 |
  | 3 | QuickShip CT | local courier | 1 |

- **Invoice 501:** Bulldog Print Co, $840.00, due 2026-08-28, `open`. That makes it **3 days overdue**, so Bulldog Print Co is blocked from shipping.
- **Lease 1:** Chapel Street shop, Elm City Properties, $2,400.00/month, next due **2026-09-02**. It is due in 2 days and not overdue yet.
- **Inventory:**

  | SKU | S | M | L | XL | OS | Unit cost | List price |
  |---|---|---|---|---|---|---|---|
  | CC-HOOD-NAVY | 4 | 8 | 14 | 6 | | $22.00 | $58.00 |
  | CC-TEE-WHITE | **0** | 5 | 3 | 2 | | $8.00 | $28.00 |
  | CC-HAT-BLUE | | | | | 40 | $6.00 | $22.00 |
  | CC-MUG-CREST | | | | | **0** | $3.50 | $14.00 |

## The three open tickets and how they link

### Ticket 101: `customer_order`, Tauhid Zaman, "Bulldog tee"
- **Links:** `sku`/`size` → inventory (CC-TEE-WHITE, S) and `invoice_id` → invoice 501 → vendor 1.
- **What the data shows:** Size S has **0** in stock against 1 requested. Bulldog Print Co (apparel reprint, 5-day lead time) would restock it, but invoice 501 is open and overdue, so they won't ship.
- **Path:** Inventory finds the shortfall and the vendor block. Accounting prepares the $840 payment for human approval. Once it's paid, restock arrives 5 days after the payment date (2026-09-05 if paid 2026-08-31). Customer Service drafts a delay message for Tauhid.
- **Agents:** Boss → Inventory → Accounting → Customer Service.

### Ticket 102: `rent_notice`, Elm City Properties, "Rent due"
- **Links:** `lease_id` → lease 1.
- **What the data shows:** $2,400 is due 2026-09-02, 2 days from today, so it isn't overdue yet. Checking has $3,400, which covers it.
- **Path:** Facilities confirms the amount and due date. Accounting prepares the payment for human approval. Once it's paid, the agents write a `payments` row, lower the cash balance, and move `leases.next_due` to 2026-10-02.
- **Agents:** Boss → Facilities → Accounting.

### Ticket 103: `price_override`, Yale AI Club, "Bulk hoodie discount"
- **Links:** `sku`/`size` → inventory and pricing (CC-HOOD-NAVY, M). There is no lease or invoice link.
- **What the data shows:** They want 20 size M hoodies and only **8** are on hand, a **shortfall of 12**. At list price the order is 20 × $58 = $1,160 against $440 cost, a 62% margin. Restocking 12 would cost 12 × $22 = $264, but the apparel vendor is Bulldog Print Co, which is blocked by invoice 501.
- **Path:** Inventory finds the shortfall and the vendor. Accounting checks how much discount the margin can take and prepares the restock purchase order for approval. The Boss makes the final call on the discount. Customer Service drafts the reply to the club.
- **Agents:** Boss → Inventory → Accounting → Customer Service.

## Cross-ticket constraint: cash is tight

| Spend | Amount | Checking after |
|---|---|---|
| Starting balance | | $3,400.00 |
| Invoice 501 (unblocks Bulldog Print Co) | $840.00 | $2,560.00 |
| Rent (lease 1) | $2,400.00 | $160.00 |
| Restock 12 × CC-HOOD-NAVY M | $264.00 | **−$104.00 (not allowed)** |

All three spends together come to $3,504, which is **$104 more than the shop has**. The invoice and the rent fit, leaving $160. The hoodie restock does not fit on top of them, and the pay tool must refuse it. No money comes in to help. The Boss has to prioritize: rent and the overdue invoice come first, and the hoodie order gets partly filled or delayed.

## First three MCP tools (Problem 3)

The server is `mcp_server/server.py` (FastMCP). It works on `data/campus_customs_new.db`, and every agent uses these tools. These first three are read-only and return only data from the database, plus arithmetic on it.

| Tool | Table(s) it reads | Ticket it unlocks | Why it's the right tool for that ticket |
|---|---|---|---|
| `check_stock(sku, size, qty_needed)` | `inventory` | **101** (Bulldog tee, size S) | Ticket 101 depends on whether the shop holds a size S tee, and this tool finds the exact SKU + size row: 0 on hand, a shortfall of 1. That tells the team it's a restock problem, not a pick-and-ship order. |
| `get_lease_rent_status(lease_id)` | `leases`, `desk`, `cash_accounts` | **102** (rent notice) | Ticket 102 links to `lease_id` 1, and this tool gives the $2,400 rent, its 2026-09-02 due date (2 days after `desk.date_today`, not overdue) and whether checking ($3,400) covers it. That's everything Facilities and Accounting need before asking a human to approve payment. |
| `check_discount_margin(sku, qty, discount_pct)` | `pricing` | **103** (AI Club bulk hoodie discount) | Ticket 103 is a price-override request, so the deciding fact is how much margin a discount leaves. This tool shows 20 hoodies at list price earn a 62% margin and that break-even is a 62.1% discount, so the Boss can choose a discount using real cost and list-price figures. |

`check_stock` also covers the stock side of 103 (8 size M on hand for 20 requested, a shortfall of 12). The vendor/invoice block on 101 (invoice 501) is covered by `check_vendor_status` and `get_invoice`, added in Problem 5 (see the full list below).

## MCP connection and smoke test

- **Connection:** `.mcp.json` at the `Homework 5` project root registers the server as `campus-customs` (stdio). It runs `${CLAUDE_PROJECT_DIR:-.}/.venv/bin/python ${CLAUDE_PROJECT_DIR:-.}/mcp_server/server.py`. There are no machine-specific paths, so it runs on any computer once `.venv` is created from `requirements.txt`. Claude Code lists it under "Project config (shared via .mcp.json)".
- **Test:** `.venv/bin/python tests/mcp_smoke_test.py` launches the server from `.mcp.json` and calls each tool with arguments taken from its ticket. It then re-reads `data/campus_customs_new.db` with plain SQL and compares every value.
- **Evidence:** `output/mcp_smoke.json` has the prompt, tool name, arguments, full tool output and a per-field database check for each tool. Result: **all 3 tools match the database.**

| Ticket | Tool | Key output (matches the database) |
|---|---|---|
| 101 | `check_stock` | CC-TEE-WHITE size S: 0 on hand, shortfall 1, Aisle B |
| 102 | `get_lease_rent_status` | $2,400 due 2026-09-02, 2 days after 2026-08-31, not overdue; checking $3,400 covers it |
| 103 | `check_discount_margin` | 20 hoodies at 10% off (a test value; the ticket names no %): $52.20 each, $1,044 total, $604 margin |

## All MCP tools (23)

There is one MCP server and no second path to the database. The backend reads the board through MCP too.

| Tool | Tables used | Reads/writes | Who can call it |
|---|---|---|---|
| `get_today` | `desk` | read | all agents |
| `list_open_tickets` | `tickets` | read | Boss (and the backend runner) |
| `list_tickets` | `tickets` | read | dashboard (`GET /api/tickets`) |
| `list_payment_requests` | `payment_requests`, `cash_accounts` | read | dashboard (`GET /api/payment-requests`) |
| `get_ticket` | `tickets`, `leases`, `invoices`, `vendors`, `board_notes`, `drafts`, `payment_requests` | read | all agents |
| `check_stock` | `inventory` | read | Inventory |
| `list_inventory` | `inventory` | read | Inventory |
| `list_vendors` | `vendors`, `invoices`, `desk` | read | Inventory, Accounting |
| `check_vendor_status` | `vendors`, `invoices`, `desk` | read | Inventory, Accounting |
| `get_invoice` | `invoices`, `vendors`, `desk`, `payment_requests` | read | Accounting |
| `get_cash_position` | `cash_accounts`, `payment_requests` | read | Boss, Accounting |
| `check_discount_margin` | `pricing` | read | Accounting |
| `get_lease_rent_status` | `leases`, `desk`, `cash_accounts` | read | Accounting, Facilities |
| `request_payment` | `invoices`, `leases`, `drafts`, `vendors`, `cash_accounts` → **writes** `payment_requests` | board write | Accounting |
| `draft_purchase_order` | `vendors`, `pricing`, `inventory`, `invoices`, `desk` → **writes** `drafts` | board write | Accounting |
| `draft_customer_message` | `tickets` → **writes** `drafts` | board write | Customer Service |
| `add_board_note` | `tickets` → **writes** `board_notes` | board write | all agents |
| `set_ticket_status` | `tickets`, `payment_requests` → **writes** `tickets.status`, `board_notes` | board write | Boss |
| `pay_approved_request` | `payment_requests`, `payments`, `cash_accounts`, `invoices`, `leases`, `drafts` | **moves money** | **human only** (dashboard) |
| `reject_payment_request` | `payment_requests` | board write | **human only** |
| `resolve_ticket` | `tickets`, `payment_requests` → **writes** `tickets.status`, `board_notes` | board write | **human only** (refused while a payment is pending) |
| `add_human_note` | `tickets` → **writes** `board_notes` (marked `[From the human desk]`) | board write | **human only**; agents' `add_board_note` and `set_ticket_status` refuse that mark |
| `reset_shop_database` | copies `campus_customs.db` → `campus_customs_new.db`, recreates board tables | reset | **human only** |

## Agent team (Problem 5)

Built with PydanticAI in `backend/`. Each agent has a light-touch personality on the dashboard and in its prompt: **Ron** (Boss), **April** (Inventory), **Ben** (Accounting), **Chris** (Facilities) and **Leslie** (Customer Service). Personality only changes tone; jobs, tools and rules are unchanged, and customer drafts stay professional. Every agent runs on **`gpt-6-luna` via Portkey** (`PORTKEY_API_KEY`), using OpenAI's Responses API. Portkey reports the deployment as `gpt-6-luna-global`, which is the provider's name for the same model. The model is one constant in `backend/config.py` and can't be overridden by an environment variable.

| Agent | Prompt | Job | MCP tools it gets | Output |
|---|---|---|---|---|
| Boss | `backend/prompts/boss.md` | Reads tickets, routes work, enforces rules, sets priorities when cash is short, makes final calls | `get_today`, `get_ticket`, `list_open_tickets`, `get_cash_position`, `add_board_note`, `set_ticket_status` | `TicketDecision` |
| Inventory | `backend/prompts/inventory.md` | Stock by SKU + size, shortfalls, alternatives, restock vendor and lead time | `get_today`, `get_ticket`, `check_stock`, `list_inventory`, `list_vendors`, `check_vendor_status`, `add_board_note` | `AgentReport` |
| Accounting | `backend/prompts/accounting.md` | Invoices, overdue, cash after pending requests, margins, payment requests and POs for human approval | `get_today`, `get_ticket`, `get_invoice`, `check_vendor_status`, `list_vendors`, `get_cash_position`, `check_discount_margin`, `get_lease_rent_status`, `request_payment`, `draft_purchase_order`, `add_board_note` | `AgentReport` |
| Facilities | `backend/prompts/facilities.md` | Lease, rent, landlord, and building issues; urgent vs. routine | `get_today`, `get_ticket`, `get_lease_rent_status`, `add_board_note` | `AgentReport` |
| Customer Service | `backend/prompts/customer_service.md` | Draft replies (never sent); gets facts from teammates | `get_today`, `get_ticket`, `draft_customer_message`, `add_board_note` | `AgentReport` |

- **Full connectivity:** every agent also has `ask_agent(teammate, question)` and can delegate to any of the other four. The teammate runs its own loop and returns its report.
- **Agent loop:** each agent runs PydanticAI's loop: model call, then tool calls, then the results go back to the model, until it returns its typed output. The Boss starts each ticket (`run_ticket`). `run_open_tickets` runs every open ticket oldest first, so later tickets see the payment requests filed by earlier ones.
- **Files:** `backend/config.py` holds the model, Portkey, tool access and limits. `backend/models.py` holds the data types. `backend/agents.py` builds the team, the loop and delegation. `backend/mcp_client.py` connects through `.mcp.json`. `backend/audit.py` writes the audit trail. `backend/run_team.py` is the command-line runner.
- **Check:** `tests/check_prompt_tools.py` confirms every tool named in a prompt exists on the MCP server and is given to that agent. Result: OK.
- **Prompt fixes after the first full run (Problem 9):**
  - The Boss decides *before* asking Customer Service for a reply and asks for one draft.
  - On price overrides, the Boss asks Accounting one combined question (margin, restock cost, cash).
  - Customer Service treats facts handed over by a teammate as confirmed, and checks the board before drafting.
- **Human-desk notes:** all five prompts say that board notes marked `[From the human desk]` come from the person running the shop. Agents take them into account, but the notes never override a shop rule.

## Audit trail

`output/audit_trail.json` is one JSON array that is **only ever appended to**. Each run adds entries to the end and never removes old ones, and the file is never wiped. Writes are file-locked and atomic (written to a temp file, then renamed into place).

Every entry records: `timestamp`, `run_id`, `ticket_id`, `agent`, `depth` and the delegation `chain`, the loop `step`, `event`, `model`, `detail`, and the running `usage` (requests, tool calls, input/output/total tokens). The events are:

- `run_start`: prompt file, user prompt, the agent's tool list.
- `user_prompt` and `model_request`: the loop advancing.
- `model_response`: the tools the model called, with arguments; any text; the finish reason; the provider's model name; tokens for that response.
- `tool_results`: each tool's result, and any retry messages.
- `delegation`, `delegation_cached` and `delegation_refused`: who asked whom, what was asked, and why a request was refused.
- `end`, `run_end` and `run_error`: the final typed output or the error.

## Backend routes (Problem 7)

`backend/main.py` (FastAPI). Start it from `backend/` with `uvicorn main:app --reload --port 8000`. All routes go through the MCP server, except `/api/events`, which reads the audit trail file.

- `GET  /api/tickets` — **(1)** every ticket with its `status` and `is_open` (open or resolved), plus open/resolved counts.
- `POST /api/tickets/{ticket_id}/run` — **(2)** runs the agent team (the Boss first) on one ticket. Returns a `run_id` right away; add `?wait=true` to wait for the decision. Returns 409 if another run is in progress.
- `GET  /api/events?limit=&after=&ticket_id=&run_id=` — **(3)** recent agent events from `output/audit_trail.json`: who spoke, what they said, which tools they called and what came back. Use `after=<last_index>` to poll for new ones.
- `POST /api/payment-requests/{request_id}/approve` (body `{"approved_by": "<human name>"}`) — **(4)** a human approves a prepared payment or purchase order. This is the **only** route that moves cash: it updates `payments`, `cash_accounts`, and the invoice, lease or PO. It's refused if cash is short, the approver is an agent, or the vendor is blocked.
- `GET  /api/cash` — **(5)** the current checking balance from `cash_accounts`, plus the pending total and what's left after it.
- `POST /api/reset` — **(6)** restores `campus_customs_new.db` from the original for a fresh run. The swap is atomic, so a dashboard poll never sees a half-reset database. The audit trail is kept and gets a `shop_reset` marker, so the dashboard only shows runs after it. Returns 409 during a run.
- `GET  /api/tickets/{ticket_id}` — one ticket plus its board (notes, drafts, payment requests).
- `GET  /api/tickets/{ticket_id}/summary` — a short per-agent summary of the latest run since the last reset: who asked whom, the tools used, each agent's conclusion. (Problem 8)
- `POST /api/tickets/{ticket_id}/resolve` (body `{"resolved_by", "note"}`) — a human marks a reviewed ticket resolved. Refused while a payment is pending. (Problem 8)
- `GET  /api/payment-requests?status=pending|paid|rejected|all` — the human approval queue.
- `GET  /api/briefing` — the dashboard whiteboard: overdue invoices, vendors on hold, rent coming due, signatures waiting and overdraw warnings, computed through MCP reads. (Problem 8 follow-up)
- `POST /api/tickets/{ticket_id}/notes` (body `{"author", "note"}`) — the suggestion box: a person pins a signed `[From the human desk]` note that agents read on their next run. It never overrides shop rules. (Problem 8 follow-up)
- `POST /api/payment-requests/{request_id}/reject` (body `{"decided_by", "reason"}`) — a human turns a request down; no money moves.
- `GET  /api/runs` and `GET /api/runs/{run_id}` — status and result of runs since the server started.
- `GET  /api/health` — whether the team is ready, the model, and any run in progress.

Interactive docs: `http://localhost:8000/docs`. CORS allows the Vite dashboard origin `http://localhost:5173` (and `127.0.0.1:5173`, plus other localhost ports as a fallback).

The approve route also **auto-resolves** a ticket when its last pending payment is approved and the Boss had left it `awaiting_approval`, because nothing is left for a human.

**Tested (8/31 shop date):** every route was called against the running server.
- Ticket 102 ran through the API in 11 model calls, about 26,000 tokens, ending in `awaiting_approval` with rent request #1 for $2,400.
- Approval as `accounting` was refused. Approval as a human paid it: cash went from $3,400 to $1,000, and `leases.next_due` moved to 2026-10-02. Approving again was refused.
- `/api/reset` restored everything ($3,400, all three tickets open, no payments).

## Dashboard (Problem 8)

`frontend/` (React + Vite + TypeScript), styled as a warm sitcom-style **operations desk**: file-folder tickets, memo, bullpen, ID badges, ledger, a clipboard of checks, and a corkboard. Start it with `npm run dev` in `frontend/` → http://localhost:5173. It calls the backend at http://localhost:8000. The design and why are in `output/design.md`.

| Need | How the dashboard does it | Route(s) |
|---|---|---|
| List all three tickets | Ticket rail with status pills and a stamp for resolved tickets | `GET /api/tickets` (polled every 4 s) |
| Pick a ticket and start the team | Click a ticket, then **Start the team** | `POST /api/tickets/{id}/run` |
| See each agent while it runs | Live "On the floor" feed, team roster and ticker | `GET /api/events?run_id=` + `GET /api/runs/{id}` (polled every 1.2 s) |
| Mark resolved when the run finishes | A "Team finished" banner, then a **Resolved** stamp once nothing is left for a human: auto on final approval, or **Mark resolved** | `POST /api/payment-requests/{id}/approve`, `POST /api/tickets/{id}/resolve` |
| Short summary of what each agent did | "Who did what" cards | `GET /api/tickets/{id}/summary` |
| Human approves a payment or purchase | Approvals queue: type your name, then **Sign & pay $X** (or Decline) | `GET /api/payment-requests`, `POST .../approve`, `POST .../reject` |
| Checking balance drops after a payment | Cash card rolls down with a −$X chip | `GET /api/cash` |
| Fresh run | **Reset shop** (asks to confirm) | `POST /api/reset` |

**Tested in the browser:** ticket 102 ran from the dashboard and the feed showed Boss → Facilities → Accounting live. The ticket went to "Needs your OK". Signing as a human paid $2,400, checking rolled from $3,400 to $1,000, ticket 102 got its Resolved stamp, and the queue emptied. The shop was then reset to its original data.

**Office features added after the first draft:**
- a **whiteboard** briefing (`GET /api/briefing`),
- a **suggestion box** for signed human notes the agents read on re-runs (`POST /api/tickets/{id}/notes`),
- an **Employee of the Month** frame computed from the audit trail,
- a **waffle break** when every file is closed,
- a **break-room quotes board**.

Deep links like `http://localhost:5173/#ticket=103` open a file, and `&expand=1` shows the whole bullpen (used for the screenshots).

## Full run results (Problem 9)

The shop was reset, then the three tickets were run oldest first (101 → 102 → 103) through the API that the dashboard uses, until each was resolved. Details are in `output/desk_tickets.html` (Actual sections, Cash tab and Reflection tab), `output/resolved_tickets.json` and `output/resolved_board.html`, with screenshots in `output/screenshots/`.

| Ticket | Run | Boss left it | Human action | Final | Cash change |
|---|---|---|---|---|---|
| #101 Bulldog tee | `d41f5bd4208e` | `awaiting_approval` | paid request #1 (invoice, $840.00) as Gabriella Saven | `resolved` | −$840.00 |
| #102 Rent due | `3035ad09c001` | `awaiting_approval` | paid request #2 (rent, $2,400.00) as Gabriella Saven | `resolved` | −$2,400.00 |
| #103 Bulk hoodie discount | `53d572ff39ac` | `awaiting_approval` | reviewed Ron's hold and closed the file | `resolved` | $0.00 |

**Cash:** $3,400.00 − $840.00 − $2,400.00 − $0.00 = **$160.00**, which matches `cash_accounts.checking` = $160.00. Both `payments` rows have `approved_by = Gabriella Saven`. Invoice 501 is `paid`, and `leases.next_due` moved to 2026-10-02.

**What the run showed:**
- The vendor-invoice rule, the human-approval rule, the no-negative-cash rule and the `desk.date_today` rule were all followed.
- On #103, Ben's math matched the plan exactly: a 12 × $22 = $264 restock against $160 available is $104 short. No unaffordable request was filed.
- The team used specialist-to-specialist handoffs (Ben → Chris on #102, Ben → April on #103), plus hub-and-spoke from Ron.
- **Miss:** Leslie's draft to the Yale AI Club mentions the "outstanding vendor invoice and funding". That's internal detail. It stays an unsent draft for human editing.
- **Not flagged:** no agent asked whether the rush reprint on invoice 501 already exists.

**First attempt (kept in the audit trail, before the final reset).** #101 and #102 finished, but #103 hit the **40-tool-call guardrail** and stopped cleanly with no money moved. Leslie had re-asked teammates for facts the Boss had already given her, and Ron had asked for a letter before deciding the discount. The fix was prompt changes (see Agent team) plus limits of 40 model calls / 50 tool calls. The whole run was then redone from a fresh reset.

**Follow-up fix: customer-draft privacy.** The Problem 9 draft to the Yale AI Club leaked "outstanding vendor invoice and funding". I tightened Leslie's prompt and added the draft guardrail above, then tested it with `tests/test_customer_draft_privacy.py`. The test re-runs #103 with the real MCP server and agents against a **scratch copy** of the shop, set to the moment just before #103 ran. The graded working database, audit trail and reports are untouched; the server's `CAMPUS_CUSTOMS_DB` setting points it at the scratch copy. Results (`output/customer_draft_privacy_test.json`):
- The Problem 9 wording was **refused**, and a clean rewording was accepted.
- The re-run draft had **no internal money terms**, 0 drafts were blocked during the run, no money moved, and the working database fingerprint was unchanged.
- The run took 57,943 tokens on gpt-6-luna.
- **Still borderline:** the new draft quotes a hedged earliest date ("if restocking is unblocked… earliest possible arrival would be Sep 5, but that isn't confirmed"). The rules say no date while the vendor is blocked.

**Audit trail:** both attempts and the final run are appended to `output/audit_trail.json` (nothing removed). Each reset leaves a `shop_reset` marker.

## Safety guardrails

Guardrails a real business would want once agents touch real customers and real money. The ones marked ✅ are built in now.

**Money**
- ✅ Agents can only *request* payments. The pay tool is never in any agent's toolset, and the backend also blocks it if an agent somehow calls it.
- ✅ The pay tool needs a named human approver (agent names are refused). It refuses when cash is short, so no balance can go negative.
- ✅ The pay tool refuses a purchase order while that vendor still has an open invoice.
- ✅ A completed payment updates `payments`, `cash_accounts`, and the invoice, lease or purchase order in one transaction.
- ✅ Payment amounts are pulled from the records, never typed in by an agent. Duplicate requests are refused.
- ✅ A ticket with a pending payment can't be marked `resolved`.
- Real world: two-person approval above a threshold, daily spend caps, payee allowlists (no new bank details by email), and reconciliation against the bank.

**Customers and vendors**
- ✅ Messages and purchase orders are drafts on the board. No tool can send email or contact a vendor.
- ✅ Customer Service can't read cash, costs or vendor debts directly, and its prompt forbids sharing them.
- ✅ **Draft guardrail (added after Problem 9):** `draft_customer_message` refuses any draft that mentions internal money matters (invoice, unpaid, overdue, owe, funding, cash, bank balance, margin, unit cost, payment request, "a human", manager approval) and tells the agent to rephrase. Leslie's prompt now spells out what stays internal, with a before/after example.
- Real world: human review before anything goes out, PII minimization and retention rules, opt-out handling, and a tone and claims checklist (no promised dates or discounts that weren't confirmed).

**Data and access**
- ✅ One MCP server is the only path to shop data, and each agent gets only the tools its job needs.
- ✅ Agents can't fake who wrote something: `author` is filled in by the backend and hidden from the model, and only people can write `[From the human desk]` notes.
- ✅ The original database is never written to, and there's a reset before every full run.
- ✅ Every model call, tool call, result and delegation is in the append-only audit trail.
- Real world: separate dev and prod data, secrets in a vault (not `.env`), rate limits, alerting on unusual tool use, and regular review of audit logs.

## Token and cost limits

All of these live in `backend/config.py`. Usage is shared across a ticket's whole delegation tree, so the limits cover the entire team's work on that ticket.

| Limit | Value | What it prevents |
|---|---|---|
| Model | `gpt-6-luna` only, reasoning effort `low` | Expensive models or long reasoning |
| Model calls per ticket | 40 (raised from 30 in Problem 9) | Endless loops |
| Tool calls per ticket | 50 (raised from 40 in Problem 9) | Tool-call spirals |
| Tokens per ticket | 150,000 total | Runaway cost; the run stops cleanly and logs it |
| Output tokens per response | 2,000 | Rambling answers |
| Delegation depth | 2 (Boss → specialist → specialist) | Deep chains |
| Delegations per ticket | 8 | Too much back-and-forth |
| Ask back up the chain | refused | A asks B, B asks A |
| Same question to the same teammate | answered from cache | Paying twice for the same answer |
| Retries on bad tool arguments or output | 1 | Retry storms |
| Prompts | "Keep it tight" footer in all five | Repeated tool calls and chatter |

For scale: a two-agent check (Facilities asking Accounting) used about 12,000 tokens. The final full run used #101 53,658, #102 33,125, #103 46,322 tokens (133,105 total). In the first full attempt, the guardrail stopped #103 at 40 tool calls; see Full run results.

## Shop rules the harness enforces (from the scenario)

1. `desk.date_today` is "today" for every overdue and due-date check.
2. Vendor lead times come only from `vendors.lead_days`.
3. A vendor with an `open` invoice will not ship new product.
4. Every payment needs human approval. Payments are prepared by agents and executed only after a human approves.
5. A completed payment updates every related table: `payments`, `cash_accounts`, plus `invoices.status` or `leases.next_due`.
6. The pay tool refuses if cash is short, and balances can never go negative.
7. Cash only goes out; no revenue is modeled.
8. Reset the working database from the original before every full run.
9. Nothing is sent to customers or vendors. Drafts stay on the board.
10. Every agent uses `gpt-6-luna` through Portkey (`PORTKEY_API_KEY`), with no other model.
