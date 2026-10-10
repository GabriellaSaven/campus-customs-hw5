"""Smoke-test the Campus Customs MCP server over a real stdio connection.

Launches the server exactly as configured in .mcp.json, calls each tool with
arguments taken from the open tickets, then re-reads data/campus_customs_new.db
directly with SQL to confirm every tool value matches the database.
Writes the evidence to output/mcp_smoke.json.
"""

import asyncio
import json
import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path

from fastmcp import Client

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "campus_customs_new.db"
OUT_PATH = ROOT / "output" / "mcp_smoke.json"
SERVER = "campus-customs"
DISCOUNT_TEST_PCT = 10.0  # ticket 103 asks for "a bulk discount" with no %, so test 10%


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


def ticket(ticket_id: int) -> dict:
    return query("SELECT * FROM tickets WHERE id = ?", (ticket_id,))[0]


def build_cases() -> list[dict]:
    t101, t102, t103 = ticket(101), ticket(102), ticket(103)
    today = query("SELECT date_today FROM desk")[0]["date_today"]

    # --- 101: check_stock -------------------------------------------------
    inv = query(
        "SELECT qty, name, location FROM inventory WHERE sku = ? AND size = ?",
        (t101["sku"], t101["size"]),
    )[0]
    case_101 = {
        "ticket_id": 101,
        "prompt": (
            f"Ticket 101: {t101['requester']} wants {t101['qty']} {inv['name']} in "
            f"size {t101['size']}. How many do we have on hand, and is there a shortfall?"
        ),
        "tool": "check_stock",
        "arguments": {"sku": t101["sku"], "size": t101["size"], "qty_needed": t101["qty"]},
        "db_sql": "SELECT qty, name, location FROM inventory WHERE sku = ? AND size = ?",
        "expected": {
            "on_hand": inv["qty"],
            "name": inv["name"],
            "location": inv["location"],
            "shortfall": max(t101["qty"] - inv["qty"], 0),
        },
    }

    # --- 102: get_lease_rent_status --------------------------------------
    lease = query("SELECT * FROM leases WHERE id = ?", (t102["lease_id"],))[0]
    cash = query("SELECT balance FROM cash_accounts WHERE name = 'checking'")[0]
    days = (date.fromisoformat(lease["next_due"]) - date.fromisoformat(today)).days
    case_102 = {
        "ticket_id": 102,
        "prompt": (
            f"Ticket 102: {t102['requester']} says rent is due. How much is the rent on "
            f"lease {t102['lease_id']}, when is it due, is it overdue, and can our cash cover it?"
        ),
        "tool": "get_lease_rent_status",
        "arguments": {"lease_id": t102["lease_id"]},
        "db_sql": (
            "SELECT * FROM leases WHERE id = ?; SELECT date_today FROM desk; "
            "SELECT balance FROM cash_accounts WHERE name = 'checking'"
        ),
        "expected": {
            "monthly_rent": lease["monthly_rent"],
            "landlord": lease["landlord"],
            "next_due": lease["next_due"],
            "today": today,
            "days_until_due": days,
            "is_overdue": days < 0,
            "checking_balance": cash["balance"],
            "any_account_covers_rent": cash["balance"] >= lease["monthly_rent"],
        },
    }

    # --- 103: check_discount_margin --------------------------------------
    price = query("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (t103["sku"],))[0]
    unit_price = round(price["list_price"] * (1 - DISCOUNT_TEST_PCT / 100), 2)
    unit_margin = round(unit_price - price["unit_cost"], 2)
    case_103 = {
        "ticket_id": 103,
        "prompt": (
            f"Ticket 103: {t103['requester']} wants {t103['qty']} {t103['sku']} hoodies "
            f"and is asking for a bulk discount. What margin do we keep at "
            f"{DISCOUNT_TEST_PCT:g}% off list?"
        ),
        "tool": "check_discount_margin",
        "arguments": {"sku": t103["sku"], "qty": t103["qty"], "discount_pct": DISCOUNT_TEST_PCT},
        "db_sql": "SELECT unit_cost, list_price FROM pricing WHERE sku = ?",
        "expected": {
            "unit_cost": price["unit_cost"],
            "list_price": price["list_price"],
            "unit_price": unit_price,
            "unit_margin": unit_margin,
            "total_price": round(unit_price * t103["qty"], 2),
            "total_cost": round(price["unit_cost"] * t103["qty"], 2),
            "total_margin": round(unit_margin * t103["qty"], 2),
        },
    }
    return [case_101, case_102, case_103]


def expand(value: str, env: dict) -> str:
    """Expand ${VAR} and ${VAR:-default} the same way Claude Code does in .mcp.json."""
    return re.sub(
        r"\$\{(\w+)(?::-([^}]*))?\}",
        lambda m: env.get(m.group(1)) or (m.group(2) or ""),
        value,
    )


def server_config() -> dict:
    """Load the portable .mcp.json entry and resolve it for this machine."""
    entry = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"][SERVER]
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
    return {
        **entry,
        "command": expand(entry["command"], env),
        "args": [expand(a, env) for a in entry.get("args", [])],
        "env": {**entry.get("env", {}), "CLAUDE_PROJECT_DIR": str(ROOT)},
        "cwd": str(ROOT),
    }


def actual_value(tool: str, output: dict, key: str):
    if tool == "get_lease_rent_status" and key == "checking_balance":
        return next(a["balance"] for a in output["cash_accounts"] if a["name"] == "checking")
    return output[key]


async def main() -> None:
    client = Client({"mcpServers": {SERVER: server_config()}})
    results = []
    async with client:
        tools = sorted(t.name for t in await client.list_tools())
        for case in build_cases():
            output = (await client.call_tool(case["tool"], case["arguments"])).data
            checks = {
                key: {
                    "database": exp,
                    "tool": actual_value(case["tool"], output, key),
                    "match": actual_value(case["tool"], output, key) == exp,
                }
                for key, exp in case.pop("expected").items()
            }
            results.append(
                {
                    **case,
                    "tool_output": output,
                    "database_check": checks,
                    "all_match": all(c["match"] for c in checks.values()),
                }
            )

    evidence = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "transport": "stdio, launched from .mcp.json",
        "mcp_server": SERVER,
        "database": "data/campus_customs_new.db",
        "tools_listed_by_server": tools,
        "all_tools_match_database": all(r["all_match"] for r in results),
        "tests": results,
    }
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(evidence, indent=2) + "\n")
    for r in results:
        print(f"{r['tool']:<24} ticket {r['ticket_id']}  match={r['all_match']}")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}  all_match={evidence['all_tools_match_database']}")


if __name__ == "__main__":
    asyncio.run(main())
