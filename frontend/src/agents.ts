import type { AgentName, TicketStatus } from "./types";

export interface AgentMeta {
  name: string; // the person at the desk
  role: string; // their job on the team
  mono: string; // initials on their ID badge
  color: string; // their identity color
  tint: string; // the paper their notes are written on
  tagline: string; // one line under their name in the staff directory
  idle: string; // what they're doing when not needed
  speaks: string; // how the feed labels their messages
}

// Five people, five desks. Personalities are a light nod to a certain small-town
// parks office; the jobs, tools and rules are exactly the same as before.
export const AGENTS: Record<AgentName, AgentMeta> = {
  boss: {
    name: "Ron",
    role: "Boss",
    mono: "R",
    color: "#6b3f22", // walnut desk
    tint: "#f6ece1",
    tagline: "Says little. Decides everything.",
    idle: "In his office. Door closed.",
    speaks: "decides",
  },
  inventory: {
    name: "April",
    role: "Inventory",
    mono: "A",
    color: "#3d3546", // stockroom after dark
    tint: "#efedf2",
    tagline: "Counts everything. Enjoys none of it.",
    idle: "Not needed. Thrilled.",
    speaks: "counted",
  },
  accounting: {
    name: "Ben",
    role: "Accounting",
    mono: "B",
    color: "#2f5d8a", // calculator blue
    tint: "#e9f0f8",
    tagline: "There's a spreadsheet for this.",
    idle: "Reconciling something, probably.",
    speaks: "ran the numbers",
  },
  facilities: {
    name: "Chris",
    role: "Facilities",
    mono: "C",
    color: "#2a8f63", // morning-run green
    tint: "#e7f5ee",
    tagline: "Genuinely thrilled about the lease.",
    idle: "Out for a run. Back soon!",
    speaks: "checked the building",
  },
  customer_service: {
    name: "Leslie",
    role: "Customer Service",
    mono: "L",
    color: "#c2553a", // warm waffle-brunch red
    tint: "#fbece6",
    tagline: "Has a binder for every customer.",
    idle: "Color-coding a binder.",
    speaks: "drafted",
  },
};

export const AGENT_ORDER: AgentName[] = ["boss", "inventory", "accounting", "facilities", "customer_service"];

/** "Ron (Boss)" style label for places that need both. */
export const who = (a: AgentName) => `${AGENTS[a].name} (${AGENTS[a].role})`;

// Plain-language verbs for tool calls, so the feed reads like an office, not a log file.
export const TOOL_VERBS: Record<string, string> = {
  get_today: "checked the desk calendar",
  get_ticket: "pulled the file",
  list_open_tickets: "flipped through open files",
  check_stock: "counted the shelf",
  list_inventory: "checked every size",
  list_vendors: "went through the vendor Rolodex",
  check_vendor_status: "called up the vendor's file",
  get_invoice: "pulled the invoice",
  get_cash_position: "checked the ledger",
  check_discount_margin: "priced the discount",
  get_lease_rent_status: "checked the lease",
  request_payment: "filed a payment request",
  draft_purchase_order: "drafted a purchase order",
  draft_customer_message: "drafted a letter",
  add_board_note: "pinned a note",
  set_ticket_status: "stamped the file",
  ask_agent: "walked over to a desk",
};

export const STATUS_LABEL: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "In progress",
  awaiting_approval: "Needs your signature",
  escalated: "Escalated",
  resolved: "Resolved",
};

export const money = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
