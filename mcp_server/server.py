"""Campus Customs MCP server.

Every agent on the Campus Customs team reaches the shop database through these
tools, and so does the human dashboard. All tools work on the working copy
data/campus_customs_new.db and only return facts stored in it (plus arithmetic
on those facts).

Three "board" tables are added to the working copy on startup (never to the
original): payment_requests, drafts and board_notes. Agents can write to the
board; only a human can move money (pay_approved_request).
"""

import calendar
import os
import re
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

_DATA = Path(__file__).resolve().parent.parent / "data"
# CAMPUS_CUSTOMS_DB lets tests point the server at a scratch copy; normal runs use the working copy.
DB_PATH = Path(os.environ.get("CAMPUS_CUSTOMS_DB") or _DATA / "campus_customs_new.db")
ORIGINAL_DB_PATH = _DATA / "campus_customs.db"  # read-only source for resets

# Names the agents run under. A payment approver must be a human, not one of these.
AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}
HUMAN_NOTE_MARK = "[From the human desk]"  # only add_human_note may write this
# Internal money matters that must never appear in a draft to a customer.
CUSTOMER_DRAFT_BLOCKLIST = (
    "invoice", "unpaid", "overdue", "outstanding balance", "owe", "funding", "cash", "bank balance",
    "checking account", "margin", "our cost", "unit cost", "payment request", "a human", "manager approval",
)
TICKET_STATUSES = ("open", "in_progress", "awaiting_approval", "escalated", "resolved")

BOARD_SCHEMA = """
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL CHECK (kind IN ('invoice', 'rent', 'purchase_order')),
    ref_id INTEGER NOT NULL,
    payee TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    account TEXT NOT NULL,
    reason TEXT,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'rejected')),
    created_at TEXT NOT NULL,
    decided_at TEXT,
    decided_by TEXT,
    decision_note TEXT,
    payment_id INTEGER REFERENCES payments(id)
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL CHECK (kind IN ('customer_message', 'purchase_order')),
    author TEXT NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    vendor_id INTEGER,
    sku TEXT,
    size TEXT,
    qty INTEGER,
    unit_cost REAL,
    total REAL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS board_notes (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    author TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

mcp = FastMCP(
    "campus-customs",
    instructions=(
        "Tools for the Campus Customs shop database. desk.date_today is 'today' "
        "for all due-date checks. Never guess values that a tool does not return. "
        "Agents may prepare payments; only a human may pay."
    ),
)


# --------------------------------------------------------------------------- helpers


@contextmanager
def _connect(read_only: bool = True) -> Iterator[sqlite3.Connection]:
    """Open the working database (read-only unless a tool needs to write),
    commit on success, and always close the connection."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Working database not found: {DB_PATH}")
    mode = "ro" if read_only else "rw"
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def ensure_board_tables() -> None:
    """Create the board tables in the working copy if they are missing."""
    with _connect(read_only=False) as conn:
        conn.executescript(BOARD_SCHEMA)


