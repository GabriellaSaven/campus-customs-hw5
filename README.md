# Campus Customs Multi-Agent Operations (Homework 5)

An agent team that runs a campus merch shop's ticket board. It has three pieces that talk to each other:

1. **MCP server** (`mcp_server/`, FastMCP): the only way into the shop database, with 23 tools.
2. **FastAPI backend with a multi-agent team** (`backend/`, PydanticAI): Boss, Inventory, Accounting, Facilities and Customer Service. Any agent can delegate to any other. Every agent runs on **`gpt-6-luna` through Portkey**.
3. **React dashboard** (`frontend/`, React + Vite + TypeScript): a person watches the agents work, approves payments and resolves tickets.

Agents only *prepare* payments; a human approves them on the dashboard. No email is sent and no vendor is contacted. Drafts stay on the board.

## Layout

```
hw5/
├── AI_prompts.md            prompt log, one section per problem
├── requirements.txt         Python dependencies
├── .env.example             copy to .env and add PORTKEY_API_KEY
├── .gitignore
├── .mcp.json                how to launch the MCP server (used by the backend and Claude Code)
├── README.md
├── data/
│   ├── campus_customs.db       ORIGINAL database (never written to)
│   └── campus_customs_new.db   WORKING copy (the app reads and writes this one)
├── mcp_server/
│   ├── server.py
│   └── README.md            full tool list
├── frontend/                React + Vite + TypeScript dashboard
├── backend/
│   ├── main.py              FastAPI routes
│   ├── models.py            data types
│   ├── agents.py            the five agents, delegation, agent loop, audit logging
│   ├── config.py            model (gpt-6-luna), Portkey, tool access, cost limits
│   ├── mcp_client.py        connects to the MCP server via .mcp.json
│   ├── audit.py             append-only output/audit_trail.json
│   ├── run_team.py          command-line runner
│   └── prompts/
│       ├── boss.md
│       ├── inventory.md
│       ├── accounting.md
│       ├── facilities.md
│       └── customer_service.md
├── output/
│   ├── harness.md           tables, MCP tools, agents, routes, dashboard, safety rules
│   ├── mcp_smoke.json
│   ├── desk_tickets.html    Expected vs. Actual per ticket, Cash, Reflection
│   ├── design.md
│   ├── resolved_tickets.json
│   ├── resolved_board.html  screenshots of the board for 101, 102 and 103
│   ├── audit_trail.json
│   ├── github_url.txt
│   └── screenshots/         full-size board images used by resolved_board.html
├── scripts/                 report builders (read the audit trail and the API only)
└── tests/                   MCP smoke test, prompt/tool check, customer-draft privacy test
```

## Setup (once)

You'll need Python 3.12+ and Node 20+. From this folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env              # then put your PORTKEY_API_KEY in .env
cd frontend && npm install && cd ..
```

The backend reads `PORTKEY_API_KEY` from `.env` in this folder. If that file doesn't exist, it uses the `.env` one folder up.

## 1. Clean database: copy the original to the working copy

`data/campus_customs.db` is the original and is never changed. The app uses `data/campus_customs_new.db`. This repo ships the working copy in its **finished state** after the graded run (all three tickets resolved, checking at $160.00).

For a clean start, with the servers **stopped**, copy the original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

When the MCP server next starts, it adds its three empty board tables to the working copy: `payment_requests`, `drafts` and `board_notes`. (To reset while the servers are running, use step 5 instead.)

## 2. Start the MCP server

The backend **starts the MCP server for you** (over stdio, as described in `.mcp.json`), so for normal use you can go straight to step 3. To start or check it on its own:

```bash
.venv/bin/python mcp_server/server.py              # runs the server over stdio (Ctrl-C to stop)
.venv/bin/python tests/mcp_smoke_test.py           # launches it from .mcp.json and checks 3 tools against the DB
.venv/bin/python tests/check_prompt_tools.py       # every tool named in a prompt exists and is given to that agent
```

Claude Code also picks the server up from `.mcp.json` as `campus-customs`.

## 3. Start the FastAPI backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

- API: http://localhost:8000 (interactive docs at http://localhost:8000/docs)
- Main routes: `GET /api/tickets`, `POST /api/tickets/{id}/run`, `GET /api/events`, `POST /api/payment-requests/{id}/approve`, `GET /api/cash`, `POST /api/reset`. The full list is in `output/harness.md`.

## 4. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The dashboard calls the backend at http://localhost:8000; CORS allows the Vite origin.

## 5. Reset the database before a full three-ticket run

Always reset before a full run, so cash starts at $3,400.00 and all three tickets are open. Use any one of these (they all go through the MCP server's human-only `reset_shop_database` tool):

- On the dashboard: **Start a fresh day** (top right).
- `curl -X POST http://localhost:8000/api/reset`
- `.venv/bin/python -m backend.run_team --reset`

The audit trail is never wiped; a reset adds a `shop_reset` marker to it.

## 6. Run the three tickets

On the dashboard, open each file **oldest first (101 → 102 → 103)** and press **Hand it to Ron →**. Later tickets rely on the payment requests filed by earlier ones. Then:

1. Type your name on the clipboard ("Sign here").
2. **Sign & pay** the checks you approve. Approving a ticket's last pending payment resolves that ticket.
3. For a ticket left for review with nothing to pay (e.g. 103), press **Close the file**.

From the command line instead: `.venv/bin/python -m backend.run_team --all --reset`. Approvals still happen on the dashboard or through `POST /api/payment-requests/{id}/approve`.

**Graded run:** $3,400.00 − $840.00 (invoice #501) − $2,400.00 (rent) − $0.00 (#103, restock not affordable) = **$160.00**, which matches `cash_accounts`. Details are in `output/desk_tickets.html` (Cash tab) and `output/resolved_tickets.json`.

## Safety rules (summary)

- The shop's "today" is `desk.date_today`, never the computer clock.
- A vendor with an open, unpaid invoice won't ship.
- Agents can't pay. Only the human-only `pay_approved_request` tool moves money. It needs a named person, refuses if cash is short (no negative balances), and updates `payments`, `cash_accounts`, and the invoice, lease or purchase order.
- Customer drafts can't mention internal money matters; the drafting tool rejects them.
- Per-ticket cost limits: 40 model calls, 50 tool calls, 150k tokens, delegation depth 2.

The full list is in `output/harness.md`.
