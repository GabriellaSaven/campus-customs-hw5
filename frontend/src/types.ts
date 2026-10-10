export type AgentName = "boss" | "inventory" | "accounting" | "facilities" | "customer_service";
export type TicketStatus = "open" | "in_progress" | "awaiting_approval" | "escalated" | "resolved";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: TicketStatus;
  notes: string | null;
  created_at: string;
  is_open: boolean;
}

export interface TicketList {
  count: number;
  open: number;
  resolved: number;
  tickets: Ticket[];
}

export interface Draft {
  id: number;
  kind: "customer_message" | "purchase_order";
  author: string;
  recipient: string;
  subject: string;
  status: string;
  total: number | null;
}

export interface BoardNote {
  author: string;
  note: string;
  created_at: string;
}

export interface TicketDetail {
  ticket: Ticket;
  linked: Record<string, unknown>;
  board: {
    notes: BoardNote[];
    drafts: Draft[];
    payment_requests: { id: number; kind: string; amount: number; status: string; payee: string }[];
  };
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  call_id: string;
}

export interface AgentEvent {
  index: number;
  timestamp: string;
  run_id: string;
  ticket_id: number | null;
  agent: AgentName;
  depth: number;
  chain: AgentName[];
  step: number | null;
  event: string;
  tokens_so_far: number | null;
  said?: string | null;
  tools?: string[];
  tool_calls?: ToolCall[];
  results?: { tool: string; call_id: string; result: string }[];
  to?: AgentName;
  reason?: string;
  output?: Record<string, unknown>;
}

export interface EventsResponse {
  total_in_file: number;
  last_index: number;
  events: AgentEvent[];
}

export interface Run {
  run_id: string;
  ticket_id: number;
  status: "running" | "done" | "error";
  started_at: string;
  finished_at: string | null;
  error: string | null;
  result: {
    decision: { status: TicketStatus; decision: string; waiting_on_human: string[] } | null;
    usage: { total_tokens: number; requests: number };
  } | null;
}

export interface PaymentRequest {
  id: number;
  ticket_id: number | null;
  kind: "invoice" | "rent" | "purchase_order";
  ref_id: number;
  payee: string;
  amount: number;
  account: string;
  reason: string | null;
  requested_by: string;
  status: "pending" | "paid" | "rejected";
  created_at: string;
  decided_by: string | null;
}

export interface Queue {
  count: number;
  requests: PaymentRequest[];
  checking_balance: number;
  pending_total: number;
  checking_after_pending: number;
}

export interface Cash {
  account: string;
  balance: number;
  as_of: string;
  pending_requests_total: number;
  available_after_pending: number;
}

export interface AgentSummary {
  agent: AgentName;
  asked_by: AgentName[];
  asked: AgentName[];
  tools: Record<string, number>;
  summary: string | null;
  needs_human: boolean | null;
  actions_taken: string[];
  open_questions: string[];
}

export interface TicketSummary {
  ticket_id: number;
  run_id: string | null;
  started_at?: string;
  finished_at?: string | null;
  status?: "done" | "error" | "running";
  total_tokens?: number;
  agents: AgentSummary[];
}

export interface Health {
  ok: boolean;
  model: string;
  running: Run | null;
}

export interface BriefingItem {
  tone: "red" | "amber" | "green";
  text: string;
}

export interface Briefing {
  today: string;
  open_files: number;
  untouched_files: number;
  items: BriefingItem[];
}