def _today(conn: sqlite3.Connection) -> str:
    """The shop's 'today' comes from desk.date_today, never the system clock."""
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    if row is None:
        raise ValueError("desk.date_today is missing from the database.")
    return row["date_today"]


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _add_month(iso_day: str) -> str:
    d = date.fromisoformat(iso_day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def _now() -> str:
    """Wall-clock timestamp for board records (audit only, not shop 'today')."""
    return datetime.now().isoformat(timespec="seconds")


def _rows(cursor: sqlite3.Cursor) -> list[dict]:
    return [dict(r) for r in cursor]


def _ticket_exists(conn: sqlite3.Connection, ticket_id: int) -> bool:
    return conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is not None


def _vendor_invoices(conn: sqlite3.Connection, vendor_id: int, today: str) -> list[dict]:
    invoices = _rows(
        conn.execute(
            "SELECT id, amount, due_date, status, description FROM invoices "
            "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
            (vendor_id,),
        )
    )
    for inv in invoices:
        days = _days_between(inv["due_date"], today)
        inv["days_overdue"] = max(days, 0)
        inv["is_overdue"] = days > 0
    return invoices


def _pending_requests(conn: sqlite3.Connection) -> list[dict]:
    return _rows(
        conn.execute(
            "SELECT id, ticket_id, kind, ref_id, payee, amount, account, requested_by, created_at "
            "FROM payment_requests WHERE status = 'pending' ORDER BY id"
        )
    )


# --------------------------------------------------------------------------- shared lookups


@mcp.tool
def get_today() -> dict:
    """Return the shop's 'today' (desk.date_today) and any desk notes.
    Use this for every overdue or due-soon decision, never the real-world date.

    Reads: desk.
    """
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
    if row is None:
        return {"error": "desk.date_today is missing from the database."}
    return {"date_today": row["date_today"], "desk_notes": row["notes"]}


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket that is not resolved, oldest first.

    Reads: tickets.
    """
    with _connect() as conn:
        tickets = _rows(
            conn.execute(
                "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, "
                "status, created_at FROM tickets WHERE status != 'resolved' ORDER BY created_at"
            )
        )
    return {"count": len(tickets), "tickets": tickets}


@mcp.tool
def list_tickets() -> dict:
    """List every ticket (open or resolved) with its status, oldest first.
    `is_open` is true for any status other than 'resolved'.

    Reads: tickets.
    """
    with _connect() as conn:
        tickets = _rows(
            conn.execute(
                "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, "
                "status, notes, created_at FROM tickets ORDER BY created_at"
            )
        )
    for t in tickets:
        t["is_open"] = t["status"] != "resolved"
    return {
        "count": len(tickets),
        "open": sum(t["is_open"] for t in tickets),
        "resolved": sum(not t["is_open"] for t in tickets),
        "tickets": tickets,
    }


@mcp.tool
def list_payment_requests(status: Literal["pending", "paid", "rejected", "all"] = "pending") -> dict:
    """List payment requests on the board (the human approval queue), newest
    first, with the cash left if every pending request were paid.

    Reads: payment_requests, cash_accounts.
    """
    with _connect() as conn:
        sql = "SELECT * FROM payment_requests"
        params: tuple = ()
        if status != "all":
            sql += " WHERE status = ?"
            params = (status,)
        requests = _rows(conn.execute(sql + " ORDER BY id DESC", params))
        checking = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = 'checking'"
        ).fetchone()
        pending_total = sum(p["amount"] for p in _pending_requests(conn))
    balance = checking["balance"] if checking else None
    return {
        "status_filter": status,
        "count": len(requests),
        "requests": requests,
        "checking_balance": balance,
        "pending_total": round(pending_total, 2),
        "checking_after_pending": None if balance is None else round(balance - pending_total, 2),
    }


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Return one ticket, the lease or invoice it links to, and everything the
    team has already put on the board for it (notes, drafts, payment requests).
    Check the board first so work is not repeated.

    Reads: tickets, leases, invoices, vendors, board_notes, drafts, payment_requests.
    """
    with _connect() as conn:
        ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"error": f"Ticket {ticket_id} not found."}
        ticket = dict(ticket)
        linked: dict = {}
        if ticket["lease_id"] is not None:
            lease = conn.execute(
                "SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],)
            ).fetchone()
            linked["lease"] = dict(lease) if lease else None
        if ticket["invoice_id"] is not None:
            inv = conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i "
                "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ticket["invoice_id"],),
            ).fetchone()
            linked["invoice"] = dict(inv) if inv else None
        board = {
            "notes": _rows(
                conn.execute(
                    "SELECT author, note, created_at FROM board_notes WHERE ticket_id = ? ORDER BY id",
                    (ticket_id,),
                )
            ),
            "drafts": _rows(
                conn.execute(
                    "SELECT id, kind, author, recipient, subject, status, total FROM drafts "
                    "WHERE ticket_id = ? ORDER BY id",
                    (ticket_id,),
                )
            ),
            "payment_requests": _rows(
                conn.execute(
                    "SELECT id, kind, ref_id, payee, amount, status, requested_by FROM payment_requests "
                    "WHERE ticket_id = ? ORDER BY id",
                    (ticket_id,),
                )
            ),
        }
    return {"ticket": ticket, "linked": linked, "board": board}


# --------------------------------------------------------------------------- inventory


