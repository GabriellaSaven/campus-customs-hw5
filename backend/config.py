"""Settings for the Campus Customs agent team: model, Portkey, paths, tool
access per agent, and the limits that keep token use (and cost) in check."""

import os
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

ROOT = Path(__file__).resolve().parent.parent  # Homework 5/
PROMPTS_DIR = ROOT / "backend" / "prompts"
OUTPUT_DIR = ROOT / "output"
AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"
ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"
MCP_CONFIG = ROOT / ".mcp.json"
MCP_SERVER_NAME = "campus-customs"

# PORTKEY_API_KEY lives in the course-level .env (AI Foundations/.env); a
# Homework 5/.env would also work. The first one found wins.
for env_file in (ROOT / ".env", ROOT.parent / ".env"):
    if env_file.exists():
        load_dotenv(env_file)
        break

# The ONLY model this homework may use, for every agent. Deliberately not
# overridable by an environment variable.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
PORTKEY_PROVIDER = "openai"


def portkey_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to the AI Foundations/.env file.")
    return key


# --- Tool access: each agent only sees the MCP tools its job needs ----------
SHARED_TOOLS = {"get_today", "get_ticket", "add_board_note"}
AGENT_TOOLS: dict[str, set[str]] = {
    "boss": SHARED_TOOLS | {"list_open_tickets", "get_cash_position", "set_ticket_status"},
    "inventory": SHARED_TOOLS | {"check_stock", "list_inventory", "list_vendors", "check_vendor_status"},
    "accounting": SHARED_TOOLS
    | {
        "get_invoice",
        "check_vendor_status",
        "list_vendors",
        "get_cash_position",
        "check_discount_margin",
        "get_lease_rent_status",
        "request_payment",
        "draft_purchase_order",
    },
    "facilities": SHARED_TOOLS | {"get_lease_rent_status"},
    "customer_service": SHARED_TOOLS | {"draft_customer_message"},
}
# Money-moving tools: only the human dashboard may call these. Never an agent.
HUMAN_ONLY_TOOLS = {
    "pay_approved_request",
    "reject_payment_request",
    "resolve_ticket",
    "add_human_note",
    "reset_shop_database",
}
# Read-only lookups the human dashboard may call (through MCP, like everything else).
DASHBOARD_READ_TOOLS = {
    "list_tickets",
    "get_ticket",
    "get_cash_position",
    "list_payment_requests",
    "list_vendors",
    "get_invoice",
    "get_lease_rent_status",
    "get_today",
}
# Tools whose `author` argument the backend fills in (agents can't spoof it).
AUTHOR_TOOLS = {
    "request_payment",
    "draft_purchase_order",
    "draft_customer_message",
    "add_board_note",
    "set_ticket_status",
}
assert not any(tools & HUMAN_ONLY_TOOLS for tools in AGENT_TOOLS.values())

# --- Cost guardrails (per ticket; usage is shared across every delegation) --
REQUEST_LIMIT = 40  # model calls per ticket, all agents combined (30 was too tight for #103)
TOOL_CALLS_LIMIT = 50  # MCP + delegation tool calls per ticket (40 was too tight for #103)
TOTAL_TOKENS_LIMIT = 150_000  # input + output tokens per ticket
MAX_OUTPUT_TOKENS = 2_000  # per model response (includes reasoning tokens)
REASONING_EFFORT = "low"  # enough for tool routing; keeps reasoning tokens cheap
MAX_DELEGATION_DEPTH = 2  # boss -> specialist -> specialist, no deeper
MAX_DELEGATIONS_PER_TICKET = 8
AGENT_RETRIES = 1  # retries for bad tool args / output validation
AUDIT_TEXT_LIMIT = 2_000  # characters kept per audited text field
