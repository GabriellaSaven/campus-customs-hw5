# Campus Customs MCP Server

**Purpose:** This server is the only way into the shop's data. The Campus Customs agent team (Boss, Inventory, Accounting, Facilities and Customer Service) and the human dashboard both reach the database through it. Nothing queries the database directly. Every tool returns only facts stored in the database, plus simple arithmetic on them.

**Database:** `../data/campus_customs_new.db` is the working copy (tests can point the server at a scratch copy with the `CAMPUS_CUSTOMS_DB` environment variable). The original `data/campus_customs.db` is never written to; `reset_shop_database` copies it over the working copy before each full run. The shop's "today" is `desk.date_today`, never the computer's clock.

**Board tables:** on startup the server adds three tables to the working copy only: `payment_requests`, `drafts` and `board_notes`. Agents write their work there, and it stays on the board until a human acts.

**Built with:** [FastMCP](https://gofastmcp.com), in `server.py`.

## Tools (23)

### Lookups (read-only)
| Tool | Reads | Returns |
|---|---|---|
| `get_today()` | `desk` | The shop's date and desk notes |
| `list_open_tickets()` | `tickets` | Every ticket not yet resolved |
| `list_tickets()` | `tickets` | Every ticket with its status and `is_open` (used by the dashboard) |
| `list_payment_requests(status)` | `payment_requests`, `cash_accounts` | The approval queue and cash left after pending requests (used by the dashboard) |
| `get_ticket(ticket_id)` | `tickets`, `leases`, `invoices`, `vendors`, board tables | The ticket, its linked lease or invoice, and everything already on the board for it |
| `check_stock(sku, size, qty_needed=1)` | `inventory` | On hand, location, shortfall |
| `list_inventory(sku=None)` | `inventory` | Every size of a SKU, or the whole stockroom |
| `list_vendors()` | `vendors`, `invoices`, `desk` | Specialty, lead days, open invoices, whether the vendor is blocked from shipping |
| `check_vendor_status(vendor_id)` | `vendors`, `invoices`, `desk` | Blocked or not (and why), lead days, earliest arrival date |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk`, `payment_requests` | Amount, due date, days overdue, any requests already filed |
| `get_cash_position()` | `cash_accounts`, `payment_requests` | Balance, pending requests, and cash left after them |
| `check_discount_margin(sku, qty, discount_pct=0)` | `pricing` | Price, margin and margin %, a below-cost flag, the break-even discount |
| `get_lease_rent_status(lease_id)` | `leases`, `desk`, `cash_accounts` | Rent, due date, days until due, overdue flag, whether cash covers it |

### Board writes (agents; nothing is sent and no money moves)
| Tool | Writes | Notes |
|---|---|---|
| `request_payment(kind, ref_id, ticket_id, reason, account)` | `payment_requests` | The amount comes from the invoice, lease or purchase-order record. Duplicates are refused. |
| `draft_purchase_order(vendor_id, sku, size, qty, ticket_id, note)` | `drafts` | Cost comes from `pricing.unit_cost`. Flags a vendor that's blocked by an open invoice. |
| `draft_customer_message(ticket_id, recipient, subject, body)` | `drafts` | Saved as a draft for human review. Refuses drafts that mention internal money matters (invoice, funding, cash, margin…). |
| `add_board_note(ticket_id, note)` | `board_notes` | Findings and handoffs |
| `set_ticket_status(ticket_id, status, decision)` | `tickets.status`, `board_notes` | Can't mark a ticket `resolved` while a payment is pending |

The board-write tools also take an `author` argument. The backend fills it in with the calling agent's name and hides it from the model.

### Human only (the dashboard calls these; no agent ever gets them)
| Tool | Writes | Notes |
|---|---|---|
| `pay_approved_request(request_id, approved_by)` | `payments`, `cash_accounts`, `payment_requests`, plus `invoices.status` / `leases.next_due` / the PO draft | Needs a named human approver. Refuses if cash is short (no negative balances) or if a PO's vendor is still blocked. |
| `reject_payment_request(request_id, decided_by, reason)` | `payment_requests` | No money moves |
| `resolve_ticket(ticket_id, resolved_by, note)` | `tickets.status`, `board_notes` | A person closes a reviewed ticket; refused while a payment is pending |
| `add_human_note(ticket_id, author, note)` | `board_notes` | The dashboard's suggestion box. Writes a `[From the human desk]` note; agents can't use that mark |
| `reset_shop_database(confirm)` | the whole working copy | Restores it from the original and recreates the board tables |

## Setup on any computer

From the `Homework 5` folder:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

`.mcp.json` at the project root registers this server as `campus-customs`. It uses `${CLAUDE_PROJECT_DIR:-.}` instead of fixed paths, so it works wherever the project is copied. The backend (`backend/mcp_client.py`) launches the server from that same file.