@mcp.tool
def check_stock(sku: str, size: str, qty_needed: int = 1) -> dict:
    """Check on-hand stock for one SKU and size and report any shortfall.

    Reads: inventory.
    """
    if qty_needed < 1:
        return {"error": "qty_needed must be at least 1."}
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory "
            "WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        if row is None:
            sizes = [
                r["size"]
                for r in conn.execute(
                    "SELECT size FROM inventory WHERE sku = ?", (sku,)
                )
            ]
            if sizes:
                return {"error": f"No size '{size}' for {sku}.", "sizes_on_file": sizes}
            return {"error": f"SKU '{sku}' is not in inventory."}

    shortfall = max(qty_needed - row["qty"], 0)
    return {
        "sku": row["sku"],
        "name": row["name"],
        "size": row["size"],
        "location": row["location"],
        "on_hand": row["qty"],
        "qty_needed": qty_needed,
        "shortfall": shortfall,
        "can_fill_from_stock": shortfall == 0,
    }


@mcp.tool
def list_inventory(sku: str | None = None) -> dict:
    """List stock rows (every size) for one SKU, or the whole stockroom if no
    SKU is given. Useful for finding in-stock alternatives.

    Reads: inventory.
    """
    with _connect() as conn:
        if sku:
            rows = _rows(
                conn.execute(
                    "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid",
                    (sku,),
                )
            )
            if not rows:
                return {"error": f"SKU '{sku}' is not in inventory."}
        else:
            rows = _rows(
                conn.execute("SELECT sku, name, size, qty, location FROM inventory ORDER BY rowid")
            )
    return {"rows": rows, "total_units": sum(r["qty"] for r in rows)}


# --------------------------------------------------------------------------- vendors and invoices


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with its specialty, lead time and whether an open
    invoice is blocking it from shipping new product.

    Reads: vendors, invoices, desk.
    """
    with _connect() as conn:
        today = _today(conn)
        vendors = _rows(conn.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id"))
        for v in vendors:
            open_invoices = _vendor_invoices(conn, v["id"], today)
            v["open_invoice_ids"] = [i["id"] for i in open_invoices]
            v["open_invoice_total"] = round(sum(i["amount"] for i in open_invoices), 2)
            v["blocked_from_shipping"] = bool(open_invoices)
    return {"today": today, "vendors": vendors}


@mcp.tool
def check_vendor_status(vendor_id: int) -> dict:
    """Check whether a vendor can ship new product. A vendor with any open,
    unpaid invoice will not ship. Also gives the lead time and the earliest
    arrival date counted from desk.date_today.

    Reads: vendors, invoices, desk.
    """
    with _connect() as conn:
        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        if vendor is None:
            return {"error": f"Vendor {vendor_id} not found."}
        today = _today(conn)
        open_invoices = _vendor_invoices(conn, vendor_id, today)

    lead = vendor["lead_days"]
    arrival = date.fromordinal(date.fromisoformat(today).toordinal() + lead).isoformat()
    blocked = bool(open_invoices)
    return {
        "vendor_id": vendor["id"],
        "name": vendor["name"],
        "specialty": vendor["specialty"],
        "lead_days": lead,
        "today": today,
        "open_invoices": open_invoices,
        "blocked_from_shipping": blocked,
        "reason": (
            f"Open invoice(s) {[i['id'] for i in open_invoices]} must be paid before this vendor ships."
            if blocked
            else "No open invoices; vendor can ship."
        ),
        "earliest_arrival_if_ordered_today": None if blocked else arrival,
        "earliest_arrival_if_unblocked_and_ordered_today": arrival,
    }


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Return one invoice with its vendor, how many days it is overdue as of
    desk.date_today, and any payment requests already filed for it.

    Reads: invoices, vendors, desk, payment_requests.
    """
    with _connect() as conn:
        inv = conn.execute(
            "SELECT i.*, v.name AS vendor_name, v.lead_days FROM invoices i "
            "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        if inv is None:
            return {"error": f"Invoice {invoice_id} not found."}
        today = _today(conn)
        requests = _rows(
            conn.execute(
                "SELECT id, amount, status, requested_by, created_at FROM payment_requests "
                "WHERE kind = 'invoice' AND ref_id = ? ORDER BY id",
                (invoice_id,),
            )
        )
    inv = dict(inv)
    days = _days_between(inv["due_date"], today)
    return {
        **inv,
        "today": today,
        "is_overdue": inv["status"] == "open" and days > 0,
        "days_overdue": max(days, 0) if inv["status"] == "open" else 0,
        "blocks_vendor_shipping": inv["status"] == "open",
        "payment_requests": requests,
    }


# --------------------------------------------------------------------------- cash, pricing, leases


@mcp.tool
def get_cash_position() -> dict:
    """Show cash on hand per account, every pending payment request, and the
    cash left if all pending requests were paid. No revenue is modeled: cash
    only goes out.

    Reads: cash_accounts, payment_requests.
    """
    with _connect() as conn:
        accounts = _rows(conn.execute("SELECT name, balance, date FROM cash_accounts ORDER BY name"))
        pending = _pending_requests(conn)
    for acct in accounts:
        committed = round(sum(p["amount"] for p in pending if p["account"] == acct["name"]), 2)
        acct["pending_requests_total"] = committed
        acct["available_after_pending"] = round(acct["balance"] - committed, 2)
        acct["overcommitted"] = acct["available_after_pending"] < 0
    return {"accounts": accounts, "pending_requests": pending}


@mcp.tool
def check_discount_margin(sku: str, qty: int, discount_pct: float = 0.0) -> dict:
    """Price an order of one SKU at an optional discount off list price and
    report the unit and total margin.

    Reads: pricing.
    """
    if qty < 1:
        return {"error": "qty must be at least 1."}
    if not 0 <= discount_pct < 100:
        return {"error": "discount_pct must be between 0 and 100 (exclusive of 100)."}
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
    if row is None:
        return {"error": f"No pricing on file for SKU '{sku}'."}

    unit_cost = row["unit_cost"]
    list_price = row["list_price"]
    unit_price = round(list_price * (1 - discount_pct / 100), 2)
    unit_margin = round(unit_price - unit_cost, 2)
    return {
        "sku": row["sku"],
        "qty": qty,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "discount_pct": discount_pct,
        "unit_price": unit_price,
        "unit_margin": unit_margin,
        "margin_pct": round(unit_margin / unit_price * 100, 1),
        "total_price": round(unit_price * qty, 2),
        "total_cost": round(unit_cost * qty, 2),
        "total_margin": round(unit_margin * qty, 2),
        "below_cost": unit_margin < 0,
        "max_discount_pct_at_breakeven": round((1 - unit_cost / list_price) * 100, 1),
    }


@mcp.tool
def get_lease_rent_status(lease_id: int) -> dict:
    """Report a lease's rent, due date, days until due vs. desk.date_today,
    and whether current cash could cover it.

    Reads: leases, desk, cash_accounts.
    """
    with _connect() as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
            "FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            return {"error": f"Lease {lease_id} not found."}
        today = _today(conn)
        accounts = [
            {"name": r["name"], "balance": r["balance"], "as_of": r["date"]}
            for r in conn.execute("SELECT name, balance, date FROM cash_accounts")
        ]

    days_until_due = _days_between(today, lease["next_due"])
    rent = lease["monthly_rent"]
    return {
        "lease_id": lease["id"],
        "space_name": lease["space_name"],
        "landlord": lease["landlord"],
        "monthly_rent": rent,
        "next_due": lease["next_due"],
        "today": today,
        "days_until_due": days_until_due,
        "is_overdue": days_until_due < 0,
        "notes": lease["notes"],
        "cash_accounts": accounts,
        "any_account_covers_rent": any(a["balance"] >= rent for a in accounts),
    }


# --------------------------------------------------------------------------- board writes (agents)


@mcp.tool
def request_payment(
    kind: Literal["invoice", "rent", "purchase_order"],
    ref_id: int,
    ticket_id: int | None = None,
    reason: str = "",
    account: str = "checking",
    author: str = "unknown",
) -> dict:
    """File a payment request on the board for a human to approve. This does
    NOT pay anything. The amount is taken from the records, never typed in:
    kind='invoice' -> invoices.amount (ref_id = invoice id),
    kind='rent' -> leases.monthly_rent (ref_id = lease id),
    kind='purchase_order' -> drafts.total (ref_id = purchase-order draft id).
    Refuses duplicates. `author` is filled in automatically.

    Reads: invoices, leases, drafts, vendors, cash_accounts, payment_requests.
    Writes: payment_requests.
    """
    with _connect(read_only=False) as conn:
        if ticket_id is not None and not _ticket_exists(conn, ticket_id):
            return {"error": f"Ticket {ticket_id} not found."}
        if conn.execute("SELECT 1 FROM cash_accounts WHERE name = ?", (account,)).fetchone() is None:
            return {"error": f"Cash account '{account}' not found."}

        if kind == "invoice":
            row = conn.execute(
                "SELECT i.amount, i.status, v.name FROM invoices i "
                "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ref_id,),
            ).fetchone()
            if row is None:
                return {"error": f"Invoice {ref_id} not found."}
            if row["status"] != "open":
                return {"error": f"Invoice {ref_id} is '{row['status']}', not open; nothing to pay."}
            amount, payee = row["amount"], row["name"]
        elif kind == "rent":
            row = conn.execute(
                "SELECT monthly_rent, landlord, next_due FROM leases WHERE id = ?", (ref_id,)
            ).fetchone()
            if row is None:
                return {"error": f"Lease {ref_id} not found."}
            amount, payee = row["monthly_rent"], row["landlord"]
            reason = reason or f"Rent due {row['next_due']}"
        else:
            row = conn.execute(
                "SELECT d.total, d.status, v.name FROM drafts d JOIN vendors v ON v.id = d.vendor_id "
                "WHERE d.id = ? AND d.kind = 'purchase_order'",
                (ref_id,),
            ).fetchone()
            if row is None:
                return {"error": f"Purchase-order draft {ref_id} not found."}
            amount, payee = row["total"], row["name"]

        duplicate = conn.execute(
            "SELECT id, status FROM payment_requests WHERE kind = ? AND ref_id = ? "
            "AND status IN ('pending', 'paid')",
            (kind, ref_id),
        ).fetchone()
        if duplicate and not (kind == "rent" and duplicate["status"] == "paid"):
            return {
                "error": "Duplicate: a request for this already exists.",
                "existing_request_id": duplicate["id"],
                "existing_status": duplicate["status"],
            }

        cur = conn.execute(
            "INSERT INTO payment_requests (ticket_id, kind, ref_id, payee, amount, account, reason, "
            "requested_by, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (ticket_id, kind, ref_id, payee, amount, account, reason, author, _now()),
        )
        balance = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()["balance"]
        committed = sum(p["amount"] for p in _pending_requests(conn) if p["account"] == account)

    return {
        "request_id": cur.lastrowid,
        "status": "pending",
        "kind": kind,
        "ref_id": ref_id,
        "payee": payee,
        "amount": amount,
        "account": account,
        "note": "Filed for human approval. No money has moved.",
        "account_balance": balance,
        "all_pending_total": round(committed, 2),
        "available_after_pending": round(balance - committed, 2),
        "exceeds_available_cash": balance - committed < 0,
    }


@mcp.tool
def draft_purchase_order(
    vendor_id: int,
    sku: str,
    size: str,
    qty: int,
    ticket_id: int | None = None,
    note: str = "",
    author: str = "unknown",
) -> dict:
    """Draft a restock purchase order on the board. Cost comes from
    pricing.unit_cost. Flags (but still drafts) when the vendor is blocked by an
    open invoice. Nothing is sent to the vendor. `author` is filled in automatically.

    Reads: vendors, pricing, inventory, invoices, desk. Writes: drafts.
    """
    if qty < 1:
        return {"error": "qty must be at least 1."}
    with _connect(read_only=False) as conn:
        if ticket_id is not None and not _ticket_exists(conn, ticket_id):
            return {"error": f"Ticket {ticket_id} not found."}
        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        if vendor is None:
            return {"error": f"Vendor {vendor_id} not found."}
        item = conn.execute(
            "SELECT name FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        if item is None:
            return {"error": f"{sku} size {size} is not an inventory item."}
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"error": f"No pricing on file for SKU '{sku}'."}
        open_invoices = _vendor_invoices(conn, vendor_id, _today(conn))

        unit_cost = price["unit_cost"]
        total = round(unit_cost * qty, 2)
        body = (
            f"Purchase order: {qty} x {item['name']} ({sku}, size {size}) at "
            f"${unit_cost:.2f} each = ${total:.2f}. Vendor lead time {vendor['lead_days']} days."
            + (f" Note: {note}" if note else "")
        )
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, kind, author, recipient, subject, body, vendor_id, sku, "
            "size, qty, unit_cost, total, status, created_at) "
            "VALUES (?, 'purchase_order', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)",
            (
                ticket_id, author, vendor["name"], f"PO: {qty} x {sku} {size}", body,
                vendor_id, sku, size, qty, unit_cost, total, _now(),
            ),
        )
    return {
        "draft_id": cur.lastrowid,
        "status": "draft",
        "vendor": vendor["name"],
        "vendor_specialty": vendor["specialty"],
        "sku": sku,
        "size": size,
        "qty": qty,
        "unit_cost": unit_cost,
        "total": total,
        "lead_days": vendor["lead_days"],
        "vendor_blocked_by_invoices": [i["id"] for i in open_invoices],
        "note": (
            "Draft only; not sent. To pay it, file request_payment(kind='purchase_order', "
            f"ref_id={cur.lastrowid}) for human approval."
            + (" Vendor will not ship until its open invoice is paid." if open_invoices else "")
        ),
    }


@mcp.tool
def draft_customer_message(
    ticket_id: int,
    recipient: str,
    subject: str,
    body: str,
    author: str = "unknown",
) -> dict:
    """Save a message to a customer or requester as a DRAFT on the board for a
    human to review. Nothing is emailed or sent. `author` is filled in automatically.

    Reads: tickets. Writes: drafts.
    """
    if not body.strip():
        return {"error": "body must not be empty."}
    text = f"{subject} {body}".lower()
    leaks = sorted({w for w in CUSTOMER_DRAFT_BLOCKLIST if re.search(rf"\b{re.escape(w)}\b", text)})
    if leaks:
        return {
            "error": "Draft not saved: customer messages can't mention internal money matters "
            f"({', '.join(leaks)}). Rephrase: say what we can do now, what we can't confirm yet, "
            "and that we'll follow up.",
            "blocked_terms": leaks,
        }
    with _connect(read_only=False) as conn:
        if not _ticket_exists(conn, ticket_id):
            return {"error": f"Ticket {ticket_id} not found."}
        cur = conn.execute(
            "INSERT INTO drafts (ticket_id, kind, author, recipient, subject, body, status, created_at) "
            "VALUES (?, 'customer_message', ?, ?, ?, ?, 'draft', ?)",
            (ticket_id, author, recipient, subject, body, _now()),
        )
    return {
        "draft_id": cur.lastrowid,
        "status": "draft",
        "note": "Saved on the board for human review. Not sent.",
    }


@mcp.tool
def add_board_note(ticket_id: int, note: str, author: str = "unknown") -> dict:
    """Add a short note to a ticket on the board (findings, handoffs, what is
    still missing). `author` is filled in automatically.

    Reads: tickets. Writes: board_notes.
    """
    if not note.strip():
        return {"error": "note must not be empty."}
    if HUMAN_NOTE_MARK.lower() in note.lower():
        return {"error": f"Agents can't write '{HUMAN_NOTE_MARK}' notes; that mark is reserved for people."}
    with _connect(read_only=False) as conn:
        if not _ticket_exists(conn, ticket_id):
            return {"error": f"Ticket {ticket_id} not found."}
        cur = conn.execute(
            "INSERT INTO board_notes (ticket_id, author, note, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, author, note, _now()),
        )
    return {"note_id": cur.lastrowid, "ticket_id": ticket_id}


@mcp.tool
def set_ticket_status(
    ticket_id: int,
    status: Literal["in_progress", "awaiting_approval", "escalated", "resolved"],
    decision: str,
    author: str = "unknown",
) -> dict:
    """Set a ticket's status and record the decision on the board. A ticket
    with a pending payment request cannot be marked 'resolved'; use
    'awaiting_approval'. `author` is filled in automatically.

    Reads: tickets, payment_requests. Writes: tickets.status, board_notes.
    """
    with _connect(read_only=False) as conn:
        if not _ticket_exists(conn, ticket_id):
            return {"error": f"Ticket {ticket_id} not found."}
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM payment_requests WHERE ticket_id = ? AND status = 'pending'",
            (ticket_id,),
        ).fetchone()["n"]
        if HUMAN_NOTE_MARK.lower() in decision.lower():
            return {"error": f"'{HUMAN_NOTE_MARK}' is reserved for people."}
        if status == "resolved" and pending:
            return {
                "error": f"Ticket {ticket_id} has {pending} pending payment request(s) waiting on a "
                "human. Use 'awaiting_approval' instead of 'resolved'."
            }
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        conn.execute(
            "INSERT INTO board_notes (ticket_id, author, note, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, author, f"Status -> {status}. Decision: {decision}", _now()),
        )
    return {"ticket_id": ticket_id, "status": status}


# --------------------------------------------------------------------------- human-only money tools
# These are never given to an agent; the backend only exposes them to the human dashboard.


@mcp.tool(tags={"human_only"})
def pay_approved_request(request_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Pay a pending payment request after a person approves it.
    Refuses if cash is short (no balance may go negative), if the approver is
    missing or is an agent, or if the vendor of a purchase order is still
    blocked. On success it updates payments, cash_accounts, and the invoice
    (status='paid'), lease (next_due + 1 month) or purchase-order draft.

    Reads/Writes: payment_requests, payments, cash_accounts, invoices, leases, drafts.
    """
    approver = approved_by.strip()
    if not approver or approver.lower() in AGENT_NAMES:
        return {"error": "Refused: a named human must approve payments."}
    with _connect(read_only=False) as conn:
        req = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return {"error": f"Payment request {request_id} not found."}
        if req["status"] != "pending":
            return {"error": f"Refused: request {request_id} is already '{req['status']}'."}
        acct = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (req["account"],)
        ).fetchone()
        if acct is None:
            return {"error": f"Cash account '{req['account']}' not found."}
        amount, balance = req["amount"], acct["balance"]
        if amount > balance:
            return {
                "error": "Refused: not enough cash. Balances may not go negative.",
                "amount": amount,
                "balance": balance,
                "short_by": round(amount - balance, 2),
            }
        today = _today(conn)

        if req["kind"] == "invoice":
            inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (req["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                return {"error": f"Refused: invoice {req['ref_id']} is not open."}
        elif req["kind"] == "purchase_order":
            po = conn.execute("SELECT vendor_id FROM drafts WHERE id = ?", (req["ref_id"],)).fetchone()
            if po is None:
                return {"error": f"Refused: purchase-order draft {req['ref_id']} not found."}
            blockers = _vendor_invoices(conn, po["vendor_id"], today)
            if blockers:
                return {
                    "error": "Refused: vendor has open invoice(s) and will not ship. Pay those first.",
                    "open_invoice_ids": [i["id"] for i in blockers],
                }

        new_balance = round(balance - amount, 2)
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (req["kind"], req["ref_id"], amount, req["account"], today, approver),
        )
        payment_id = cur.lastrowid
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, today, req["account"]),
        )
        updated: dict = {"cash_accounts": {req["account"]: new_balance}}
        if req["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
            updated["invoices"] = {req["ref_id"]: "paid"}
        elif req["kind"] == "rent":
            lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (req["ref_id"],)).fetchone()
            next_due = _add_month(lease["next_due"])
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (next_due, req["ref_id"]))
            updated["leases"] = {req["ref_id"]: {"next_due": next_due}}
        else:
            conn.execute("UPDATE drafts SET status = 'paid' WHERE id = ?", (req["ref_id"],))
            updated["drafts"] = {req["ref_id"]: "paid"}
        conn.execute(
            "UPDATE payment_requests SET status = 'paid', decided_at = ?, decided_by = ?, payment_id = ? "
            "WHERE id = ?",
            (_now(), approver, payment_id, request_id),
        )
    return {
        "request_id": request_id,
        "status": "paid",
        "payment_id": payment_id,
        "amount": amount,
        "paid_at": today,
        "approved_by": approver,
        "balance_before": balance,
        "balance_after": new_balance,
        "updated": updated,
    }


@mcp.tool(tags={"human_only"})
def reject_payment_request(request_id: int, decided_by: str, reason: str = "") -> dict:
    """HUMAN ONLY. Reject a pending payment request. No money moves.

    Writes: payment_requests.
    """
    decider = decided_by.strip()
    if not decider or decider.lower() in AGENT_NAMES:
        return {"error": "Refused: a named human must decide payment requests."}
    with _connect(read_only=False) as conn:
        req = conn.execute(
            "SELECT status FROM payment_requests WHERE id = ?", (request_id,)
        ).fetchone()
        if req is None:
            return {"error": f"Payment request {request_id} not found."}
        if req["status"] != "pending":
            return {"error": f"Request {request_id} is already '{req['status']}'."}
        conn.execute(
            "UPDATE payment_requests SET status = 'rejected', decided_at = ?, decided_by = ?, "
            "decision_note = ? WHERE id = ?",
            (_now(), decider, reason, request_id),
        )
    return {"request_id": request_id, "status": "rejected", "decided_by": decider}


@mcp.tool(tags={"human_only"})
def add_human_note(ticket_id: int, author: str, note: str) -> dict:
    """HUMAN ONLY. Pin a signed note from a person to a ticket (the dashboard's
    suggestion box). Agents see it on the board the next time they work the ticket.

    Reads: tickets. Writes: board_notes.
    """
    who = author.strip()
    if not who or who.lower() in AGENT_NAMES:
        return {"error": "Refused: notes from the human desk must be signed by a person."}
    if not note.strip():
        return {"error": "note must not be empty."}
    with _connect(read_only=False) as conn:
        if not _ticket_exists(conn, ticket_id):
            return {"error": f"Ticket {ticket_id} not found."}
        cur = conn.execute(
            "INSERT INTO board_notes (ticket_id, author, note, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, who, f"{HUMAN_NOTE_MARK} {note.strip()}", _now()),
        )
    return {"note_id": cur.lastrowid, "ticket_id": ticket_id, "author": who}


@mcp.tool(tags={"human_only"})
def resolve_ticket(ticket_id: int, resolved_by: str, note: str = "") -> dict:
    """HUMAN ONLY. Mark a ticket resolved after a person has reviewed it.
    Refused while the ticket still has a pending payment request.

    Reads: tickets, payment_requests. Writes: tickets.status, board_notes.
    """
    who = resolved_by.strip()
    if not who or who.lower() in AGENT_NAMES:
        return {"error": "Refused: a named human must resolve tickets."}
    with _connect(read_only=False) as conn:
        if not _ticket_exists(conn, ticket_id):
            return {"error": f"Ticket {ticket_id} not found."}
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM payment_requests WHERE ticket_id = ? AND status = 'pending'",
            (ticket_id,),
        ).fetchone()["n"]
        if pending:
            return {"error": f"Refused: ticket {ticket_id} still has {pending} pending payment request(s)."}
        conn.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (ticket_id,))
        conn.execute(
            "INSERT INTO board_notes (ticket_id, author, note, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, who, f"Status -> resolved by {who}." + (f" {note}" if note else ""), _now()),
        )
    return {"ticket_id": ticket_id, "status": "resolved", "resolved_by": who}


@mcp.tool(tags={"human_only"})
def reset_shop_database(confirm: bool = False) -> dict:
    """HUMAN ONLY. Restore the working copy from the original
    data/campus_customs.db (wiping all payments, requests, drafts and notes made
    since), then recreate the empty board tables. Run before every full run.
    The original file is only read, never changed.

    Reads: data/campus_customs.db. Writes: data/campus_customs_new.db (every table).
    """
    if not confirm:
        return {"error": "Pass confirm=true to reset the working database."}
    if not ORIGINAL_DB_PATH.exists():
        return {"error": f"Original database not found: {ORIGINAL_DB_PATH}"}
    # Build the fresh copy (with board tables) on the side, then swap it in
    # atomically, so a dashboard poll never sees a half-reset database.
    tmp = DB_PATH.with_name(f".{DB_PATH.name}.resetting")
    shutil.copyfile(ORIGINAL_DB_PATH, tmp)
    conn = sqlite3.connect(tmp)
    try:
        conn.executescript(BOARD_SCHEMA)
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp, DB_PATH)
    with _connect() as conn:
        counts = {
            t: conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            for t in ("tickets", "invoices", "payments", "payment_requests", "drafts", "board_notes")
        }
        cash = _rows(conn.execute("SELECT name, balance FROM cash_accounts"))
    return {"reset": True, "from": ORIGINAL_DB_PATH.name, "to": DB_PATH.name, "row_counts": counts, "cash": cash}


ensure_board_tables()

if __name__ == "__main__":
    mcp.run()
